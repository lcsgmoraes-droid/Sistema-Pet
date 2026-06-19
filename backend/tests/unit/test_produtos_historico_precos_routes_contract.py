EXPECTED_HISTORICO_PRECOS_PATHS = {
    "/{produto_id}/historico-precos",
}
EXPECTED_PRODUTOS_HISTORICO_PRECOS_PATHS = {
    f"/produtos{path}" for path in EXPECTED_HISTORICO_PRECOS_PATHS
}


def _route_paths(router):
    return {getattr(route, "path", None) for route in router.routes}


def test_produtos_historico_precos_routes_ficam_em_subrouter_dedicado():
    from app.produtos.historico_precos_routes import router

    assert EXPECTED_HISTORICO_PRECOS_PATHS.issubset(_route_paths(router))


def test_produtos_router_inclui_historico_precos_sem_mudar_paths():
    from app.produtos_routes import router

    assert EXPECTED_PRODUTOS_HISTORICO_PRECOS_PATHS.issubset(_route_paths(router))
