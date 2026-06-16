"""Safely update a user's login email.

Default mode is dry-run. Use --apply to persist data.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import inspect, text

if __package__ in {None, ""}:
    backend_path = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(backend_path))

from app.db import SessionLocal


PRODUCTION_ENVS = {"prod", "production"}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Troca o e-mail de login de um usuario sem alterar seus dados."
    )
    parser.add_argument("--old-email", required=True, help="E-mail atual do usuario.")
    parser.add_argument("--new-email", required=True, help="Novo e-mail do usuario.")
    parser.add_argument(
        "--expected-tenant-id",
        help="Opcional: bloqueia a troca se o usuario atual nao pertencer a este tenant.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persiste a troca. Sem esta flag, executa apenas dry-run.",
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


def _normalize_email(value: str) -> str:
    email = str(value or "").strip().lower()
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise ValueError(f"E-mail invalido: {value}")
    return email


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


def _columns(db) -> set[str]:
    return {column["name"] for column in inspect(db.connection()).get_columns("users")}


def _user_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row.get("id"),
        "email": row.get("email"),
        "tenant_id": str(row.get("tenant_id"))
        if row.get("tenant_id") is not None
        else None,
        "nome": row.get("nome"),
        "is_active": row.get("is_active"),
        "is_admin": row.get("is_admin"),
        "email_verified": row.get("email_verified"),
    }


def _fetch_user_by_email(db, email: str, columns: set[str]) -> dict[str, Any] | None:
    select_columns = [
        "id",
        "email",
        "tenant_id",
        "nome" if "nome" in columns else "NULL AS nome",
        "is_active" if "is_active" in columns else "NULL AS is_active",
        "is_admin" if "is_admin" in columns else "NULL AS is_admin",
        "email_verified" if "email_verified" in columns else "NULL AS email_verified",
    ]
    row = (
        db.execute(
            text(
                f"""
            SELECT {", ".join(select_columns)}
            FROM users
            WHERE lower(email) = lower(:email)
            ORDER BY id ASC
            LIMIT 1
            """
            ),
            {"email": email},
        )
        .mappings()
        .first()
    )
    return dict(row) if row else None


def _build_update_sql(columns: set[str]) -> str:
    assignments = ["email = :new_email"]
    if "updated_at" in columns:
        assignments.append("updated_at = CURRENT_TIMESTAMP")

    # Pending old-email tokens should not survive an identity change.
    nullable_token_columns = [
        "email_verification_token_hash",
        "email_verification_token_expires",
        "email_verification_sent_at",
        "reset_token",
        "reset_token_expires",
    ]
    assignments.extend(
        f"{column} = NULL" for column in nullable_token_columns if column in columns
    )

    return f"""
        UPDATE users
        SET {", ".join(assignments)}
        WHERE id = :user_id
    """


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    dry_run = not args.apply

    try:
        old_email = _normalize_email(args.old_email)
        new_email = _normalize_email(args.new_email)
    except ValueError as exc:
        return _fail(str(exc), dry_run=dry_run)

    if old_email == new_email:
        return _fail("O e-mail novo e igual ao e-mail atual.", dry_run=dry_run)

    environment = _environment_name()
    if (
        args.apply
        and environment in PRODUCTION_ENVS
        and not args.allow_production_apply
    ):
        return _fail(
            "Ambiente production/prod detectado; --apply bloqueado sem --allow-production-apply.",
            dry_run=False,
        )

    db = SessionLocal()
    try:
        columns = _columns(db)
        if "email" not in columns:
            db.rollback()
            return _fail("Tabela users sem coluna email.", dry_run=dry_run)

        current = _fetch_user_by_email(db, old_email, columns)
        if not current:
            db.rollback()
            return _fail(f"Usuario atual nao encontrado: {old_email}.", dry_run=dry_run)

        if args.expected_tenant_id:
            expected_tenant_id = str(args.expected_tenant_id).strip()
            current_tenant_id = str(current.get("tenant_id") or "")
            if current_tenant_id != expected_tenant_id:
                db.rollback()
                return _fail(
                    f"Tenant divergente para {old_email}: esperado {expected_tenant_id}, encontrado {current_tenant_id}.",
                    dry_run=dry_run,
                )

        existing = _fetch_user_by_email(db, new_email, columns)
        if existing:
            db.rollback()
            return _fail(
                f"Novo e-mail ja esta em uso pelo usuario #{existing['id']}: {new_email}.",
                dry_run=dry_run,
            )

        db.execute(
            text(_build_update_sql(columns)),
            {"new_email": new_email, "user_id": current["id"]},
        )
        updated = _fetch_user_by_email(db, new_email, columns)

        if args.apply:
            db.commit()
        else:
            db.rollback()

        print(
            json.dumps(
                {
                    "ok": True,
                    "dry_run": dry_run,
                    "changed_fields": ["email"],
                    "cleared_pending_tokens": True,
                    "before": _user_payload(current),
                    "after": _user_payload(updated or {**current, "email": new_email}),
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
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
