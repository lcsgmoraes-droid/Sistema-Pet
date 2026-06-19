EXPECTED_RELATORIO_PATHS = {
    "/relatorio/movimentacoes",
    "/relatorio/produto-vendas",
    "/relatorio/validade-proxima",
    "/relatorio/valorizacao-estoque",
}
EXPECTED_PRODUTOS_RELATORIO_PATHS = {
    f"/produtos{path}" for path in EXPECTED_RELATORIO_PATHS
}


def _route_paths(router):
    return {getattr(route, "path", None) for route in router.routes}


def test_produtos_relatorios_routes_ficam_em_subrouter_dedicado():
    from app.produtos.relatorios_routes import router

    assert EXPECTED_RELATORIO_PATHS.issubset(_route_paths(router))


def test_produtos_router_inclui_relatorios_sem_mudar_paths():
    from app.produtos_routes import router

    assert EXPECTED_PRODUTOS_RELATORIO_PATHS.issubset(_route_paths(router))
