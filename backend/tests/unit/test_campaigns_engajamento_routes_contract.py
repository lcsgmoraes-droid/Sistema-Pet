from app.campaigns import routes
from app.campaigns import engajamento_routes


EXPECTED_SUBROUTES = {
    ("/retencao", "GET"),
    ("/retencao", "POST"),
    ("/retencao/{campaign_id}", "PUT"),
    ("/retencao/{campaign_id}", "DELETE"),
    ("/destaque-mensal", "GET"),
    ("/destaque-mensal/enviar", "POST"),
    ("/seed", "POST"),
    ("/ranking/envio-em-lote", "POST"),
    ("/notificacoes/inativos", "POST"),
}

EXPECTED_PUBLIC_ROUTES = {
    (f"/campanhas{path}", method) for path, method in EXPECTED_SUBROUTES
}


def _route_signatures(router):
    return {
        (route.path, ",".join(sorted(route.methods)))
        for route in router.routes
        if hasattr(route, "methods")
    }


def test_rotas_de_engajamento_ficam_em_router_dedicado():
    assert EXPECTED_SUBROUTES <= _route_signatures(engajamento_routes.router)


def test_campaigns_routes_preserva_caminhos_publicos_de_engajamento():
    assert EXPECTED_PUBLIC_ROUTES <= _route_signatures(routes.router)


def test_campaigns_routes_mantem_aliases_de_compatibilidade():
    assert routes.listar_retencao is engajamento_routes.listar_retencao
    assert (
        routes.calcular_destaque_mensal is engajamento_routes.calcular_destaque_mensal
    )
    assert routes.envio_em_lote is engajamento_routes.envio_em_lote
    assert (
        routes.envio_escalonado_inativos is engajamento_routes.envio_escalonado_inativos
    )
