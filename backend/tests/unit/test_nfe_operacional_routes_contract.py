from app import nfe_routes
from app.nfe import listagem
from app.nfe import operacional_routes


EXPECTED_SUBROUTES = {
    ("/{nfe_id}/reconciliar-fluxo", "POST"),
    ("/{nfe_id}", "GET"),
    ("/{nfe_id}/xml", "GET"),
    ("/{nfe_id}/cancelar", "POST"),
    ("/{nfe_id}/carta-correcao", "POST"),
    ("/{venda_id}", "DELETE"),
    ("/webhook/bling", "POST"),
    ("/{venda_id}/sincronizar-status", "POST"),
    ("/sincronizar-todos", "POST"),
    ("/{nfe_id}/danfe", "GET"),
    ("/config/testar-conexao", "GET"),
}

EXPECTED_PUBLIC_ROUTES = {
    (f"/nfe{path}", method) for path, method in EXPECTED_SUBROUTES
}


def _route_signatures(router):
    return {
        (route.path, ",".join(sorted(route.methods)))
        for route in router.routes
        if hasattr(route, "methods")
    }


def test_rotas_operacionais_ficam_em_router_dedicado():
    assert EXPECTED_SUBROUTES <= _route_signatures(operacional_routes.router)


def test_nfe_routes_preserva_caminhos_publicos_operacionais():
    assert EXPECTED_PUBLIC_ROUTES <= _route_signatures(nfe_routes.router)


def test_nfe_routes_mantem_aliases_de_compatibilidade():
    assert nfe_routes.consultar_nfe is operacional_routes.consultar_nfe
    assert nfe_routes.cancelar_nfe is operacional_routes.cancelar_nfe
    assert nfe_routes.webhook_bling is operacional_routes.webhook_bling
    assert nfe_routes.baixar_danfe is operacional_routes.baixar_danfe


def test_nfe_routes_mantem_aliases_de_listagem_para_imports_legados():
    assert nfe_routes._normalizar_nota_bling is listagem._normalizar_nota_bling
    assert nfe_routes._status_nota_bling is listagem._status_nota_bling
    assert nfe_routes._obter_detalhe_nfe_cache is listagem._obter_detalhe_nfe_cache
    assert (
        nfe_routes._sincronizar_cache_nfes_com_bling
        is listagem._sincronizar_cache_nfes_com_bling
    )
