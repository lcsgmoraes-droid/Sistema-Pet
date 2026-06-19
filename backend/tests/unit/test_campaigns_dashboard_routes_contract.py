from app.campaigns import dashboard_routes, routes


def _route_signatures(router):
    return {
        (route.path, ",".join(sorted(route.methods)))
        for route in router.routes
        if hasattr(route, "methods")
    }


def test_dashboard_fica_em_router_dedicado():
    assert ("/dashboard", "GET") in _route_signatures(dashboard_routes.router)


def test_campaigns_routes_preserva_dashboard_publico():
    assert ("/campanhas/dashboard", "GET") in _route_signatures(routes.router)


def test_campaigns_routes_mantem_alias_de_dashboard():
    assert routes.dashboard_campanhas is dashboard_routes.dashboard_campanhas
