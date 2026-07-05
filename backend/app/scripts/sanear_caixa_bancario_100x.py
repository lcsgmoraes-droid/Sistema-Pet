"""Diagnostica e saneia movimentos bancarios gravados 100x maiores.

Default mode is dry-run. Use --apply with explicit guards to persist data.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import text

if __package__ in {None, ""}:
    backend_path = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(backend_path))

from app.db import SessionLocal
from app.financeiro.saneamento_caixa_bancario import (
    CONFIRM_TOKEN_100X,
    sanear_movimentos_100x,
)


PRODUCTION_ENVS = {"prod", "production"}
CENT = Decimal("0.01")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Diagnostica ou normaliza movimentacoes_financeiras de conta_pagar "
            "gravadas em escala 100x."
        )
    )
    parser.add_argument("--tenant-id", required=True, help="UUID do tenant alvo.")
    parser.add_argument(
        "--conta-bancaria-id",
        type=int,
        default=None,
        help="Conta bancaria alvo. Obrigatoria no modo --apply.",
    )
    parser.add_argument(
        "--expected-saldo-atual",
        default=None,
        help="Saldo atual esperado da conta antes do apply, em reais.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persiste a normalizacao. Sem esta flag executa apenas dry-run.",
    )
    parser.add_argument(
        "--confirm-token",
        default=None,
        help=f"Token literal exigido no apply: {CONFIRM_TOKEN_100X}.",
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


def _money(value: Any) -> Decimal:
    return Decimal(str(value or 0)).quantize(CENT, rounding=ROUND_HALF_UP)


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


def _validate_args(args: argparse.Namespace) -> str | None:
    try:
        tenant_id = str(UUID(str(args.tenant_id)))
    except ValueError:
        raise ValueError("--tenant-id deve ser um UUID valido.") from None

    if not args.apply:
        return tenant_id

    if args.conta_bancaria_id is None:
        raise ValueError("--conta-bancaria-id e obrigatorio no modo --apply.")
    if args.confirm_token != CONFIRM_TOKEN_100X:
        raise ValueError(f"--confirm-token deve ser {CONFIRM_TOKEN_100X}.")
    if args.expected_saldo_atual is None:
        raise ValueError("--expected-saldo-atual e obrigatorio no modo --apply.")

    environment = _environment_name()
    if environment in PRODUCTION_ENVS and not args.allow_production_apply:
        raise ValueError(
            "Ambiente production/prod detectado; --apply bloqueado sem --allow-production-apply."
        )

    return tenant_id


def _fetch_saldo_atual(db, *, tenant_id: str, conta_bancaria_id: int) -> Decimal:
    row = (
        db.execute(
            text(
                """
                SELECT saldo_atual
                FROM contas_bancarias
                WHERE CAST(tenant_id AS TEXT) = :tenant_id
                  AND id = :conta_bancaria_id
                """
            ),
            {"tenant_id": tenant_id, "conta_bancaria_id": conta_bancaria_id},
        )
        .mappings()
        .first()
    )
    if not row:
        raise ValueError(
            f"Conta bancaria {conta_bancaria_id} nao encontrada no tenant {tenant_id}."
        )
    return _money(row["saldo_atual"])


def _validate_expected_saldo(db, args: argparse.Namespace, tenant_id: str) -> None:
    if not args.apply:
        return
    atual = _fetch_saldo_atual(
        db, tenant_id=tenant_id, conta_bancaria_id=args.conta_bancaria_id
    )
    esperado = _money(args.expected_saldo_atual)
    if atual != esperado:
        raise ValueError(
            "Saldo atual divergente antes do apply: "
            f"esperado {esperado:.2f}, encontrado {atual:.2f}."
        )


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    dry_run = not args.apply

    try:
        tenant_id = _validate_args(args)
    except ValueError as exc:
        return _fail(str(exc), dry_run=dry_run)

    db = SessionLocal()
    try:
        _validate_expected_saldo(db, args, tenant_id)
        payload = sanear_movimentos_100x(
            db,
            tenant_id=tenant_id,
            conta_bancaria_id=args.conta_bancaria_id,
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
