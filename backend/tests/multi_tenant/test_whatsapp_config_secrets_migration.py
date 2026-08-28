import runpy
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
import sqlalchemy as sa

from app.security.tenant_config_crypto import SECRET_PREFIX, decrypt_secret


MIGRATION_FILE = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "zxk20260828a1_encrypt_whatsapp_config_secrets.py"
)
ENCRYPTED_COLUMNS = {
    "api_key_encrypted": "dialog-secret",
    "webhook_secret_encrypted": "webhook-secret",
    "openai_api_key_encrypted": "openai-secret",
}


def _load_migration():
    return runpy.run_path(str(MIGRATION_FILE))


def _run_action(connection, migration, action_name: str) -> None:
    operations = Operations(MigrationContext.configure(connection))
    migration[action_name].__globals__["op"] = operations
    migration[action_name]()


def _create_legacy_table(connection) -> None:
    connection.execute(
        sa.text("""
            CREATE TABLE tenant_whatsapp_config (
                id INTEGER PRIMARY KEY,
                api_key TEXT,
                webhook_secret TEXT,
                openai_api_key TEXT
            )
            """)
    )
    connection.execute(
        sa.text("""
            INSERT INTO tenant_whatsapp_config (
                id, api_key, webhook_secret, openai_api_key
            ) VALUES (
                1, 'dialog-secret', 'webhook-secret', 'openai-secret'
            )
            """)
    )


def test_migration_metadata_and_rls_protection_are_explicit():
    source = MIGRATION_FILE.read_text(encoding="utf-8")

    assert 'revision = "zxk20260828a1"' in source
    assert 'down_revision = "zxj20260827a1"' in source
    assert "NO FORCE ROW LEVEL SECURITY" in source
    assert "DISABLE ROW LEVEL SECURITY" in source
    assert "ENABLE ROW LEVEL SECURITY" in source
    assert "FORCE ROW LEVEL SECURITY" in source


def test_upgrade_encrypts_existing_values_and_downgrade_restores_them(monkeypatch):
    monkeypatch.setenv("PAYMENT_CONFIG_ENCRYPTION_KEY", "migration-test-master-key")
    engine = sa.create_engine("sqlite://")
    migration = _load_migration()

    with engine.begin() as connection:
        _create_legacy_table(connection)
        _run_action(connection, migration, "upgrade")

        columns = {
            column["name"]
            for column in sa.inspect(connection).get_columns("tenant_whatsapp_config")
        }
        row = (
            connection.execute(
                sa.text("SELECT * FROM tenant_whatsapp_config WHERE id = 1")
            )
            .mappings()
            .one()
        )

        assert set(ENCRYPTED_COLUMNS).issubset(columns)
        assert row["api_key"] is None
        assert row["webhook_secret"] is None
        assert row["openai_api_key"] is None
        for column_name, plaintext in ENCRYPTED_COLUMNS.items():
            assert row[column_name].startswith(SECRET_PREFIX)
            assert plaintext not in row[column_name]
            assert decrypt_secret(row[column_name]) == plaintext

        _run_action(connection, migration, "downgrade")

        columns = {
            column["name"]
            for column in sa.inspect(connection).get_columns("tenant_whatsapp_config")
        }
        restored = (
            connection.execute(
                sa.text("SELECT * FROM tenant_whatsapp_config WHERE id = 1")
            )
            .mappings()
            .one()
        )

        assert not set(ENCRYPTED_COLUMNS).intersection(columns)
        assert restored["api_key"] == "dialog-secret"
        assert restored["webhook_secret"] == "webhook-secret"
        assert restored["openai_api_key"] == "openai-secret"


def test_migration_is_safe_when_whatsapp_table_does_not_exist(monkeypatch):
    monkeypatch.setenv("PAYMENT_CONFIG_ENCRYPTION_KEY", "migration-test-master-key")
    engine = sa.create_engine("sqlite://")
    migration = _load_migration()

    with engine.begin() as connection:
        _run_action(connection, migration, "upgrade")
        _run_action(connection, migration, "downgrade")

    assert sa.inspect(engine).get_table_names() == []
