"""CLI para sanear contas de NF historicas que nao devem afetar DRE."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

if __package__ in {None, ""}:
    backend_path = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(backend_path))

from app.db import SessionLocal
from app.financeiro.saneamento_nf_dre_historico import (
    CONFIRM_TOKEN_NF_DRE_HISTORICO,
    sanear_contas_pagar_nf_dre_historico,
)


PRODUCTION_ENVS = {"prod", "production"}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Diagnostica ou blinda contas a pagar historicas de NF para nao "
            "afetarem DRE."
        )
    )
    parser.add_argument("--tenant-id", required=True, help="UUID do tenant alvo.")
    parser.add_argument(
        "--data-inicio",
        required=True,
        help="Inicio do periodo por data_emissao, no formato YYYY-MM-DD.",
    )
    parser.add_argument(
        "--data-fim",
        required=True,
        help="Fim exclusivo do periodo por data_emissao, no formato YYYY-MM-DD.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persiste a blindagem. Sem esta flag executa apenas dry-run.",
    )
    parser.add_argument(
        "--confirm-token",
        default=None,
        help=f"Token literal exigido no apply: {CONFIRM_TOKEN_NF_DRE_HISTORICO}.",
    )
    parser.add_argument(
        "--allow-production-apply",
        action="store_true",
        help="Permite --apply quando APP_ENV/ENV/ENVIRONMENT for production/prod.",
    )
    parser.add_argument("--compact", action="store_true", help="Emite JSON compacto.")
    return parser


def _environment_name() -> str:
    for name in ("APP_ENV", "ENVIRONMENT", "ENV"):
        value = os.getenv(name)
        if value:
            return value.strip().lower()
    return ""


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return f"{value:.2f}"
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _fail(message: str, *, dry_run: bool) -> int:
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


def _parse_date(raw: str, name: str) -> date:
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise ValueError(f"{name} deve estar no formato YYYY-MM-DD.") from None


def _validate_args(args: argparse.Namespace) -> tuple[str, date, date]:
    try:
        tenant_id = str(UUID(str(args.tenant_id)))
    except ValueError:
        raise ValueError("--tenant-id deve ser um UUID valido.") from None

    data_inicio = _parse_date(args.data_inicio, "--data-inicio")
    data_fim = _parse_date(args.data_fim, "--data-fim")
    if data_fim <= data_inicio:
        raise ValueError("--data-fim deve ser posterior a --data-inicio.")

    if not args.apply:
        return tenant_id, data_inicio, data_fim

    if args.confirm_token != CONFIRM_TOKEN_NF_DRE_HISTORICO:
        raise ValueError(f"--confirm-token deve ser {CONFIRM_TOKEN_NF_DRE_HISTORICO}.")

    environment = _environment_name()
    if environment in PRODUCTION_ENVS and not args.allow_production_apply:
        raise ValueError(
            "Ambiente production/prod detectado; --apply bloqueado sem --allow-production-apply."
        )

    return tenant_id, data_inicio, data_fim


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    dry_run = not args.apply

    try:
        tenant_id, data_inicio, data_fim = _validate_args(args)
    except ValueError as exc:
        return _fail(str(exc), dry_run=dry_run)

    db = SessionLocal()
    try:
        payload = sanear_contas_pagar_nf_dre_historico(
            db,
            tenant_id=tenant_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            apply_changes=args.apply,
            confirm_token=args.confirm_token,
        )
        if not payload.get("ok", False):
            print(
                json.dumps(
                    payload,
                    ensure_ascii=False,
                    indent=None if args.compact else 2,
                    sort_keys=True,
                    default=_json_default,
                ),
                file=sys.stderr,
            )
            return 1

        print(
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=None if args.compact else 2,
                sort_keys=True,
                default=_json_default,
            )
        )
        return 0
    except Exception as exc:
        db.rollback()
        return _fail(str(exc), dry_run=dry_run)
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
