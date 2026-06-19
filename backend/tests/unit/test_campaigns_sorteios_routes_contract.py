EXPECTED_SORTEIOS_PATHS = {
    "/sorteios",
    "/sorteios/{drawing_id}",
    "/sorteios/{drawing_id}/inscrever",
    "/sorteios/{drawing_id}/executar",
    "/sorteios/{drawing_id}/resultado",
    "/sorteios/{drawing_id}/codigos-offline",
}
EXPECTED_CAMPANHAS_SORTEIOS_PATHS = {
    f"/campanhas{path}" for path in EXPECTED_SORTEIOS_PATHS
}


def _route_paths(router):
    return {getattr(route, "path", None) for route in router.routes}


def test_campaigns_sorteios_routes_ficam_em_subrouter_dedicado():
    from app.campaigns.sorteios_routes import router

    assert EXPECTED_SORTEIOS_PATHS.issubset(_route_paths(router))


def test_campaigns_router_inclui_sorteios_sem_mudar_paths():
    from app.campaigns.routes import router

    assert EXPECTED_CAMPANHAS_SORTEIOS_PATHS.issubset(_route_paths(router))
