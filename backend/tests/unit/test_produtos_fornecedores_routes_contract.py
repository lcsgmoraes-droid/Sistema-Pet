EXPECTED_FORNECEDORES_PATHS = {
    "/{produto_id}/fornecedores",
    "/fornecedores/{vinculo_id}",
}
EXPECTED_PRODUTOS_FORNECEDORES_PATHS = {
    f"/produtos{path}" for path in EXPECTED_FORNECEDORES_PATHS
}


def _route_paths(router):
    return {getattr(route, "path", None) for route in router.routes}


def test_produtos_fornecedores_routes_ficam_em_subrouter_dedicado():
    from app.produtos.fornecedores_routes import router

    assert EXPECTED_FORNECEDORES_PATHS.issubset(_route_paths(router))


def test_produtos_router_inclui_fornecedores_sem_mudar_paths():
    from app.produtos_routes import router

    assert EXPECTED_PRODUTOS_FORNECEDORES_PATHS.issubset(_route_paths(router))
