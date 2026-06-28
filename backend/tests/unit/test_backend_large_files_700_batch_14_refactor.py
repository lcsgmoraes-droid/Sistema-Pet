import os
from pathlib import Path


os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ["DEBUG"] = "false"


BACKEND_ROOT = Path(__file__).resolve().parents[2]
SQL_AUDIT_MODULES = [
    "app/db/sql_audit.py",
    "app/db/sql_audit_config.py",
    "app/db/sql_audit_tables.py",
    "app/db/sql_audit_classifier.py",
    "app/db/sql_audit_metrics.py",
]


def _source(relative: str) -> str:
    return (BACKEND_ROOT / relative).read_text(encoding="utf-8")


def _line_count(relative: str) -> int:
    return len(_source(relative).splitlines())


def test_sql_audit_batch_14_modules_ficam_abaixo_de_700_linhas():
    assert {relative: _line_count(relative) for relative in SQL_AUDIT_MODULES} == {
        relative: count
        for relative in SQL_AUDIT_MODULES
        if (count := _line_count(relative)) <= 700
    }


def test_sql_audit_fachada_preserva_imports_publicos():
    from app.db import sql_audit
    from app.db import sql_audit_classifier
    from app.db import sql_audit_config
    from app.db import sql_audit_metrics
    from app.db import sql_audit_tables

    assert sql_audit.TENANT_TABLES is sql_audit_tables.TENANT_TABLES
    assert sql_audit.WHITELIST_TABLES is sql_audit_tables.WHITELIST_TABLES
    assert sql_audit.SQL_AUDIT_STATS is sql_audit_metrics.SQL_AUDIT_STATS
    assert sql_audit.SNAPSHOT_INTERVAL == sql_audit_metrics.SNAPSHOT_INTERVAL
    assert (
        sql_audit._normalize_enforcement_level
        is sql_audit_config.normalize_enforcement_level
    )
    assert sql_audit._extract_table_names is sql_audit_classifier.extract_table_names
    assert sql_audit._is_raw_sql_text is sql_audit_classifier.is_raw_sql_text
    assert (
        sql_audit._should_audit_statement is sql_audit_classifier.should_audit_statement
    )


def test_sql_audit_classificacao_e_metricas_continuam_compativeis():
    from app.db import sql_audit

    risk_level, tables = sql_audit.classify_raw_sql_risk(
        "SELECT * FROM vendas WHERE id = 1"
    )

    assert risk_level == "HIGH"
    assert tables == ["vendas"]

    sql_audit.reset_audit_stats()
    sql_audit._increment_stats("HIGH", ["vendas"], "legacy.py")

    stats = sql_audit.get_audit_stats()
    assert stats["total"] == 1
    assert stats["HIGH"] == 1
    assert stats["top_files"] == [("legacy.py", 1)]
    assert stats["top_tables"] == [("vendas", 1)]
