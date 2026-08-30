from __future__ import annotations

from tests.multi_tenant.rls_migration_helpers import load_migration, migration_path


MIGRATION_FILE = migration_path(
    "zyr20260829a1_bling_oauth_app_credentials_per_tenant.py"
)


def test_bling_oauth_app_credentials_migration_contract():
    migration = load_migration(MIGRATION_FILE)
    source = MIGRATION_FILE.read_text(encoding="utf-8")

    assert migration["revision"] == "zyr20260829a1"
    assert migration["down_revision"] == "zxq20260829a1"
    assert migration["CONNECTIONS"] == "bling_connections"
    assert '"oauth_client_id"' in source
    assert '"oauth_client_secret_encrypted"' in source
    assert '"access_token_encrypted"' in source
    assert "nullable=True" in source
