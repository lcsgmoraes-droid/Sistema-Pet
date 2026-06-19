EXPECTED_CATALOGOS_PATHS = {
    "/categorias",
    "/categorias/hierarquia",
    "/categorias/{categoria_id}",
    "/marcas",
    "/marcas/{marca_id}",
    "/departamentos",
    "/departamentos/{departamento_id}",
}
EXPECTED_PRODUTOS_CATALOGOS_PATHS = {
    f"/produtos{path}" for path in EXPECTED_CATALOGOS_PATHS
}


def _route_paths(router):
    return {getattr(route, "path", None) for route in router.routes}


def test_produtos_catalogos_routes_ficam_em_subrouter_dedicado():
    from app.produtos.catalogos_routes import router

    assert EXPECTED_CATALOGOS_PATHS.issubset(_route_paths(router))


def test_produtos_router_inclui_catalogos_sem_mudar_paths():
    from app.produtos_routes import router

    assert EXPECTED_PRODUTOS_CATALOGOS_PATHS.issubset(_route_paths(router))
