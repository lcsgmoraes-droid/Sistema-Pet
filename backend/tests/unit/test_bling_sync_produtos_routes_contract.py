from app import bling_sync_routes
from app.bling_sync import produtos_routes


EXPECTED_SUBROUTES = {
    ("/produtos-bling", "GET"),
    ("/importar-imagens", "POST"),
}

EXPECTED_PUBLIC_ROUTES = {
    ("/estoque/sync/produtos-bling", "GET"),
    ("/estoque/sync/importar-imagens", "POST"),
}


def _route_signatures(router):
    return {
        (route.path, ",".join(sorted(route.methods)))
        for route in router.routes
        if hasattr(route, "methods")
    }


def test_produtos_bling_ficam_em_router_dedicado():
    assert EXPECTED_SUBROUTES <= _route_signatures(produtos_routes.router)


def test_bling_sync_preserva_rotas_publicas_de_produtos_bling():
    assert EXPECTED_PUBLIC_ROUTES <= _route_signatures(bling_sync_routes.router)


def test_bling_sync_mantem_aliases_de_compatibilidade():
    assert (
        bling_sync_routes.listar_produtos_bling is produtos_routes.listar_produtos_bling
    )
    assert (
        bling_sync_routes.importar_imagens_dos_produtos_bling
        is produtos_routes.importar_imagens_dos_produtos_bling
    )
