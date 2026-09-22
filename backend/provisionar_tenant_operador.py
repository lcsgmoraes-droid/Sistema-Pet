"""Cria uma loja e o administrador por operacao manual, em uma transacao.

Uso: python provisionar_tenant_operador.py --name ... --login-name ...
     --legal-name ... --cnpj ... --email ... --owner ... --address ...
     --number ... --city ... --uf ... --plan pet-gestao

Por padrao executa uma simulacao com rollback. --apply grava a transacao.
A senha e lida de stdin, sem constar em argumentos, logs ou arquivos.
"""

from __future__ import annotations

import argparse
import getpass
import json
import sys
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

import app.db.base  # noqa: F401 - registra as tabelas do onboarding
from app.auth import hash_password
from app.auth.auth_multitenant_support import (
    DEFAULT_TRIAL_DAYS,
    grant_all_permissions_to_role,
)
from app.db import SessionLocal
from app.empresa_config_geral_models import EmpresaConfigGeral
from app.models import Role, Tenant, User, UserTenant
from app.services.default_roles_service import create_default_roles_for_new_tenant
from app.services.pessoa_duplicate_service import _cnpj_valido
from app.services.plan_catalog import resolve_signup_selection
from app.services.tenant_login_name_service import set_primary_tenant_login_name
from app.services.tenant_onboarding_service import onboard_tenant_defaults
from app.tenancy.context import tenant_context
from app.tenancy.rls import sync_rls_auth_email, sync_rls_tenant


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    for key in (
        "name",
        "login-name",
        "legal-name",
        "cnpj",
        "email",
        "owner",
        "address",
        "number",
        "city",
        "uf",
        "plan",
    ):
        parser.add_argument(f"--{key}", required=True)
    parser.add_argument("--cep")
    parser.add_argument("--bairro")
    parser.add_argument("--phone")
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


def _senha() -> str:
    password = (
        sys.stdin.readline().rstrip("\r\n")
        if not sys.stdin.isatty()
        else getpass.getpass("Senha do administrador: ")
    )
    if len(password) < 8:
        raise ValueError("Senha deve ter no minimo 8 caracteres")
    return password


def provisionar(db, args: argparse.Namespace, password: str) -> dict:
    email = args.email.strip().lower()
    cnpj = "".join(char for char in args.cnpj if char.isdigit())
    if not _cnpj_valido(cnpj):
        raise ValueError("CNPJ invalido")
    selected_plan, organization_type = resolve_signup_selection(args.plan, "petshop")
    sync_rls_auth_email(db, email)
    if db.execute(select(User.id).where(func.lower(User.email) == email)).first():
        raise ValueError("Email ja pertence a um usuario; operacao cancelada")
    if any(
        "".join(char for char in str(existente or "") if char.isdigit()) == cnpj
        for existente in db.execute(select(Tenant.cnpj)).scalars()
    ):
        raise ValueError("CNPJ ja pertence a outro tenant; operacao cancelada")

    tenant_id = uuid.uuid4()
    trial_started = datetime.now(timezone.utc)
    tenant = Tenant(
        id=str(tenant_id),
        name=args.name.strip(),
        razao_social=args.legal_name.strip(),
        cnpj=cnpj,
        email=email,
        endereco=args.address.strip(),
        numero=args.number.strip(),
        bairro=(args.bairro or "").strip() or None,
        cidade=args.city.strip(),
        uf=args.uf.strip().upper(),
        cep=(args.cep or "").strip() or None,
        telefone=(args.phone or "").strip() or None,
        status="active",
        plan=selected_plan.code,
        billing_status="trial",
        trial_started_at=trial_started,
        trial_ends_at=trial_started + timedelta(days=DEFAULT_TRIAL_DAYS),
        subscription_source="manual",
        organization_type=organization_type,
    )
    db.add(tenant)
    db.flush()
    set_primary_tenant_login_name(db, tenant_id, args.login_name.strip())

    with tenant_context(str(tenant_id)):
        sync_rls_tenant(db, tenant_id)
        user = User(
            tenant_id=tenant_id,
            email=email,
            hashed_password=hash_password(password),
            nome=args.owner.strip(),
            nome_loja=tenant.name,
            is_active=True,
            is_admin=False,
            email_verified=True,
            email_verified_at=trial_started,
        )
        db.add(user)
        db.flush()
        admin_role = Role(name="Administrador", tenant_id=tenant_id)
        db.add(admin_role)
        db.flush()
        permissions = grant_all_permissions_to_role(admin_role.id, tenant_id, db)
        create_default_roles_for_new_tenant(db, tenant_id)
        onboard_tenant_defaults(
            db=db,
            tenant_id=tenant_id,
            user_id=user.id,
            dry_run=False,
            strict_required=True,
        )
        config = (
            db.execute(
                select(EmpresaConfigGeral).where(
                    EmpresaConfigGeral.tenant_id == tenant_id
                )
            )
            .scalars()
            .first()
        )
        if config is None:
            config = EmpresaConfigGeral(tenant_id=tenant_id)
            db.add(config)
        config.nome_fantasia = tenant.name
        config.razao_social = tenant.razao_social
        config.cnpj = tenant.cnpj
        config.logradouro = tenant.endereco
        config.numero = tenant.numero
        config.bairro = tenant.bairro
        config.cidade = tenant.cidade
        config.uf = tenant.uf
        config.cep = tenant.cep
        config.telefone = tenant.telefone
        config.email = tenant.email
        db.add(
            UserTenant(
                user_id=user.id,
                tenant_id=tenant_id,
                role_id=admin_role.id,
                is_active=True,
            )
        )
        db.flush()
        return {
            "tenant_id": str(tenant_id),
            "user_id": user.id,
            "plan": selected_plan.code,
            "permissions": permissions,
            "name": tenant.name,
            "login_name": args.login_name.strip(),
            "cnpj": cnpj,
        }


def main() -> int:
    args = _args()
    password = _senha()
    db = SessionLocal()
    try:
        result = provisionar(db, args, password)
        if args.apply:
            db.commit()
            result["status"] = "created"
        else:
            db.rollback()
            result["status"] = "simulation_rolled_back"
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
