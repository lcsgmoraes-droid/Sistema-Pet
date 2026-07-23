"""CLI segura para atualizar a fila revisavel de evidencia veterinaria."""

from __future__ import annotations

import argparse
import json
import os

from app import models as _models  # noqa: F401
from app import produtos_models as _produtos_models  # noqa: F401
from app.db import SessionLocal
from app.services.vet_clinical_evidence import (
    PUBMED_DEFAULT_QUERY,
    sync_pubmed_veterinary_evidence,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persiste em quarentena. Sem esta opcao, executa dry-run.",
    )
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--query", default=PUBMED_DEFAULT_QUERY)
    parser.add_argument(
        "--allow-production",
        action="store_true",
        help="Override adicional; ainda requer autorizacao operacional.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    environment = (os.getenv("ENVIRONMENT") or "development").strip().lower()
    if (
        args.apply
        and environment in {"prod", "production"}
        and not args.allow_production
    ):
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "Sincronizacao em producao bloqueada sem --allow-production.",
                },
                ensure_ascii=False,
            )
        )
        return 2

    db = SessionLocal()
    try:
        result = sync_pubmed_veterinary_evidence(
            db,
            dry_run=not args.apply,
            query=args.query,
            limit=args.limit,
            api_key=os.getenv("NCBI_API_KEY"),
            email=os.getenv("NCBI_EMAIL"),
        )
        if args.apply:
            db.commit()
        else:
            db.rollback()
        print(json.dumps({"ok": True, **result}, ensure_ascii=False))
        return 0
    except Exception as exc:
        db.rollback()
        print(
            json.dumps(
                {"ok": False, "error": exc.__class__.__name__},
                ensure_ascii=False,
            )
        )
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
