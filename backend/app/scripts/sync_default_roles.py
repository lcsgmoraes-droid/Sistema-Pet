"""Simula ou aplica os perfis operacionais padrao em um tenant existente."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from uuid import UUID

if __package__ in {None, ""}:
    backend_path = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(backend_path))

from app.db import SessionLocal
from app.services.default_roles_service import sync_default_roles
from app.tenancy.context import clear_tenant_context, set_tenant_context


PRODUCTION_ENVS = {"prod", "production"}


def _environment_name() -> str:
    for name in ("APP_ENV", "ENVIRONMENT", "ENV"):
        value = os.getenv(name)
        if value:
            return value.strip().lower()
    return ""


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Cria e sincroniza perfis operacionais padrao de um tenant."
    )
    parser.add_argument("--tenant-id", required=True, help="UUID exato do tenant.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persiste as alteracoes. Sem esta opcao, apenas simula.",
    )
    parser.add_argument(
        "--allow-production-apply",
        action="store_true",
        help="Libera --apply quando o ambiente for production/prod.",
    )
    return parser


def _print_result(result: dict) -> None:
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    dry_run = not args.apply

    if (
        args.apply
        and _environment_name() in PRODUCTION_ENVS
        and not args.allow_production_apply
    ):
        _print_result(
            {
                "ok": False,
                "dry_run": False,
                "error": (
                    "Ambiente de producao detectado; use "
                    "--allow-production-apply somente apos autorizacao."
                ),
            }
        )
        return 1

    db = SessionLocal()
    try:
        tenant_id = UUID(args.tenant_id)
        set_tenant_context(tenant_id)
        result = sync_default_roles(
            db,
            tenant_id,
            update_existing=True,
            dry_run=dry_run,
        )
        result["ok"] = not result["missing_permissions"]
        if args.apply:
            db.commit()
        else:
            db.rollback()
        _print_result(result)
        return 0 if result["ok"] else 1
    except Exception as exc:
        db.rollback()
        _print_result({"ok": False, "dry_run": dry_run, "error": str(exc)})
        return 1
    finally:
        clear_tenant_context()
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
