from app import bling_sync_routes
from app.bling_sync import catalog_snapshots, product_matching, produtos_routes
from app.bling_sync import status_queries


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


def test_bling_sync_matching_helpers_ficam_em_modulo_dedicado():
    assert bling_sync_routes._sku_bling is product_matching._sku_bling
    assert bling_sync_routes._barcode_bling is product_matching._barcode_bling
    assert (
        bling_sync_routes._produto_sincroniza_estoque
        is product_matching._produto_sincroniza_estoque
    )


def test_bling_sync_snapshot_helpers_ficam_em_modulo_dedicado():
    assert (
        bling_sync_routes._get_resumo_cobertura_bling
        is catalog_snapshots._get_resumo_cobertura_bling
    )
    assert (
        bling_sync_routes._get_snapshot_faltantes_bling
        is catalog_snapshots._get_snapshot_faltantes_bling
    )
    assert (
        bling_sync_routes._get_snapshot_sem_vinculo_com_match_bling
        is catalog_snapshots._get_snapshot_sem_vinculo_com_match_bling
    )
    assert (
        bling_sync_routes._invalidate_bling_snapshots
        is catalog_snapshots._invalidate_bling_snapshots
    )


def test_bling_sync_status_query_fica_em_modulo_dedicado():
    assert (
        bling_sync_routes._build_sync_problem_query
        is status_queries._build_sync_problem_query
    )
