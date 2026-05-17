#!/usr/bin/env python3
"""Run Alembic smoke checks against disposable PostgreSQL databases.

The script validates two paths:
- a clean database upgraded directly to head;
- a controlled historical revision upgraded to head.

It is intentionally PostgreSQL-only because production runs PostgreSQL and some
migrations use PostgreSQL-specific DDL.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import psycopg2
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy import create_engine


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
DEFAULT_HISTORY_REVISION = "oj20260515a1"
DB_NAME_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]{0,62}$")


@dataclass(frozen=True)
class SmokeDatabase:
    label: str
    name: str
    start_revision: str | None


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "sim", "on"}


def _database_url() -> URL:
    raw_url = os.getenv("MIGRATION_SMOKE_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not raw_url:
        raise SystemExit("DATABASE_URL or MIGRATION_SMOKE_DATABASE_URL is required")

    url = make_url(raw_url)
    if not url.drivername.startswith("postgresql"):
        raise SystemExit(
            "Migration smoke requires PostgreSQL; got driver "
            f"{url.drivername!r}"
        )
    return url


def _psycopg2_connect_kwargs(url: URL, database: str) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "dbname": database,
        "user": url.username,
        "password": url.password,
        "host": url.host or "localhost",
        "port": url.port or 5432,
    }
    return {key: value for key, value in kwargs.items() if value is not None}


def _quote_identifier(name: str) -> str:
    if not DB_NAME_RE.match(name):
        raise SystemExit(f"Unsafe temporary database name: {name!r}")
    return f'"{name}"'


def _admin_database(url: URL) -> str:
    return os.getenv("MIGRATION_SMOKE_ADMIN_DB") or "postgres"


def _prepare_database(admin_url: URL, name: str) -> None:
    quoted = _quote_identifier(name)
    conn = psycopg2.connect(**_psycopg2_connect_kwargs(admin_url, _admin_database(admin_url)))
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                "SELECT pg_terminate_backend(pid) "
                "FROM pg_stat_activity "
                "WHERE datname = %s AND pid <> pg_backend_pid()",
                (name,),
            )
            cur.execute(f"DROP DATABASE IF EXISTS {quoted}")
            cur.execute(f"CREATE DATABASE {quoted} TEMPLATE template0 ENCODING 'UTF8'")
    finally:
        conn.close()


def _drop_database(admin_url: URL, name: str) -> None:
    quoted = _quote_identifier(name)
    conn = psycopg2.connect(**_psycopg2_connect_kwargs(admin_url, _admin_database(admin_url)))
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                "SELECT pg_terminate_backend(pid) "
                "FROM pg_stat_activity "
                "WHERE datname = %s AND pid <> pg_backend_pid()",
                (name,),
            )
            cur.execute(f"DROP DATABASE IF EXISTS {quoted}")
    finally:
        conn.close()


def _run_alembic(database_url: URL, *args: str) -> None:
    env = os.environ.copy()
    env.update(
        {
            "DATABASE_URL": database_url.render_as_string(hide_password=False),
            "ENVIRONMENT": "testing",
            "ENV": "testing",
            "DEBUG": "false",
            "JWT_SECRET_KEY": "migration-smoke-secret-key-with-more-than-32-characters",
            "EMAIL_VERIFICATION_REQUIRED": "false",
            "BLING_SYNC_SCHEDULER_ENABLED": "false",
            "SEFAZ_IMPORTACAO_AUTOMATICA": "false",
        }
    )
    subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND_DIR,
        env=env,
        check=True,
    )


def _expected_head(database_url: URL) -> str:
    env = os.environ.copy()
    env.setdefault("DATABASE_URL", database_url.render_as_string(hide_password=False))
    env.setdefault("ENVIRONMENT", "testing")
    env.setdefault("ENV", "testing")
    env.setdefault(
        "JWT_SECRET_KEY",
        "migration-smoke-secret-key-with-more-than-32-characters",
    )
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "heads"],
        cwd=BACKEND_DIR,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    heads = [line.split()[0].strip() for line in result.stdout.splitlines() if line.strip()]
    if len(heads) != 1:
        raise SystemExit(f"Expected exactly one Alembic head, got: {heads}")
    return heads[0]


def _assert_database_at_head(database_url: URL, expected_head: str) -> None:
    engine = create_engine(database_url)
    try:
        with engine.connect() as conn:
            current = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
            table_count = conn.execute(
                text(
                    "SELECT count(*) FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
                )
            ).scalar()
    finally:
        engine.dispose()

    if current != expected_head:
        raise SystemExit(f"Expected Alembic head {expected_head}, got {current}")
    if int(table_count or 0) < 20:
        raise SystemExit(f"Expected migrated schema, got only {table_count} tables")


def _database_plan() -> list[SmokeDatabase]:
    prefix = os.getenv("MIGRATION_SMOKE_DB_PREFIX", "petshop_migration_smoke")
    history_revision = os.getenv("MIGRATION_SMOKE_HISTORY_REVISION", DEFAULT_HISTORY_REVISION)
    return [
        SmokeDatabase("clean", f"{prefix}_clean", None),
        SmokeDatabase("history", f"{prefix}_history", history_revision),
    ]


def main() -> int:
    base_url = _database_url()
    expected_head = _expected_head(base_url)
    keep_databases = _env_bool("MIGRATION_SMOKE_KEEP_DATABASES")

    print(f"migration_smoke_expected_head={expected_head}")

    for database in _database_plan():
        target_url = base_url.set(database=database.name)
        print(f"migration_smoke_start label={database.label} database={database.name}")
        _prepare_database(base_url, database.name)
        try:
            if database.start_revision:
                print(
                    "migration_smoke_upgrade "
                    f"label={database.label} target={database.start_revision}"
                )
                _run_alembic(target_url, "upgrade", database.start_revision)

            print(f"migration_smoke_upgrade label={database.label} target=head")
            _run_alembic(target_url, "upgrade", "head")
            _assert_database_at_head(target_url, expected_head)
            print(f"migration_smoke_status label={database.label} status=ok")
        finally:
            if keep_databases:
                print(f"migration_smoke_keep database={database.name}")
            else:
                _drop_database(base_url, database.name)

    print("migration_smoke_status=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
