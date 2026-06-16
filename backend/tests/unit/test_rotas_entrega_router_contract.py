from app.api.endpoints.rotas_entrega import router


def test_rotas_entrega_router_has_single_otimizar_selecionadas_route():
    routes = [
        route
        for route in router.routes
        if getattr(route, "path", "").endswith(
            "/vendas-pendentes/otimizar-selecionadas"
        )
        and "POST" in getattr(route, "methods", set())
    ]

    assert len(routes) == 1
