"""Cria uma loja e o administrador por operacao manual, em uma transacao.

Uso: python provisionar_tenant_operador.py --name ... --login-name ...
     --legal-name ... --cnpj ... --email ... --owner ... --address ...
     --number ... --city ... --uf ... --plan pet-gestao

Por padrao executa uma simulacao com rollback. --apply grava a transacao.
A senha e lida de stdin, sem constar em argumentos, logs ou arquivos.

Para separar um usuario que ainda possui autoria de dados no tenant anterior,
use --move-existing-user-id com os tres campos --expected-source-* e
--plan same-as-source. Nesse modo, a senha existente e preservada e as sessoes
anteriores sao revogadas. O usuario historico fica inativo na origem.
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
from app.models import Role, Tenant, User, UserSession, UserTenant
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
    parser.add_argument("--move-existing-user-id", type=int)
    parser.add_argument("--expected-source-tenant-id")
    parser.add_argument("--expected-source-tenant-email")
    parser.add_argument("--expected-source-tenant-cnpj")
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


def _prepare_existing_user_move(
    db, args: argparse.Namespace, email: str
) -> dict | None:
    if args.move_existing_user_id is None:
        return None
    if not all(
        (
            args.expected_source_tenant_id,
            args.expected_source_tenant_email,
            args.expected_source_tenant_cnpj,
        )
    ):
        raise ValueError(
            "A movimentacao exige tenant de origem, email e CNPJ esperados"
        )

    source_user = (
        db.query(User)
        .filter(User.id == args.move_existing_user_id)
        .with_for_update()
        .first()
    )
    if not source_user or source_user.email != email or not source_user.is_active:
        raise ValueError("Usuario de origem, email ou status divergente")
    if str(source_user.tenant_id) != args.expected_source_tenant_id:
        raise ValueError("Tenant principal do usuario de origem divergente")
    if (source_user.nome or "").strip().casefold() != args.owner.strip().casefold():
        raise ValueError("Nome do titular de origem divergente")
    if (
        not source_user.hashed_password
        or not source_user.email_verified
        or source_user.is_admin
        or source_user.username
        or source_user.login_phone
        or source_user.two_factor_enabled
        or source_user.oauth_provider
        or source_user.vet_calendar_token
    ):
        raise ValueError("Credenciais de origem exigem revisao manual")

    source_tenant = (
        db.query(Tenant)
        .filter(Tenant.id == args.expected_source_tenant_id)
        .with_for_update()
        .first()
    )
    source_cnpj = (
        "".join(char for char in str(source_tenant.cnpj or "") if char.isdigit())
        if source_tenant
        else ""
    )
    expected_cnpj = "".join(
        char for char in args.expected_source_tenant_cnpj if char.isdigit()
    )
    if (
        not source_tenant
        or source_tenant.email != args.expected_source_tenant_email.strip().lower()
        or source_cnpj != expected_cnpj
    ):
        raise ValueError("Dados da empresa de origem divergentes")

    source_link = (
        db.query(UserTenant)
        .filter(
            UserTenant.user_id == source_user.id,
            UserTenant.tenant_id == source_user.tenant_id,
            UserTenant.is_active.is_(True),
        )
        .with_for_update()
        .first()
    )
    if not source_link:
        raise ValueError("Vinculo ativo do usuario com a origem nao encontrado")
    other_links = (
        db.query(UserTenant)
        .filter(
            UserTenant.user_id == source_user.id,
            UserTenant.tenant_id != source_user.tenant_id,
            UserTenant.is_active.is_(True),
        )
        .count()
    )
    if other_links:
        raise ValueError("Usuario possui outros vinculos ativos")
    remaining_admin = (
        db.query(User.id)
        .join(UserTenant, UserTenant.user_id == User.id)
        .join(Role, Role.id == UserTenant.role_id)
        .filter(
            User.email == source_tenant.email,
            User.is_active.is_(True),
            UserTenant.tenant_id == source_user.tenant_id,
            UserTenant.is_active.is_(True),
            Role.name == "Administrador",
        )
        .first()
    )
    if not remaining_admin:
        raise ValueError("Empresa de origem ficaria sem administrador principal")
    historical_username = f"historico_{source_user.id}"
    if (
        db.query(User.id)
        .filter(
            User.tenant_id == source_user.tenant_id,
            User.username == historical_username,
        )
        .first()
    ):
        raise ValueError("Nome de usuario historico ja existe")
    return {
        "user": source_user,
        "link": source_link,
        "password_hash": source_user.hashed_password,
        "email_verified_at": source_user.email_verified_at,
        "password_changed_at": source_user.password_changed_at,
        "consent_date": source_user.consent_date,
        "consent_version": source_user.consent_version,
        "privacy_version": source_user.privacy_version,
        "consent_ip": source_user.consent_ip,
        "consent_user_agent": source_user.consent_user_agent,
        "telefone": source_user.telefone,
        "historical_username": historical_username,
        "source_plan": source_tenant.plan,
        "source_billing_status": source_tenant.billing_status,
    }


def provisionar(db, args: argparse.Namespace, password: str | None) -> dict:
    email = args.email.strip().lower()
    cnpj = "".join(char for char in args.cnpj if char.isdigit())
    if not _cnpj_valido(cnpj):
        raise ValueError("CNPJ invalido")
    sync_rls_auth_email(db, email)
    if args.move_existing_user_id is not None:
        sync_rls_tenant(db, args.expected_source_tenant_id)
        with tenant_context(args.expected_source_tenant_id):
            existing_move = _prepare_existing_user_move(db, args, email)
    else:
        existing_move = None
    if args.plan == "same-as-source":
        if existing_move is None or existing_move["source_billing_status"] != "active":
            raise ValueError("Copiar acesso exige empresa de origem ativa")
        plan_code = existing_move["source_plan"]
        billing_status = "active"
        trial_ends_at = None
    else:
        selected_plan, _ = resolve_signup_selection(args.plan, "petshop")
        plan_code = selected_plan.code
        billing_status = "trial"
        trial_ends_at = datetime.now(timezone.utc) + timedelta(days=DEFAULT_TRIAL_DAYS)
    if (
        existing_move is None
        and db.execute(select(User.id).where(func.lower(User.email) == email)).first()
    ):
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
        plan=plan_code,
        billing_status=billing_status,
        trial_started_at=trial_started if billing_status == "trial" else None,
        trial_ends_at=trial_ends_at,
        subscription_activated_at=trial_started if billing_status == "active" else None,
        subscription_source="manual",
        organization_type="petshop",
    )
    db.add(tenant)
    db.flush()
    set_primary_tenant_login_name(db, tenant_id, args.login_name.strip())

    if existing_move is not None:
        source_user = existing_move["user"]
        source_user.email = None
        source_user.username = existing_move["historical_username"]
        source_user.hashed_password = None
        source_user.is_active = False
        source_user.reset_token = None
        source_user.reset_token_expires = None
        source_user.email_verification_token_hash = None
        source_user.email_verification_token_expires = None
        existing_move["link"].is_active = False
        for session in (
            db.query(UserSession)
            .filter(
                UserSession.user_id == source_user.id,
                UserSession.revoked.is_(False),
            )
            .all()
        ):
            session.revoked = True
            session.revoked_at = trial_started
            session.revoke_reason = "tenant_access_moved"
        db.flush()

    with tenant_context(str(tenant_id)):
        sync_rls_tenant(db, tenant_id)
        user = User(
            tenant_id=tenant_id,
            email=email,
            hashed_password=(
                existing_move["password_hash"]
                if existing_move
                else hash_password(password)
            ),
            nome=args.owner.strip(),
            nome_loja=tenant.name,
            is_active=True,
            is_admin=False,
            email_verified=True,
            email_verified_at=(
                existing_move["email_verified_at"] if existing_move else trial_started
            ),
            password_changed_at=(
                existing_move["password_changed_at"] if existing_move else trial_started
            ),
            consent_date=(existing_move["consent_date"] if existing_move else None),
            consent_version=(
                existing_move["consent_version"] if existing_move else None
            ),
            privacy_version=(
                existing_move["privacy_version"] if existing_move else None
            ),
            consent_ip=(existing_move["consent_ip"] if existing_move else None),
            consent_user_agent=(
                existing_move["consent_user_agent"] if existing_move else None
            ),
            telefone=(existing_move["telefone"] if existing_move else None),
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
            "plan": plan_code,
            "billing_status": billing_status,
            "permissions": permissions,
            "name": tenant.name,
            "login_name": args.login_name.strip(),
            "cnpj": cnpj,
            "historical_user_id": (existing_move["user"].id if existing_move else None),
        }


def main() -> int:
    args = _args()
    password = None if args.move_existing_user_id is not None else _senha()
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
