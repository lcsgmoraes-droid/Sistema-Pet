from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]

CLIENTES_FILES = [
    "app/clientes_routes.py",
    "app/clientes/common.py",
    "app/clientes/crud_routes.py",
    "app/clientes/racas_routes.py",
]


def _non_empty_line_count(relative_path: str) -> int:
    source = (BACKEND_ROOT / relative_path).read_text(encoding="utf-8")
    return sum(1 for line in source.splitlines() if line.strip())


def _post_or_get_route_names(router):
    return [
        route.name
        for route in router.routes
        if getattr(route, "methods", set()) & {"GET", "POST", "PUT", "DELETE"}
    ]


def test_clientes_fachada_preserva_handlers_e_helpers_extraidos():
    from app import clientes_routes
    from app.clientes import common, crud_routes, racas_routes

    assert clientes_routes.create_cliente is crud_routes.create_cliente
    assert clientes_routes.list_clientes is crud_routes.list_clientes
    assert clientes_routes.get_cliente is crud_routes.get_cliente
    assert clientes_routes.update_cliente is crud_routes.update_cliente
    assert clientes_routes.delete_cliente is crud_routes.delete_cliente
    assert clientes_routes.list_racas is racas_routes.list_racas
    assert clientes_routes.list_racas_teste is racas_routes.list_racas_teste

    assert clientes_routes.gerar_codigo_cliente is common.gerar_codigo_cliente
    assert clientes_routes._obter_cliente_ou_404 is common._obter_cliente_ou_404
    assert (
        clientes_routes._validar_telefone_cliente_obrigatorio
        is common._validar_telefone_cliente_obrigatorio
    )


def test_clientes_router_mantem_ordem_das_rotas_publicas_sensiveis():
    from app import clientes_routes

    route_names = _post_or_get_route_names(clientes_routes.router)

    assert route_names.index("list_racas") < route_names.index("get_cliente")
    assert route_names.index("list_racas_teste") < route_names.index("get_cliente")


def test_clientes_fatia_31_fica_abaixo_de_700_linhas_nao_vazias():
    oversized = {
        relative_path: _non_empty_line_count(relative_path)
        for relative_path in CLIENTES_FILES
        if _non_empty_line_count(relative_path) > 700
    }

    assert oversized == {}
