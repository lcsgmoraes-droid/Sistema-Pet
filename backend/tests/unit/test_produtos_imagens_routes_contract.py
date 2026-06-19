EXPECTED_IMAGENS_PATHS = {
    "/{produto_id}/imagens",
    "/imagens/{imagem_id}",
}
EXPECTED_PRODUTOS_IMAGENS_PATHS = {
    f"/produtos{path}" for path in EXPECTED_IMAGENS_PATHS
}


def _route_paths(router):
    return {getattr(route, "path", None) for route in router.routes}


def test_produtos_imagens_routes_ficam_em_subrouter_dedicado():
    from app.produtos.imagens_routes import router

    assert EXPECTED_IMAGENS_PATHS.issubset(_route_paths(router))


def test_produtos_router_inclui_imagens_sem_mudar_paths():
    from app.produtos_routes import router

    assert EXPECTED_PRODUTOS_IMAGENS_PATHS.issubset(_route_paths(router))
