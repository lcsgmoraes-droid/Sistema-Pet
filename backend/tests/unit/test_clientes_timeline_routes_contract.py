EXPECTED_TIMELINE_PATHS = {
    "/{cliente_id}/timeline",
    "/fornecedor/{fornecedor_id}/timeline",
}
EXPECTED_CLIENTES_TIMELINE_PATHS = {
    f"/clientes{path}" for path in EXPECTED_TIMELINE_PATHS
}


def _route_paths(router):
    return {getattr(route, "path", None) for route in router.routes}


def test_clientes_timeline_routes_ficam_em_subrouter_dedicado():
    from app.clientes.timeline_routes import router

    assert EXPECTED_TIMELINE_PATHS.issubset(_route_paths(router))


def test_clientes_router_inclui_timeline_sem_mudar_paths():
    from app.clientes_routes import router

    assert EXPECTED_CLIENTES_TIMELINE_PATHS.issubset(_route_paths(router))
