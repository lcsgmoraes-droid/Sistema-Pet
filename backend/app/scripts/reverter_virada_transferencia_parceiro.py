"""Simula ou reverte baixas de Transferencia Parceiro criadas pela virada."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import UUID

if __package__ in {None, ""}:
    backend_path = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(backend_path))

from app.db import SessionLocal
from app.financeiro.reversao_virada_transferencia_parceiro import (
    CONFIRM_TOKEN_REVERSAO_TRANSFERENCIA_PARCEIRO,
    reverter_virada_transferencia_parceiro,
)


PRODUCTION_ENVS = {"prod", "production"}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Simula ou reverte somente os recebimentos de Transferencia Parceiro "
            "criados pela virada bancaria na data informada."
        )
    )
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--data-virada", required=True, help="Data YYYY-MM-DD.")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--expected-count", type=int, default=None)
    parser.add_argument("--expected-total", default=None)
    parser.add_argument("--confirm-token", default=None)
    parser.add_argument("--allow-production-apply", action="store_true")
    parser.add_argument("--compact", action="store_true")
    return parser


def _environment_name() -> str:
    for name in ("APP_ENV", "ENVIRONMENT", "ENV"):
        value = os.getenv(name)
        if value:
            return value.strip().lower()
    return ""


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


def _validate_args(args: argparse.Namespace) -> tuple[str, date, Decimal | None]:
    try:
        tenant_id = str(UUID(str(args.tenant_id)))
    except ValueError:
        raise ValueError("--tenant-id deve ser um UUID valido.") from None
    try:
        data_virada = date.fromisoformat(str(args.data_virada))
    except ValueError:
        raise ValueError("--data-virada deve estar no formato YYYY-MM-DD.") from None

    expected_total = None
    if args.expected_total is not None:
        try:
            expected_total = Decimal(str(args.expected_total))
        except InvalidOperation:
            raise ValueError("--expected-total deve ser um numero decimal valido.") from None

    if args.apply:
        if args.confirm_token != CONFIRM_TOKEN_REVERSAO_TRANSFERENCIA_PARCEIRO:
            raise ValueError(
                "--confirm-token deve ser "
                f"{CONFIRM_TOKEN_REVERSAO_TRANSFERENCIA_PARCEIRO}."
            )
        if args.expected_count is None or expected_total is None:
            raise ValueError("--apply exige --expected-count e --expected-total.")
        if _environment_name() in PRODUCTION_ENVS and not args.allow_production_apply:
            raise ValueError(
                "Ambiente production/prod detectado; apply bloqueado sem "
                "--allow-production-apply."
            )
    return tenant_id, data_virada, expected_total


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        tenant_id, data_virada, expected_total = _validate_args(args)
    except ValueError as exc:
        return _fail(str(exc), dry_run=not args.apply)

    db = SessionLocal()
    try:
        payload = reverter_virada_transferencia_parceiro(
            db,
            tenant_id=tenant_id,
            data_virada=data_virada,
            apply=args.apply,
            confirm_token=args.confirm_token,
            expected_count=args.expected_count,
            expected_total=expected_total,
        )
    finally:
        db.close()

    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=None if args.compact else 2,
            sort_keys=True,
        )
    )
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
