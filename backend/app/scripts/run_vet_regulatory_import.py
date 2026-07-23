"""CLI segura para atualizar o catalogo regulatorio veterinario global."""

from __future__ import annotations

import argparse
import json
import os

from app import models as _models  # noqa: F401 - registra relacionamentos ORM
from app import produtos_models as _produtos_models  # noqa: F401
from app.db import SessionLocal
from app.services.vet_regulatory_catalog_import import (
    import_dailymed_animal_labels,
    import_vmd_authorised_products,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persiste as alteracoes. Sem esta opcao, executa somente dry-run.",
    )
    parser.add_argument(
        "--source",
        choices=("all", "dailymed", "vmd"),
        default="all",
        help="Fonte oficial a sincronizar.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Limite por tipo de bula para teste controlado.",
    )
    parser.add_argument(
        "--limit-vmd",
        type=int,
        default=None,
        help="Limite de produtos VMD para teste controlado.",
    )
    parser.add_argument(
        "--allow-production",
        action="store_true",
        help="Override explicito adicional; ainda requer autorizacao operacional.",
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
                    "error": "Importacao em producao bloqueada sem --allow-production.",
                },
                ensure_ascii=False,
            )
        )
        return 2

    db = SessionLocal()
    try:
        results = []
        if args.source in {"all", "dailymed"}:
            results.append(
                import_dailymed_animal_labels(
                    db,
                    dry_run=not args.apply,
                    max_pages=args.max_pages,
                )
            )
        if args.source in {"all", "vmd"}:
            results.append(
                import_vmd_authorised_products(
                    db,
                    dry_run=not args.apply,
                    limit=args.limit_vmd,
                )
            )
        if args.apply:
            db.commit()
        else:
            db.rollback()
        print(json.dumps({"ok": True, "results": results}, ensure_ascii=False))
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
