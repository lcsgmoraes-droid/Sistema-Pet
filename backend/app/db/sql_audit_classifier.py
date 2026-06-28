"""Risk classification helpers for SQL raw-query auditing."""

import re
from typing import List, Tuple

from app.db.sql_audit_tables import TENANT_TABLES, WHITELIST_TABLES


def extract_table_names(sql: str) -> List[str]:
    """Extract table names from common SQL clauses using lightweight regexes."""
    sql_lower = sql.lower()
    tables = []

    patterns = [
        r"\bfrom\s+(\w+)",
        r"\bjoin\s+(\w+)",
        r"\binto\s+(\w+)",
        r"\bupdate\s+(\w+)",
    ]

    for pattern in patterns:
        matches = re.findall(pattern, sql_lower)
        tables.extend(matches)

    tables = [table for table in tables if len(table) >= 3]

    seen = set()
    unique_tables = []
    for table in tables:
        if table not in seen:
            seen.add(table)
            unique_tables.append(table)

    return unique_tables


def classify_raw_sql_risk(
    sql: str, has_tenant_filter: bool = False
) -> Tuple[str, List[str]]:
    """Classify a raw SQL statement as HIGH, MEDIUM, or LOW risk."""
    sql_lower = sql.lower().strip()
    tables = extract_table_names(sql)

    if any(
        pattern in sql_lower
        for pattern in [
            "select 1",
            "select version()",
            "show server_version",
            "pg_is_in_recovery",
        ]
    ):
        return ("LOW", [])

    if any(
        pattern in sql_lower
        for pattern in [
            "pg_catalog",
            "information_schema",
            "pg_stat_",
            "pg_class",
        ]
    ):
        return ("LOW", tables)

    if sql_lower in ["begin", "commit", "rollback", "savepoint"]:
        return ("LOW", [])

    if "alembic_version" in sql_lower:
        return ("LOW", ["alembic_version"])

    tenant_tables_touched = [table for table in tables if table in TENANT_TABLES]
    if tenant_tables_touched and not has_tenant_filter:
        return ("HIGH", tenant_tables_touched)

    whitelist_tables_touched = [table for table in tables if table in WHITELIST_TABLES]
    if whitelist_tables_touched:
        return ("MEDIUM", whitelist_tables_touched)

    if any(
        pattern in sql_lower
        for pattern in [
            "create table",
            "alter table",
            "drop table",
            "create index",
            "drop index",
        ]
    ):
        return ("MEDIUM", tables)

    if "with " in sql_lower or "cte" in sql_lower:
        return ("MEDIUM", tables)

    if not tables:
        return ("MEDIUM", [])

    return ("MEDIUM", tables)


def is_raw_sql_text(statement: str) -> bool:
    """Return true when a SQLAlchemy statement looks hand-written."""
    if not statement:
        return False

    statement_lower = statement.lower().strip()

    raw_sql_indicators = [
        "-- ",
        "/* ",
        "with ",
        "::text",
        "::jsonb",
        "coalesce(",
        "array_agg(",
        "string_agg(",
        "json_build_object(",
    ]

    for indicator in raw_sql_indicators:
        if indicator in statement_lower:
            return True

    return False


def should_audit_statement(statement: str) -> bool:
    """Return true when a statement should go through raw SQL auditing."""
    if not statement or len(statement.strip()) < 10:
        return False

    statement_lower = statement.lower()

    ignore_patterns = [
        "pg_catalog",
        "information_schema",
        "pg_stat_",
        "pg_class",
        "alembic_version",
        "select version()",
        "show server_version",
        "set time zone",
        "begin",
        "commit",
        "rollback",
        "savepoint",
    ]

    for pattern in ignore_patterns:
        if pattern in statement_lower:
            return False

    return True
