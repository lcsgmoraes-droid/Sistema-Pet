"""Auditoria read-only de consistencia financeira por tenant e periodo."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any
from uuid import UUID

if __package__ in {None, ""}:
    backend_path = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(backend_path))

from app.db import SessionLocal
from app.financeiro.auditoria_consistencia import auditar_financeiro_tenant


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audita inconsistencias financeiras em modo somente leitura."
    )
    parser.add_argument("--tenant-id", required=True, help="UUID do tenant alvo.")
    parser.add_argument(
        "--data-inicio",
        required=True,
        help="Data inicial inclusiva no formato YYYY-MM-DD.",
    )
    parser.add_argument(
        "--data-fim",
        required=True,
        help="Data final exclusiva no formato YYYY-MM-DD.",
    )
    parser.add_argument("--compact", action="store_true", help="Emite JSON compacto.")
    return parser


def _json_default(value: Any) -> Any:
    return str(value)


def _fail(message: str) -> int:
    print(
        json.dumps(
            {"ok": False, "mode": "read_only", "error": message},
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        file=sys.stderr,
    )
    return 1


def _parse_date(value: str, arg_name: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError(f"{arg_name} deve estar no formato YYYY-MM-DD.") from None


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    args = _build_parser().parse_args(argv)
    try:
        args.tenant_id = str(UUID(str(args.tenant_id)))
    except ValueError:
        raise ValueError("--tenant-id deve ser um UUID valido.") from None
    args.data_inicio = _parse_date(args.data_inicio, "--data-inicio")
    args.data_fim = _parse_date(args.data_fim, "--data-fim")
    if args.data_fim <= args.data_inicio:
        raise ValueError("--data-fim deve ser maior que --data-inicio.")
    return args


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parse_args(argv)
    except ValueError as exc:
        return _fail(str(exc))

    db = SessionLocal()
    try:
        payload = auditar_financeiro_tenant(
            db,
            tenant_id=args.tenant_id,
            data_inicio=args.data_inicio,
            data_fim=args.data_fim,
        )
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
        return _fail(str(exc))
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
