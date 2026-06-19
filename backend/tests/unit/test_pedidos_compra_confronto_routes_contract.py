EXPECTED_CONFRONTO_PATHS = {
    "/{pedido_id}/notas-candidatas",
    "/{pedido_id}/vincular-nota/{nota_id}",
    "/{pedido_id}/confronto",
    "/{pedido_id}/confronto/csv",
    "/{pedido_id}/confronto/pdf",
    "/{pedido_id}/confronto/email-texto",
    "/{pedido_id}/finalizar-confronto",
    "/{pedido_id}/sugerir-pedido-complementar",
}
EXPECTED_PEDIDOS_COMPRA_CONFRONTO_PATHS = {
    f"/pedidos-compra{path}" for path in EXPECTED_CONFRONTO_PATHS
}


def _route_paths(router):
    return {getattr(route, "path", None) for route in router.routes}


def test_pedidos_compra_confronto_routes_ficam_em_subrouter_dedicado():
    from app.pedidos_compra.confronto_routes import router

    assert EXPECTED_CONFRONTO_PATHS.issubset(_route_paths(router))


def test_pedidos_compra_router_inclui_confronto_sem_mudar_paths():
    from app.pedidos_compra_routes import router

    assert EXPECTED_PEDIDOS_COMPRA_CONFRONTO_PATHS.issubset(_route_paths(router))
