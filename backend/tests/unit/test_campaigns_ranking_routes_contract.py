from app.campaigns import ranking_routes, routes


EXPECTED_SUBROUTES = {
    ("/ranking", "GET"),
    ("/ranking/config", "GET"),
    ("/ranking/config", "PUT"),
    ("/ranking/recalcular", "POST"),
    ("/config/horarios", "GET"),
    ("/config/horarios", "PUT"),
    ("/campanhas", "POST"),
    ("/campanhas/{campaign_id}", "DELETE"),
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


def test_rotas_de_ranking_ficam_em_router_dedicado():
    assert EXPECTED_SUBROUTES <= _route_signatures(ranking_routes.router)


def test_campaigns_routes_preserva_caminhos_publicos_de_ranking():
    assert EXPECTED_PUBLIC_ROUTES <= _route_signatures(routes.router)


def test_campaigns_routes_mantem_aliases_de_ranking():
    assert routes.listar_ranking is ranking_routes.listar_ranking
    assert routes.get_ranking_config is ranking_routes.get_ranking_config
    assert routes.salvar_ranking_config is ranking_routes.salvar_ranking_config
    assert routes.get_scheduler_config is ranking_routes.get_scheduler_config
    assert routes.salvar_scheduler_config is ranking_routes.salvar_scheduler_config
    assert routes.recalcular_ranking is ranking_routes.recalcular_ranking
    assert routes.criar_campanha is ranking_routes.criar_campanha
    assert routes.deletar_campanha is ranking_routes.deletar_campanha
