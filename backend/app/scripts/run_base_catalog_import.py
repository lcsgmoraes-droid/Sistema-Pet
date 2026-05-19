"""Run the administrative base catalog import for a tenant.

Default mode is dry-run. Use --apply to persist data.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import text

if __package__ in {None, ""}:
    backend_path = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(backend_path))

from app.db import SessionLocal
from app.services.base_catalog_import_service import (
    DEFAULT_BASE_CATALOG_SOURCE_EMAIL,
    import_base_catalog,
)


PRODUCTION_ENVS = {"prod", "production"}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Importa o catalogo base da loja padrao para um tenant destino."
    )
    parser.add_argument("--target-tenant-id", required=True, help="Tenant UUID que recebera o catalogo.")
    parser.add_argument("--target-user-id", type=int, required=True, help="Usuario dono/auditor dos registros criados.")
    parser.add_argument(
        "--source-email",
        default=DEFAULT_BASE_CATALOG_SOURCE_EMAIL,
        help="Email do usuario fonte do catalogo base.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persiste a importacao. Sem esta flag, executa apenas dry-run.",
    )
    parser.add_argument(
        "--allow-production-apply",
        action="store_true",
        help="Permite --apply quando APP_ENV/ENV/ENVIRONMENT for production/prod.",
    )
    return parser


def _environment_name() -> str:
    for name in ("APP_ENV", "ENVIRONMENT", "ENV"):
        value = os.getenv(name)
        if value:
            return value.strip().lower()
    return ""


def _fail(message: str, dry_run: bool) -> int:
    print(
        json.dumps(
            {
                "ok": False,
                "error": message,
                "dry_run": dry_run,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        file=sys.stderr,
    )
    return 1


def _resolve_source_tenant_id(db, source_email: str) -> str | None:
    row = db.execute(
        text(
            """
            SELECT tenant_id
            FROM users
            WHERE lower(email) = lower(:email)
              AND tenant_id IS NOT NULL
            ORDER BY id
            LIMIT 1
            """
        ),
        {"email": source_email.strip()},
    ).first()
    if not row:
        return None
    return str(row[0])


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    dry_run = not args.apply

    environment = _environment_name()
    if args.apply and environment in PRODUCTION_ENVS and not args.allow_production_apply:
        return _fail(
            "Ambiente production/prod detectado; --apply bloqueado sem --allow-production-apply.",
            dry_run=False,
        )

    db = SessionLocal()
    try:
        source_tenant_id = _resolve_source_tenant_id(db, args.source_email)
        if not source_tenant_id:
            db.rollback()
            return _fail(
                f"Usuario fonte nao encontrado ou sem tenant: {args.source_email}.",
                dry_run=dry_run,
            )

        result: dict[str, Any] = import_base_catalog(
            db=db,
            source_tenant_id=source_tenant_id,
            target_tenant_id=args.target_tenant_id,
            user_id=args.target_user_id,
            dry_run=dry_run,
        )
        if args.apply:
            db.commit()
        else:
            db.rollback()

        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if result.get("ok", True) else 1
    except Exception as exc:
        db.rollback()
        return _fail(str(exc), dry_run=dry_run)
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
