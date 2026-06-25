from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_ops_tenants_frontend_route_nav_and_api_contract():
    app_source = (ROOT / "frontend/src/App.jsx").read_text(encoding="utf-8")
    app_routes_source = (ROOT / "frontend/src/app/AppRoutes.jsx").read_text(
        encoding="utf-8"
    )
    ops_routes_source = (ROOT / "frontend/src/app/routes/OpsRoutes.jsx").read_text(
        encoding="utf-8"
    )
    lazy_pages_source = (ROOT / "frontend/src/app/lazyPages.jsx").read_text(
        encoding="utf-8"
    )
    layout_source = (ROOT / "frontend/src/components/OpsLayout.jsx").read_text(
        encoding="utf-8"
    )
    page_source = (ROOT / "frontend/src/pages/OpsTenants.jsx").read_text(
        encoding="utf-8"
    )

    assert "<AppRoutes />" in app_source
    assert "OpsLayout" in app_routes_source
    assert 'path="/ops"' in app_routes_source
    assert "OpsTenants" in lazy_pages_source
    assert 'path="tenants"' in ops_routes_source
    assert 'to: "/ops/tenants"' in layout_source
    assert 'api.get("/admin/tenants"' in page_source
    assert "catalog-import/preview" in page_source
    assert "catalog-import/apply" in page_source
    assert "Importar catalogo base" in page_source
