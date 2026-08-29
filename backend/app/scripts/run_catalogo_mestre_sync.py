"""Executa a sincronizacao unilateral Atacadao -> catalogo mestre.

O padrao e sempre dry-run. ``--apply`` grava somente nas tabelas
``catalogo_mestre_*`` e possui uma trava adicional em producao.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from sqlalchemy import text

if __package__ in {None, ""}:
    backend_path = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(backend_path))

from app.db import SessionLocal
from app.services.catalogo_mestre_service import (
    DEFAULT_IMAGE_TARGET,
    DEFAULT_MASTER_CATALOG_SOURCE_EMAIL,
    sync_catalogo_mestre_from_tenant,
)

PRODUCTION_ENVS = {"prod", "production"}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Consulta o cadastro do Atacadao e sincroniza o catalogo mestre global, "
            "sem alterar produtos de nenhuma loja."
        )
    )
    parser.add_argument(
        "--source-email",
        default=DEFAULT_MASTER_CATALOG_SOURCE_EMAIL,
        help="Identificador do Atacadao usado para localizar o tenant fonte.",
    )
    parser.add_argument(
        "--image-target",
        type=int,
        default=DEFAULT_IMAGE_TARGET,
        help="Quantidade minima desejada de imagens por produto (padrao: 5).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Grava no catalogo mestre. Sem esta flag, apenas simula.",
    )
    parser.add_argument(
        "--allow-production-apply",
        action="store_true",
        help="Libera --apply se o ambiente for production/prod.",
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
            {"ok": False, "dry_run": dry_run, "error": message},
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        file=sys.stderr,
    )
    return 1


def _resolve_source_tenant_id(db, source_email: str) -> str | None:
    row = db.execute(
        text("""
            SELECT tenant_id
              FROM users
             WHERE lower(email) = lower(:email)
               AND tenant_id IS NOT NULL
             ORDER BY id
             LIMIT 1
            """),
        {"email": source_email.strip()},
    ).first()
    return str(row[0]) if row else None


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    dry_run = not args.apply
    if args.source_email.strip().casefold() != DEFAULT_MASTER_CATALOG_SOURCE_EMAIL:
        return _fail(
            "Esta primeira versao aceita somente o Atacadao como fonte autorizada.",
            dry_run,
        )
    if (
        args.apply
        and _environment_name() in PRODUCTION_ENVS
        and not args.allow_production_apply
    ):
        return _fail(
            "Ambiente production/prod detectado; --apply bloqueado sem "
            "--allow-production-apply.",
            dry_run=False,
        )

    db = SessionLocal()
    try:
        source_tenant_id = _resolve_source_tenant_id(db, args.source_email)
        if not source_tenant_id:
            db.rollback()
            return _fail(
                f"Atacadao nao encontrado ou sem tenant: {args.source_email}.",
                dry_run,
            )
        result = sync_catalogo_mestre_from_tenant(
            db=db,
            source_tenant_id=source_tenant_id,
            source_identifier=args.source_email,
            dry_run=dry_run,
            image_target=args.image_target,
        )
        if args.apply:
            db.commit()
        else:
            db.rollback()
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if result.get("ok", True) else 1
    except Exception as exc:
        db.rollback()
        return _fail(str(exc), dry_run)
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
