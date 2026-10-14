"""Simula e aplica a carga JN Moura de clientes, produtos e estoque.

``plan`` executa tudo e desfaz; ``apply`` aceita apenas o mesmo banco, tenant,
usuario e arquivos aprovados, dentro de 24 horas. Nenhum dado da empresa do
backup substitui o cadastro fiscal da empresa de destino.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy import select

import app.db.base  # noqa: F401 - registra os modelos
from app.db import SessionLocal
from app.models import Role, Tenant, User, UserTenant
from app.tenancy.context import tenant_context
from app.tenancy.rls import sync_rls_tenant
from importar_jnm_catalogo import (
    JnmImportError,
    _sha256_file,
    insert_catalog,
    load_source,
    normalize_cnpj,
    prepare_rows,
)
from importar_simplesvet_plan import database_identity, environment_name, is_production


DEFAULT_REPORT_DIR = Path("data/importacoes-jnm/reports")
PLAN_LIFETIME = timedelta(hours=24)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    plan = commands.add_parser("plan", help="Simula e reverte toda a carga.")
    plan.add_argument("--tenant-id", required=True)
    plan.add_argument("--user-id", required=True, type=int)
    plan.add_argument("--expected-target-cnpj", required=True)
    plan.add_argument("--expected-source-cnpj", required=True)
    plan.add_argument("--expected-backup-sha256", required=True)
    plan.add_argument("--source-dir", required=True, type=Path)
    plan.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    apply = commands.add_parser("apply", help="Aplica somente um plano valido.")
    apply.add_argument("--plan-file", required=True, type=Path)
    apply.add_argument("--confirm-tenant-id", required=True)
    apply.add_argument("--confirm-plan-id", required=True)
    apply.add_argument("--allow-production-apply", action="store_true")
    apply.add_argument("--confirm-production")
    return parser


def _normalize_uuid(value: str) -> str:
    try:
        return str(UUID(value))
    except ValueError as exc:
        raise JnmImportError("ID de empresa invalido") from exc


def _target(db, tenant_id: str, user_id: int, expected_cnpj: str) -> dict:
    with tenant_context(tenant_id):
        sync_rls_tenant(db, tenant_id)
        tenant = db.get(Tenant, tenant_id)
        user = db.get(User, user_id)
        if not tenant or not user or str(user.tenant_id) != tenant_id:
            raise JnmImportError("Empresa ou usuario de destino divergente")
        if normalize_cnpj(tenant.cnpj) != normalize_cnpj(expected_cnpj):
            raise JnmImportError("CNPJ do tenant de destino divergente")
        if tenant.status != "active" or not user.is_active:
            raise JnmImportError("Empresa ou usuario de destino inativo")
        admin = db.execute(
            select(UserTenant.user_id)
            .join(Role, Role.id == UserTenant.role_id)
            .where(
                UserTenant.tenant_id == tenant_id,
                UserTenant.user_id == user_id,
                UserTenant.is_active.is_(True),
                Role.name == "Administrador",
            )
        ).first()
        if not admin:
            raise JnmImportError("Usuario de destino nao e administrador ativo")
        return {
            "tenant_id": tenant_id,
            "tenant_name": tenant.name,
            "tenant_cnpj": normalize_cnpj(tenant.cnpj),
            "user_id": user_id,
            "user_email": user.email,
        }


def _material_hash(payload: dict) -> str:
    material = {key: value for key, value in payload.items() if key != "plan_id"}
    encoded = json.dumps(
        material, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _run(
    db,
    tenant_id: str,
    user_id: int,
    clients: list[dict],
    products: list[dict],
    *,
    dry_run: bool,
    expected_created: dict | None = None,
) -> dict:
    try:
        with tenant_context(tenant_id):
            sync_rls_tenant(db, tenant_id)
            db.execute(
                select(Tenant.id).where(Tenant.id == tenant_id).with_for_update()
            ).first()
            result = insert_catalog(
                db,
                tenant_id=tenant_id,
                user_id=user_id,
                clients=clients,
                products=products,
            )
        if expected_created is not None and result != expected_created:
            raise JnmImportError("Contagens aplicadas diferem da simulacao")
        if dry_run:
            db.rollback()
        else:
            db.commit()
        return result
    except Exception:
        db.rollback()
        raise


def _plan(args: argparse.Namespace) -> dict:
    tenant_id = _normalize_uuid(args.tenant_id)
    manifest, source = load_source(
        args.source_dir,
        args.expected_source_cnpj,
        args.expected_backup_sha256,
    )
    clients, products, metrics = prepare_rows(source)
    with SessionLocal() as db:
        database = database_identity(str(db.get_bind().url))
        target = _target(db, tenant_id, args.user_id, args.expected_target_cnpj)
        created = _run(db, tenant_id, args.user_id, clients, products, dry_run=True)
    now = datetime.now(timezone.utc)
    payload = {
        "version": 1,
        "status": "simulation_complete",
        "created_at": now.isoformat(),
        "expires_at": (now + PLAN_LIFETIME).isoformat(),
        "environment": environment_name(),
        "database": database,
        "target": target,
        "source": {
            "directory": str(args.source_dir.resolve()),
            "source_cnpj": manifest["source_cnpj"],
            "backup_sha256": manifest["backup_sha256"],
            "manifest_sha256": _sha256_file(args.source_dir / "manifest.json"),
            "files": manifest["files"],
        },
        "simulation": {"metrics": metrics, "created": created},
    }
    payload["plan_id"] = _material_hash(payload)
    path = args.report_dir.resolve() / f"jnm-plan-{payload['plan_id'][:16]}.json"
    _write_json(path, payload)
    return {
        "ok": True,
        "mode": "plan",
        "tenant_id": tenant_id,
        "tenant_name": target["tenant_name"],
        "plan_id": payload["plan_id"],
        "expires_at": payload["expires_at"],
        "plan_file": str(path),
        "metrics": metrics,
        "created": created,
        "changes_saved": False,
    }


def _apply(args: argparse.Namespace) -> dict:
    plan = json.loads(args.plan_file.read_text(encoding="utf-8"))
    if plan.get("version") != 1 or plan.get("status") != "simulation_complete":
        raise JnmImportError("Plano de importacao invalido")
    if (
        plan.get("plan_id") != _material_hash(plan)
        or plan["plan_id"] != args.confirm_plan_id
    ):
        raise JnmImportError("Identificador ou integridade do plano divergente")
    tenant_id = _normalize_uuid(args.confirm_tenant_id)
    if tenant_id != plan["target"]["tenant_id"]:
        raise JnmImportError("Empresa confirmada difere do plano")
    if datetime.now(timezone.utc) > datetime.fromisoformat(plan["expires_at"]):
        raise JnmImportError("Plano expirado; simule novamente")
    source_dir = Path(plan["source"]["directory"])
    manifest, source = load_source(
        source_dir,
        plan["source"]["source_cnpj"],
        plan["source"]["backup_sha256"],
    )
    if _sha256_file(source_dir / "manifest.json") != plan["source"]["manifest_sha256"]:
        raise JnmImportError("Manifesto alterado apos a simulacao")
    if manifest["files"] != plan["source"]["files"]:
        raise JnmImportError("Arquivos alterados apos a simulacao")
    clients, products, metrics = prepare_rows(source)
    if metrics != plan["simulation"]["metrics"]:
        raise JnmImportError("Contagens alteradas apos a simulacao")
    with SessionLocal() as db:
        database = database_identity(str(db.get_bind().url))
        if database != plan["database"]:
            raise JnmImportError("Banco de dados difere do plano")
        production = is_production(environment_name(), database)
        if production and (
            not args.allow_production_apply
            or args.confirm_production != f"IMPORTAR-JNM-PRODUCAO-{tenant_id}"
        ):
            raise JnmImportError(
                "Aplicacao em producao exige liberacao e frase de confirmacao"
            )
        target = _target(
            db, tenant_id, plan["target"]["user_id"], plan["target"]["tenant_cnpj"]
        )
        if target != plan["target"]:
            raise JnmImportError("Cadastro do destino mudou apos a simulacao")
        created = _run(
            db,
            tenant_id,
            target["user_id"],
            clients,
            products,
            dry_run=False,
            expected_created=plan["simulation"]["created"],
        )
    receipt = args.plan_file.parent / f"jnm-applied-{plan['plan_id']}.json"
    result = {"ok": True, "mode": "apply", "tenant_id": tenant_id, "created": created}
    try:
        _write_json(
            receipt,
            {
                "plan_id": plan["plan_id"],
                "tenant_id": tenant_id,
                "applied_at": datetime.now(timezone.utc).isoformat(),
                "created": created,
            },
        )
        result["receipt_file"] = str(receipt)
    except OSError:
        result["warning"] = "Carga aplicada, mas o recibo local nao foi gravado"
    return result


def main() -> int:
    args = _parser().parse_args()
    try:
        result = _plan(args) if args.command == "plan" else _apply(args)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except JnmImportError as exc:
        print(
            json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False),
            file=sys.stderr,
        )
        return 1
    except Exception:
        print("Falha na importacao; transacao revertida.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
