from pathlib import Path

from app.campaigns import (
    beneficios_manuais_routes,
    campaign_management_routes,
    clientes_routes,
    coupons_routes,
    routes,
    routes_common,
    validade_routes,
)


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _route_signatures(router):
    return {
        (route.path, ",".join(sorted(route.methods)))
        for route in router.routes
        if hasattr(route, "methods")
    }


def test_campaigns_routes_preserva_paths_publicos_extraidos():
    paths = _route_signatures(routes.router)

    assert ("/campanhas", "GET") in paths
    assert ("/campanhas/validade/config", "GET") in paths
    assert ("/campanhas/cupons", "GET") in paths
    assert ("/campanhas/cupons/{code}", "DELETE") in paths
    assert ("/campanhas/clientes/{customer_id}/saldo", "GET") in paths
    assert ("/campanhas/cashback/manual", "POST") in paths
    assert ("/campanhas/carimbos/manual", "POST") in paths


def test_campaigns_routes_reexporta_handlers_extraidos():
    assert routes.get_db is routes_common.get_db
    assert routes.listar_campanhas is campaign_management_routes.listar_campanhas
    assert routes.salvar_config_campanha_validade is (
        validade_routes.salvar_config_campanha_validade
    )
    assert routes._build_manual_coupon_meta is coupons_routes._build_manual_coupon_meta
    assert routes.saldo_cliente is clientes_routes.saldo_cliente
    assert routes.cashback_manual is beneficios_manuais_routes.cashback_manual


def test_campaigns_routes_stays_below_large_file_threshold_after_extraction():
    campaigns_dir = BACKEND_ROOT / "app" / "campaigns"
    extracted_files = [
        campaigns_dir / "routes.py",
        campaigns_dir / "routes_common.py",
        campaigns_dir / "validade_routes.py",
        campaigns_dir / "campaign_management_routes.py",
        campaigns_dir / "coupons_routes.py",
        campaigns_dir / "clientes_routes.py",
        campaigns_dir / "beneficios_manuais_routes.py",
    ]

    assert (
        len((campaigns_dir / "routes.py").read_text(encoding="utf-8").splitlines())
        < 200
    )
    for source in extracted_files[1:]:
        assert len(source.read_text(encoding="utf-8").splitlines()) < 1000
