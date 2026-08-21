"""CLI segura em duas etapas para importacoes SimplesVet.

``plan`` executa toda a importacao e desfaz a transacao. ``apply`` somente
aceita o plano gerado, ainda valido e com os mesmos arquivos.
"""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import text

from importar_simplesvet_plan import (
    ImportPlanError,
    SCOPE_FILES,
    build_source_manifest,
    create_plan,
    database_identity,
    environment_name,
    is_production,
    load_plan,
    validate_plan,
    write_json,
)
from importar_simplesvet_state import NAO_IMPORTADOS, RUNTIME, STATS, reset_import_state


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_REPORT_DIR = ROOT_DIR / "runtime" / "importacoes-simplesvet"
ACTIVE_TENANT_STATUSES = {"active", "ativo", "trial"}


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("o limite deve ser maior que zero")
    return parsed


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Importacao SimplesVet segura, atomica e vinculada a uma empresa."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    plan = commands.add_parser(
        "plan", help="Simula tudo, desfaz a transacao e gera um plano imutavel."
    )
    plan.add_argument("--tenant-id", required=True, help="UUID da empresa de destino.")
    plan.add_argument(
        "--user-id", required=True, type=_positive_int, help="Usuario dono dos dados."
    )
    plan.add_argument(
        "--source-dir",
        required=True,
        type=Path,
        help="Diretorio local com os CSVs exportados.",
    )
    plan.add_argument(
        "--scope",
        required=True,
        choices=sorted(SCOPE_FILES),
        help="Conjunto de dados que sera processado.",
    )
    plan.add_argument(
        "--limit",
        type=_positive_int,
        help="Limite por CSV. Se omitido, simula todos os registros.",
    )
    plan.add_argument(
        "--report-dir",
        type=Path,
        default=DEFAULT_REPORT_DIR,
        help="Diretorio ignorado pelo Git para plano e relatorios.",
    )

    apply = commands.add_parser(
        "apply", help="Aplica uma simulacao valida, sem aceitar arquivos alterados."
    )
    apply.add_argument("--plan-file", required=True, type=Path)
    apply.add_argument("--confirm-tenant-id", required=True)
    apply.add_argument("--confirm-plan-id", required=True)
    apply.add_argument(
        "--allow-production-apply",
        action="store_true",
        help="Libera apply quando o ambiente/banco for de producao.",
    )
    apply.add_argument(
        "--confirm-production",
        help="Em producao: IMPORTAR-PRODUCAO-<tenant-id>.",
    )
    return parser


