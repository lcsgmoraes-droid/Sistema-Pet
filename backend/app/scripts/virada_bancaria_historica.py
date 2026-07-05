"""Planeja ou executa virada bancaria historica por tenant.

Default mode is dry-run. Use --apply-baixas and/or --apply-saldo with explicit
guards to persist data.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from uuid import UUID

if __package__ in {None, ""}:
    backend_path = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(backend_path))

from app.db import SessionLocal
from app.financeiro.virada_bancaria_historica import (
    CONFIRM_TOKEN_VIRADA_BANCARIA,
    executar_virada_bancaria_historica,
)


PRODUCTION_ENVS = {"prod", "production"}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Planeja ou executa virada historica: baixa CR/CP ate uma data de "
            "corte sem movimentar banco, e opcionalmente define saldo real da "
            "conta bancaria."
        )
    )
    parser.add_argument("--tenant-id", required=True, help="UUID do tenant alvo.")
    parser.add_argument(
        "--data-corte",
        required=True,
        help="Data limite inclusiva para baixar CR/CP, no formato YYYY-MM-DD.",
    )
    parser.add_argument("--conta-bancaria-id", type=int, default=None)
    parser.add_argument("--saldo-real", default=None)
    parser.add_argument("--expected-saldo-atual", default=None)
    parser.add_argument(
        "--apply-baixas",
        action="store_true",
        help="Persiste baixas historicas de CR/CP ate a data de corte.",
    )
    parser.add_argument(
        "--apply-saldo",
        action="store_true",
        help="Persiste saldo_inicial/saldo_atual da conta bancaria informada.",
    )
    parser.add_argument(
        "--confirm-token",
        default=None,
        help=f"Token literal exigido em apply: {CONFIRM_TOKEN_VIRADA_BANCARIA}.",
    )
    parser.add_argument(
        "--allow-production-apply",
        action="store_true",
        help="Permite apply quando APP_ENV/ENV/ENVIRONMENT for production/prod.",
    )
    parser.add_argument("--compact", action="store_true", help="Emite JSON compacto.")
    return parser


def _environment_name() -> str:
    for name in ("APP_ENV", "ENVIRONMENT", "ENV"):
        value = os.getenv(name)
        if value:
            return value.strip().lower()
    return ""


def _parse_date(value: str, *, field: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        raise ValueError(f"{field} deve estar no formato YYYY-MM-DD.") from None


def _parse_decimal(value: str | None, *, field: str) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        raise ValueError(f"{field} deve ser um numero decimal valido.") from None


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return f"{value:.2f}"
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


def _validate_args(
    args: argparse.Namespace,
) -> tuple[str, date, Decimal | None, Decimal | None]:
    try:
        tenant_id = str(UUID(str(args.tenant_id)))
    except ValueError:
        raise ValueError("--tenant-id deve ser um UUID valido.") from None

    data_corte = _parse_date(args.data_corte, field="--data-corte")
    saldo_real = _parse_decimal(args.saldo_real, field="--saldo-real")
    expected_saldo_atual = _parse_decimal(
        args.expected_saldo_atual, field="--expected-saldo-atual"
    )

    has_apply = bool(args.apply_baixas or args.apply_saldo)
    if not has_apply:
        return tenant_id, data_corte, saldo_real, expected_saldo_atual

    if args.confirm_token != CONFIRM_TOKEN_VIRADA_BANCARIA:
        raise ValueError(f"--confirm-token deve ser {CONFIRM_TOKEN_VIRADA_BANCARIA}.")

    environment = _environment_name()
    if environment in PRODUCTION_ENVS and not args.allow_production_apply:
        raise ValueError(
            "Ambiente production/prod detectado; apply bloqueado sem --allow-production-apply."
        )

    if args.apply_saldo:
        if args.conta_bancaria_id is None:
            raise ValueError("--conta-bancaria-id e obrigatorio com --apply-saldo.")
        if saldo_real is None:
            raise ValueError("--saldo-real e obrigatorio com --apply-saldo.")
        if expected_saldo_atual is None:
            raise ValueError("--expected-saldo-atual e obrigatorio com --apply-saldo.")

    return tenant_id, data_corte, saldo_real, expected_saldo_atual


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    dry_run = not bool(args.apply_baixas or args.apply_saldo)

    try:
        tenant_id, data_corte, saldo_real, expected_saldo_atual = _validate_args(args)
    except ValueError as exc:
        return _fail(str(exc), dry_run=dry_run)

    db = SessionLocal()
    try:
        payload = executar_virada_bancaria_historica(
            db,
            tenant_id=tenant_id,
            data_corte=data_corte,
            conta_bancaria_id=args.conta_bancaria_id,
            saldo_real=saldo_real,
            expected_saldo_atual=expected_saldo_atual,
            apply_baixas=args.apply_baixas,
            apply_saldo=args.apply_saldo,
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
