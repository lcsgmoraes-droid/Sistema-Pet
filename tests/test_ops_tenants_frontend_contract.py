from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_ops_tenants_frontend_route_nav_and_api_contract():
    app_source = (ROOT / "frontend/src/App.jsx").read_text(encoding="utf-8")
    layout_source = (ROOT / "frontend/src/components/OpsLayout.jsx").read_text(
        encoding="utf-8"
    )
    page_source = (ROOT / "frontend/src/pages/OpsTenants.jsx").read_text(
        encoding="utf-8"
    )

    assert "OpsTenants" in app_source
    assert 'path="tenants"' in app_source
    assert 'to: "/ops/tenants"' in layout_source
    assert 'api.get("/admin/tenants"' in page_source
    assert "catalog-import/preview" in page_source
    assert "catalog-import/apply" in page_source
    assert "Importar catalogo base" in page_source
