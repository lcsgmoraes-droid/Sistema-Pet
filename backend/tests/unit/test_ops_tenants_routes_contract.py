from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_ops_tenants_routes_are_admin_only_and_expose_import_actions():
    source = (BACKEND_ROOT / "app/routes/ops_tenants_routes.py").read_text(encoding="utf-8")

    assert 'prefix="/admin/tenants"' in source
    assert "require_admin" in source
    assert '@router.get("")' in source
    assert '"/{tenant_id}/catalog-import/preview"' in source
    assert '"/{tenant_id}/catalog-import/apply"' in source
    assert "confirm" in source
