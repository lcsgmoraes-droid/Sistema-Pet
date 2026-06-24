from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_stone_online_router_is_not_registered_in_app_main():
    app_bootstrap_source = (
        (BACKEND_ROOT / "app" / "main.py").read_text(encoding="utf-8")
        + (BACKEND_ROOT / "app" / "main_routers.py").read_text(encoding="utf-8")
    )

    assert "app.stone_routes" not in app_bootstrap_source
    assert "stone_router" not in app_bootstrap_source
    assert "/stone" not in app_bootstrap_source


def test_stone_online_source_files_were_removed():
    removed_files = [
        BACKEND_ROOT / "app" / "stone_routes.py",
        BACKEND_ROOT / "app" / "stone_api_client.py",
        BACKEND_ROOT / "app" / "stone_conciliation_client.py",
    ]

    for removed_file in removed_files:
        assert not removed_file.exists(), (
            f"{removed_file.name} deve permanecer removido"
        )


def test_stone_retirement_migration_scrubs_plaintext_secrets():
    migration = (
        BACKEND_ROOT
        / "alembic"
        / "versions"
        / "pq20260611a1_retire_stone_integration.py"
    )
    migration_source = migration.read_text(encoding="utf-8")

    assert 'down_revision = "pp20260611a1"' in migration_source
    assert "UPDATE stone_configs" in migration_source
    assert "client_id = ''" in migration_source
    assert "client_secret = ''" in migration_source
    assert "webhook_secret = NULL" in migration_source
    assert "conciliacao_client_id = NULL" in migration_source
    assert "conciliacao_client_secret = NULL" in migration_source
    assert "conciliacao_username = NULL" in migration_source
    assert "conciliacao_password_enc = NULL" in migration_source
    assert "pos_serial_number = NULL" in migration_source
    assert "active = FALSE" in migration_source
    assert "ALTER COLUMN client_id DROP NOT NULL" in migration_source
    assert "ALTER COLUMN client_secret DROP NOT NULL" in migration_source


def test_stone_config_model_keeps_retired_secret_fields_nullable():
    model_source = (BACKEND_ROOT / "app" / "stone_models.py").read_text(
        encoding="utf-8"
    )

    assert "client_id = Column(String(200), nullable=True)" in model_source
    assert "client_secret = Column(String(200), nullable=True)" in model_source
    assert "active = Column(Boolean, default=False)" in model_source
