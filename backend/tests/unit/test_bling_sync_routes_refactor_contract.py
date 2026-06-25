from pathlib import Path

from app import bling_sync_routes
from app.bling_sync import config_routes, dashboard_routes, operational_routes
from app.bling_sync import routes_common, webhook_routes


ROOT = Path(__file__).resolve().parents[2]

EXPECTED_PUBLIC_ROUTES = {
    ("/estoque/sync/produtos-bling", "GET"),
    ("/estoque/sync/importar-imagens", "POST"),
    ("/estoque/sync/config", "POST"),
    ("/estoque/sync/vincular", "POST"),
    ("/estoque/sync/vincular-automatico/{produto_id}", "POST"),
    ("/estoque/sync/health", "GET"),
    ("/estoque/sync/produtos-sem-vinculo", "GET"),
    ("/estoque/sync/resumo-cobertura", "GET"),
    ("/estoque/sync/faltantes-bling", "GET"),
    ("/estoque/sync/dashboard", "GET"),
    ("/estoque/sync/faltantes-bling/criar", "POST"),
    ("/estoque/sync/enviar/{produto_id}", "POST"),
    ("/estoque/sync/forcar/{produto_id}", "POST"),
    ("/estoque/sync/status", "GET"),
    ("/estoque/sync/status-problemas", "GET"),
    ("/estoque/sync/reprocessar-falhas", "POST"),
    ("/estoque/sync/reconciliar-recentes", "POST"),
    ("/estoque/sync/reconciliar-geral", "POST"),
    ("/estoque/sync/reconciliar-geral/status", "GET"),
    ("/estoque/sync/reconciliar/{produto_id}", "POST"),
    ("/estoque/sync/webhook/bling", "POST"),
    ("/estoque/sync/vincular-todos", "POST"),
}


def _route_signatures(router):
    return {
        (route.path, ",".join(sorted(route.methods)))
        for route in router.routes
        if hasattr(route, "methods")
    }


def test_bling_sync_routes_publicas_preservadas():
    assert EXPECTED_PUBLIC_ROUTES <= _route_signatures(bling_sync_routes.router)


def test_bling_sync_routes_mantem_aliases_de_compatibilidade():
    assert (
        bling_sync_routes._buscar_item_bling_para_vinculo
        is routes_common._buscar_item_bling_para_vinculo
    )
    assert bling_sync_routes._upsert_sync_vinculo is routes_common._upsert_sync_vinculo
    assert (
        bling_sync_routes.configurar_sincronizacao
        is config_routes.configurar_sincronizacao
    )
    assert (
        bling_sync_routes.dashboard_pendencias_bling
        is dashboard_routes.dashboard_pendencias_bling
    )
    assert bling_sync_routes.reconciliar_geral is operational_routes.reconciliar_geral
    assert bling_sync_routes.webhook_bling is webhook_routes.webhook_bling


def test_bling_sync_routes_refactor_mantem_arquivos_focados():
    limits = {
        "app/bling_sync_routes.py": 180,
        "app/bling_sync/routes_common.py": 230,
        "app/bling_sync/config_routes.py": 240,
        "app/bling_sync/dashboard_routes.py": 430,
        "app/bling_sync/operational_routes.py": 520,
        "app/bling_sync/webhook_routes.py": 320,
    }

    for relative_path, max_lines in limits.items():
        path = ROOT / relative_path
        assert sum(1 for _ in path.open(encoding="utf-8")) <= max_lines
