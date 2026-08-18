"""CLI segura para enriquecer produtos existentes pelo GTIN/EAN.

O modo padrao e dry-run. A aplicacao exige --apply e uma frase explicita.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

if Path("/app/app").is_dir() and "/app" not in sys.path:
    sys.path.insert(0, "/app")

from app.db import SessionLocal, engine
from app.services.base_catalog_enrichment_service import (
    enrich_existing_products_by_gtin,
)


CONFIRMATION = "ENRIQUECER_CATALOGO_POR_EAN"


def parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(
        description="Enriquece produtos existentes pelo EAN sem copiar precos ou estoque."
    )
    cli.add_argument("--source-tenant-id", required=True)
    cli.add_argument("--target-tenant-id", required=True)
    cli.add_argument("--actor-user-id", required=True, type=int)
    cli.add_argument("--apply", action="store_true")
    cli.add_argument("--confirm")
    return cli


def ensure_safe_apply(args: argparse.Namespace) -> None:
    if not args.apply:
        return
    if args.confirm != CONFIRMATION:
        raise RuntimeError(f"Confirmacao obrigatoria: {CONFIRMATION}")
    environment = (
        (os.getenv("ENVIRONMENT") or os.getenv("APP_ENV") or os.getenv("ENV") or "")
        .strip()
        .lower()
    )
    if environment not in {"production", "prod"}:
        return
    database = (engine.url.database or "").strip().lower()
    host = (engine.url.host or "").strip().lower()
    if database != "petshop_prod" or host not in {
        "postgres",
        "petshop-prod-postgres",
    }:
        raise RuntimeError("Banco de producao nao corresponde ao ambiente esperado.")


def main() -> int:
    args = parser().parse_args()
    ensure_safe_apply(args)
    db = SessionLocal()
    try:
        result = enrich_existing_products_by_gtin(
            db=db,
            source_tenant_id=args.source_tenant_id,
            target_tenant_id=args.target_tenant_id,
            user_id=args.actor_user_id,
            dry_run=not args.apply,
        )
        if args.apply:
            db.commit()
        else:
            db.rollback()
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 0
    except Exception as exc:
        db.rollback()
        print(
            json.dumps(
                {"ok": False, "error": str(exc), "dry_run": not args.apply},
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
