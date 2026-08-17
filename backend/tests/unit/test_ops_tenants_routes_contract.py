from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_ops_tenants_routes_are_platform_admin_only_and_expose_import_actions():
    source = (BACKEND_ROOT / "app/routes/ops_tenants_routes.py").read_text(
        encoding="utf-8"
    )

    assert 'prefix="/admin/tenants"' in source
    assert "require_platform_admin" in source
    assert "require_admin" not in source
    assert '@router.get("")' in source
    assert '@router.patch("/{tenant_id}/commercial")' in source
    assert '"/{tenant_id}/catalog-import/preview"' in source
    assert '"/{tenant_id}/catalog-import/apply"' in source
    assert "CommercialStateRequest" in source
    assert "confirm" in source


def test_observability_routes_are_platform_admin_only():
    source = (BACKEND_ROOT / "app/routes/error_events_routes.py").read_text(
        encoding="utf-8"
    )

    assert "Depends(require_platform_admin)" in source
    assert "Depends(require_admin)" not in source


def test_platform_admin_migration_copies_legacy_owner_without_tenant():
    source = (
        BACKEND_ROOT / "alembic/versions/zwq20260816a1_platform_admin_identity.py"
    ).read_text(encoding="utf-8")

    assert '"platform_admins"' in source
    assert '"platform_admin_sessions"' in source
    assert "WHERE is_admin = true" in source
    assert "tenant_id" not in source
