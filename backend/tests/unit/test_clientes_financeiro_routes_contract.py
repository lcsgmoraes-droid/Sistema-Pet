import importlib.util


EXPECTED_FINANCEIRO_PATHS = {
    "/{cliente_id}/credito/extrato",
    "/{cliente_id}/historico-compras",
    "/{cliente_id}/vendas-em-aberto",
    "/{cliente_id}/baixar-vendas-lote",
    "/{cliente_id}/historico",
}
EXPECTED_CLIENTES_FINANCEIRO_PATHS = {
    f"/clientes{path}" for path in EXPECTED_FINANCEIRO_PATHS
}
EXPECTED_PETS_PATHS = {
    "/{cliente_id}/pets",
    "/pets/todos",
    "/pets/{pet_id}",
}
EXPECTED_CREDITO_PATHS = {
    "/{cliente_id}/remover-campo",
    "/{cliente_id}/credito/adicionar",
    "/{cliente_id}/credito/remover",
}
EXPECTED_PARCEIROS_PATHS = {
    "/{cliente_id}/parceiro",
    "/{cliente_id}/controla-dre",
    "/entregadores/{entregador_id}/custo-operacional",
}
EXPECTED_DUPLICIDADES_PATHS = {
    "/verificar-duplicata/campo",
    "/fusao/preview",
    "/fusao/executar",
    "/duplicidades/sugestoes",
    "/duplicidades/fundir-automaticas",
}


def _route_paths(router):
    return {getattr(route, "path", None) for route in router.routes}


def test_clientes_financeiro_routes_ficam_em_subrouter_dedicado():
    assert importlib.util.find_spec("app.clientes.financeiro_routes") is not None

    from app.clientes.financeiro_routes import router

    assert EXPECTED_FINANCEIRO_PATHS.issubset(_route_paths(router))


def test_clientes_router_inclui_financeiro_sem_mudar_paths():
    from app import clientes_routes
    from app.clientes import financeiro_routes

    assert EXPECTED_CLIENTES_FINANCEIRO_PATHS.issubset(
        _route_paths(clientes_routes.router)
    )
    assert clientes_routes.get_extrato_credito is financeiro_routes.get_extrato_credito
    assert (
        clientes_routes.get_historico_compras
        is financeiro_routes.get_historico_compras
    )
    assert (
        clientes_routes.get_vendas_em_aberto
        is financeiro_routes.get_vendas_em_aberto
    )
    assert clientes_routes.baixar_vendas_lote is financeiro_routes.baixar_vendas_lote
    assert (
        clientes_routes.get_cliente_historico
        is financeiro_routes.get_cliente_historico
    )


def test_clientes_outros_subrouters_ficam_dedicados_e_reexportados():
    for module_name in (
        "app.clientes.pets_routes",
        "app.clientes.credito_routes",
        "app.clientes.parceiros_routes",
        "app.clientes.duplicidades_routes",
    ):
        assert importlib.util.find_spec(module_name) is not None

    from app import clientes_routes
    from app.clientes import credito_routes, duplicidades_routes, parceiros_routes
    from app.clientes import pets_routes

    assert EXPECTED_PETS_PATHS.issubset(_route_paths(pets_routes.router))
    assert EXPECTED_CREDITO_PATHS.issubset(_route_paths(credito_routes.router))
    assert EXPECTED_PARCEIROS_PATHS.issubset(_route_paths(parceiros_routes.router))
    assert EXPECTED_DUPLICIDADES_PATHS.issubset(
        _route_paths(duplicidades_routes.router)
    )

    clientes_paths = _route_paths(clientes_routes.router)
    for path in (
        EXPECTED_PETS_PATHS
        | EXPECTED_CREDITO_PATHS
        | EXPECTED_PARCEIROS_PATHS
        | EXPECTED_DUPLICIDADES_PATHS
    ):
        assert f"/clientes{path}" in clientes_paths

    assert clientes_routes.create_pet is pets_routes.create_pet
    assert clientes_routes.update_pet is pets_routes.update_pet
    assert clientes_routes.adicionar_credito is credito_routes.adicionar_credito
    assert clientes_routes.remover_credito is credito_routes.remover_credito
    assert clientes_routes.toggle_parceiro is parceiros_routes.toggle_parceiro
    assert (
        clientes_routes.obter_custo_operacional_entregador
        is parceiros_routes.obter_custo_operacional_entregador
    )
    assert (
        clientes_routes.verificar_duplicata
        is duplicidades_routes.verificar_duplicata
    )
