EXPECTED_RACAO_PATHS = {
    "/{produto_id}/classificar-ia",
    "/classificar-lote",
    "/racao/alertas",
}
EXPECTED_PRODUTOS_RACAO_PATHS = {f"/produtos{path}" for path in EXPECTED_RACAO_PATHS}


def _route_paths(router):
    return {getattr(route, "path", None) for route in router.routes}


def test_produtos_racao_routes_ficam_em_subrouter_dedicado():
    from app.produtos.racao_routes import router

    assert EXPECTED_RACAO_PATHS.issubset(_route_paths(router))


def test_produtos_router_inclui_racao_sem_mudar_paths():
    from app.produtos_routes import router

    assert EXPECTED_PRODUTOS_RACAO_PATHS.issubset(_route_paths(router))