def _fail(message: str, *, mode: str) -> int:
    print(
        json.dumps(
            {"ok": False, "mode": mode, "error": message},
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        file=sys.stderr,
    )
    return 1


def _normalize_tenant_id(value: str) -> str:
    try:
        return str(UUID(str(value).strip()))
    except (TypeError, ValueError) as exc:
        raise ImportPlanError("tenant-id deve ser um UUID valido.") from exc


def _resolve_target(db, *, tenant_id: str, user_id: int) -> dict[str, Any]:
    from app.tenancy.context import tenant_context
    from app.tenancy.rls import sync_rls_tenant

    # A tabela users possui RLS. O contexto precisa existir antes da consulta
    # que comprova que o usuario realmente pertence ao tenant informado.
    with tenant_context(tenant_id):
        sync_rls_tenant(db, tenant_id)
        return _resolve_target_in_context(db, tenant_id=tenant_id, user_id=user_id)


def _resolve_target_in_context(db, *, tenant_id: str, user_id: int) -> dict[str, Any]:
    row = (
        db.execute(
            text(
                """
                SELECT CAST(t.id AS TEXT) AS tenant_id,
                       t.name AS tenant_name,
                       t.status AS tenant_status,
                       u.id AS user_id,
                       u.is_active AS user_active
                FROM tenants t
                JOIN users u ON CAST(u.tenant_id AS TEXT) = CAST(t.id AS TEXT)
                WHERE CAST(t.id AS TEXT) = :tenant_id
                  AND u.id = :user_id
                LIMIT 1
                """
            ),
            {"tenant_id": tenant_id, "user_id": user_id},
        )
        .mappings()
        .first()
    )
    if not row:
        raise ImportPlanError(
            "Empresa/usuario de destino nao encontrados ou nao pertencem um ao outro."
        )

    target = dict(row)
    status = str(target["tenant_status"] or "").strip().lower()
    if status not in ACTIVE_TENANT_STATUSES:
        raise ImportPlanError(
            f"Empresa de destino nao esta ativa (status={status or 'vazio'})."
        )
    if not bool(target["user_active"]):
        raise ImportPlanError("Usuario de destino esta inativo.")

    return {
        "tenant_id": str(target["tenant_id"]),
        "tenant_name": str(target["tenant_name"]),
        "tenant_status": status,
        "user_id": int(target["user_id"]),
    }


def _ensure_atomic_transaction(db) -> None:
    """Garante uma transacao externa real antes dos savepoints por linha."""

    connection = db.connection()
    if connection.dialect.name != "sqlite":
        return

    driver_connection = connection.connection.driver_connection
    if not driver_connection.in_transaction:
        connection.exec_driver_sql("BEGIN")


def _run_import(
    db,
    *,
    tenant_id: str,
    user_id: int,
    source_dir: Path,
    report_dir: Path,
    scope: str,
    limit: int | None,
    dry_run: bool,
) -> tuple[dict[str, Any], dict[str, int]]:
    from app.tenancy.context import tenant_context
    from app.tenancy.rls import sync_rls_tenant
    from importar_simplesvet import executar_escopo

    reset_import_state()
    RUNTIME.configure(
        tenant_id=UUID(tenant_id),
        user_id=user_id,
        source_dir=source_dir,
        report_dir=report_dir,
        dry_run=dry_run,
    )
    try:
        _ensure_atomic_transaction(db)
        with tenant_context(tenant_id):
            sync_rls_tenant(db, tenant_id)
            executar_escopo(db, scope=scope, limite=limit)

        stats = deepcopy(STATS)
        rejected = {name: len(items) for name, items in NAO_IMPORTADOS.items()}
        if dry_run:
            db.rollback()
        else:
            db.commit()
        return stats, rejected
    except Exception:
        db.rollback()
        raise
    finally:
        RUNTIME.clear()


def _plan_command(
    args, *, database: dict[str, Any], environment: str, session_factory
) -> int:
    tenant_id = _normalize_tenant_id(args.tenant_id)
    source_dir = args.source_dir.expanduser().resolve()
    report_dir = args.report_dir.expanduser().resolve()
    files = build_source_manifest(source_dir, args.scope)

    db = session_factory()
    try:
        target = _resolve_target(db, tenant_id=tenant_id, user_id=args.user_id)
        stats, rejected = _run_import(
            db,
            tenant_id=tenant_id,
            user_id=args.user_id,
            source_dir=source_dir,
            report_dir=report_dir,
            scope=args.scope,
            limit=args.limit,
            dry_run=True,
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    plan = create_plan(
        database=database,
        environment=environment,
        target=target,
        source_dir=source_dir,
        files=files,
        scope=args.scope,
        limit=args.limit,
        stats=stats,
        rejected=rejected,
    )
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    plan_path = report_dir / f"simplesvet-plan-{timestamp}-{plan['plan_id'][:12]}.json"
    write_json(plan_path, plan)
    print(
        json.dumps(
            {
                "ok": True,
                "mode": "plan",
                "dry_run": True,
                "tenant": target,
                "scope": args.scope,
                "plan_id": plan["plan_id"],
                "plan_file": str(plan_path),
                "expires_at": plan["expires_at"],
                "stats": stats,
                "rejected": rejected,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _apply_command(
    args, *, database: dict[str, Any], environment: str, session_factory
) -> int:
    plan_path = args.plan_file.expanduser().resolve()
    plan = load_plan(plan_path)
    confirm_tenant_id = _normalize_tenant_id(args.confirm_tenant_id)
    source_dir, _files = validate_plan(
        plan,
        database=database,
        confirm_tenant_id=confirm_tenant_id,
        confirm_plan_id=args.confirm_plan_id,
    )
    tenant_id = str(plan["target"]["tenant_id"])
    user_id = int(plan["target"]["user_id"])

    production = is_production(environment, database)
    if production and not args.allow_production_apply:
        raise ImportPlanError(
            "Apply em producao bloqueado sem --allow-production-apply."
        )
    expected_production_confirmation = f"IMPORTAR-PRODUCAO-{tenant_id}"
    if production and args.confirm_production != expected_production_confirmation:
        raise ImportPlanError("Confirmacao de producao ausente ou incorreta.")

    marker_path = plan_path.parent / f"simplesvet-applied-{plan['plan_id']}.json"
    if marker_path.exists():
        raise ImportPlanError("Este plano ja foi aplicado; gere uma nova simulacao.")
    lock_path = plan_path.parent / f"simplesvet-applying-{plan['plan_id']}.lock"
    try:
        with lock_path.open("x", encoding="utf-8") as lock_file:
            lock_file.write(
                json.dumps(
                    {
                        "plan_id": plan["plan_id"],
                        "tenant_id": tenant_id,
                        "started_at": datetime.now(timezone.utc).isoformat(),
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n"
            )
    except FileExistsError as exc:
        raise ImportPlanError(
            "Este plano ja esta sendo aplicado ou exige auditoria de uma tentativa anterior."
        ) from exc

    try:
        db = session_factory()
    except Exception:
        lock_path.unlink(missing_ok=True)
        raise
    try:
        current_target = _resolve_target(db, tenant_id=tenant_id, user_id=user_id)
        stats, rejected = _run_import(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            source_dir=source_dir,
            report_dir=plan_path.parent,
            scope=str(plan["scope"]),
            limit=plan.get("limit"),
            dry_run=False,
        )
    except Exception:
        db.rollback()
        lock_path.unlink(missing_ok=True)
        raise
    finally:
        db.close()

    result = {
        "ok": True,
        "mode": "apply",
        "dry_run": False,
        "applied_at": datetime.now(timezone.utc).isoformat(),
        "plan_id": plan["plan_id"],
        "plan_file": str(plan_path),
        "tenant": current_target,
        "scope": plan["scope"],
        "stats": stats,
        "rejected": rejected,
        "simulation_stats": plan["simulation"]["stats"],
        "simulation_rejected": plan["simulation"]["rejected"],
        "matches_simulation": (
            stats == plan["simulation"]["stats"]
            and rejected == plan["simulation"]["rejected"]
        ),
    }
    try:
        write_json(marker_path, result)
    except OSError as exc:
        result["report_warning"] = (
            "A importacao foi confirmada no banco, mas o recibo local falhou. "
            "O bloqueio foi mantido para impedir reaplicacao: " + str(exc)
        )
    else:
        lock_path.unlink(missing_ok=True)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        from app.db import DATABASE_URL, SessionLocal

        database = database_identity(DATABASE_URL)
        environment = environment_name()
        if args.command == "plan":
            return _plan_command(
                args,
                database=database,
                environment=environment,
                session_factory=SessionLocal,
            )
        return _apply_command(
            args,
            database=database,
            environment=environment,
            session_factory=SessionLocal,
        )
    except (ImportPlanError, ValueError) as exc:
        return _fail(str(exc), mode=args.command)
    except Exception as exc:
        return _fail(f"Falha inesperada: {exc}", mode=args.command)


if __name__ == "__main__":
    raise SystemExit(main())
