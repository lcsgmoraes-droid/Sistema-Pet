import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ["DEBUG"] = "false"

from app.db import sql_audit


def test_sql_audit_accepts_runtime_level_aliases():
    assert sql_audit._normalize_enforcement_level("error") == ("HIGH", "ERROR")
    assert sql_audit._normalize_enforcement_level("warn") == ("HIGH", "WARN")
    assert sql_audit._normalize_enforcement_level("strict") == ("MEDIUM", "STRICT")
    assert sql_audit._normalize_enforcement_level("medium") == ("MEDIUM", "MEDIUM")


def test_sql_audit_config_exposes_environment_and_raw_level():
    config = sql_audit.get_enforcement_config()

    assert "enabled" in config
    assert config["level"] in {"HIGH", "MEDIUM", "LOW"}
    assert "raw_level" in config
    assert "environment" in config
