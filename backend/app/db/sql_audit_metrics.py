"""In-memory metrics for SQL raw-query auditing."""

import logging
from datetime import datetime
from typing import List


logger = logging.getLogger("sql_audit")

SQL_AUDIT_STATS = {
    "total": 0,
    "HIGH": 0,
    "MEDIUM": 0,
    "LOW": 0,
    "by_file": {},
    "by_table": {},
    "last_snapshot": None,
}

SNAPSHOT_INTERVAL = 50


def increment_stats(
    risk_level: str, tables_detected: List[str], file_origin: str
) -> None:
    """Increment the in-memory SQL audit counters."""
    SQL_AUDIT_STATS["total"] += 1

    if risk_level in SQL_AUDIT_STATS:
        SQL_AUDIT_STATS[risk_level] += 1

    if file_origin:
        if file_origin not in SQL_AUDIT_STATS["by_file"]:
            SQL_AUDIT_STATS["by_file"][file_origin] = 0
        SQL_AUDIT_STATS["by_file"][file_origin] += 1

    for table in tables_detected:
        if table not in SQL_AUDIT_STATS["by_table"]:
            SQL_AUDIT_STATS["by_table"][table] = 0
        SQL_AUDIT_STATS["by_table"][table] += 1


def log_snapshot() -> None:
    """Log a snapshot of accumulated audit metrics."""
    total = SQL_AUDIT_STATS["total"]

    if total == 0:
        return

    high_pct = (SQL_AUDIT_STATS["HIGH"] / total * 100) if total > 0 else 0
    medium_pct = (SQL_AUDIT_STATS["MEDIUM"] / total * 100) if total > 0 else 0
    low_pct = (SQL_AUDIT_STATS["LOW"] / total * 100) if total > 0 else 0

    top_files = sorted(
        SQL_AUDIT_STATS["by_file"].items(), key=lambda item: item[1], reverse=True
    )[:5]
    top_tables = sorted(
        SQL_AUDIT_STATS["by_table"].items(), key=lambda item: item[1], reverse=True
    )[:5]

    SQL_AUDIT_STATS["last_snapshot"] = datetime.utcnow().isoformat()

    logger.warning(
        "SQL AUDIT SNAPSHOT",
        extra={
            "event": "sql_audit_snapshot",
            "timestamp": SQL_AUDIT_STATS["last_snapshot"],
            "total_queries": total,
            "high_count": SQL_AUDIT_STATS["HIGH"],
            "medium_count": SQL_AUDIT_STATS["MEDIUM"],
            "low_count": SQL_AUDIT_STATS["LOW"],
            "top_files": dict(top_files),
            "top_tables": dict(top_tables),
        },
    )

    files_str = (
        "\n    ".join(
            [
                f"{index + 1}. {file}: {count} queries"
                for index, (file, count) in enumerate(top_files)
            ]
        )
        if top_files
        else "none"
    )

    tables_str = (
        "\n    ".join(
            [
                f"{index + 1}. {table}: {count} accesses"
                for index, (table, count) in enumerate(top_tables)
            ]
        )
        if top_tables
        else "none"
    )

    logger.warning(
        f"\n"
        f"{'=' * 80}\n"
        f"SQL AUDIT SNAPSHOT - {total} queries audited\n"
        f"{'=' * 80}\n"
        f"By Risk Level:\n"
        f"  HIGH:   {SQL_AUDIT_STATS['HIGH']:3d} ({high_pct:5.1f}%)\n"
        f"  MEDIUM: {SQL_AUDIT_STATS['MEDIUM']:3d} ({medium_pct:5.1f}%)\n"
        f"  LOW:    {SQL_AUDIT_STATS['LOW']:3d} ({low_pct:5.1f}%)\n"
        f"\n"
        f"Top Files:\n"
        f"    {files_str}\n"
        f"\n"
        f"Top Tables:\n"
        f"    {tables_str}\n"
        f"{'=' * 80}\n"
    )


def build_audit_stats(listener_registered: bool) -> dict:
    """Build the public stats payload returned by the audit module."""
    stats = SQL_AUDIT_STATS.copy()
    stats["status"] = "active"
    stats["listener_registered"] = listener_registered
    stats["top_files"] = sorted(
        SQL_AUDIT_STATS["by_file"].items(), key=lambda item: item[1], reverse=True
    )[:10]
    stats["top_tables"] = sorted(
        SQL_AUDIT_STATS["by_table"].items(), key=lambda item: item[1], reverse=True
    )[:10]
    return stats


def reset_stats() -> None:
    """Reset all accumulated audit metrics."""
    SQL_AUDIT_STATS["total"] = 0
    SQL_AUDIT_STATS["HIGH"] = 0
    SQL_AUDIT_STATS["MEDIUM"] = 0
    SQL_AUDIT_STATS["LOW"] = 0
    SQL_AUDIT_STATS["by_file"] = {}
    SQL_AUDIT_STATS["by_table"] = {}
    SQL_AUDIT_STATS["last_snapshot"] = None
    logger.info("SQL Audit stats reset")
