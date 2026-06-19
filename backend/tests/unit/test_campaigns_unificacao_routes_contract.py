EXPECTED_UNIFICACAO_PATHS = {
    "/unificacao/sugestoes",
    "/unificacao/confirmar",
    "/unificacao/{merge_id}",
}
EXPECTED_CAMPANHAS_UNIFICACAO_PATHS = {
    f"/campanhas{path}" for path in EXPECTED_UNIFICACAO_PATHS
}


def _route_paths(router):
    return {getattr(route, "path", None) for route in router.routes}


def test_campaigns_unificacao_routes_ficam_em_subrouter_dedicado():
    from app.campaigns.unificacao_routes import router

    assert EXPECTED_UNIFICACAO_PATHS.issubset(_route_paths(router))


def test_campaigns_router_inclui_unificacao_sem_mudar_paths():
    from app.campaigns.routes import router

    assert EXPECTED_CAMPANHAS_UNIFICACAO_PATHS.issubset(_route_paths(router))
