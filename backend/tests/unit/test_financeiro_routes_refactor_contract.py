from pathlib import Path

from app import financeiro_routes
from app.financeiro import cliente_routes, config_routes, fluxo_caixa_routes
from app.financeiro.fluxo_caixa_periodos import _agrupar_por_periodo


ROOT = Path(__file__).resolve().parents[2]


def _method_paths(router):
    paths = set()
    for route in router.routes:
        for method in getattr(route, "methods", set()):
            paths.add((method, getattr(route, "path", None)))
    return paths


def test_financeiro_routes_preserva_paths_publicos_extraidos():
    paths = _method_paths(financeiro_routes.router)

    assert ("GET", "/financeiro/categorias") in paths
    assert ("POST", "/financeiro/categorias") in paths
    assert ("PUT", "/financeiro/categorias/{categoria_id}") in paths
    assert ("DELETE", "/financeiro/categorias/{categoria_id}") in paths
    assert ("GET", "/financeiro/formas-pagamento") in paths
    assert ("POST", "/financeiro/formas-pagamento") in paths
    assert ("PUT", "/financeiro/formas-pagamento/{forma_id}") in paths
    assert ("DELETE", "/financeiro/formas-pagamento/{forma_id}") in paths
    assert ("GET", "/financeiro/fluxo-caixa") in paths
    assert ("GET", "/financeiro/cliente/{cliente_id}") in paths
    assert ("GET", "/financeiro/cliente/{cliente_id}/resumo") in paths


def test_financeiro_routes_reexporta_handlers_extraidos():
    assert financeiro_routes.listar_categorias is config_routes.listar_categorias
    assert financeiro_routes.criar_categoria is config_routes.criar_categoria
    assert financeiro_routes.listar_formas_pagamento is (
        config_routes.listar_formas_pagamento
    )
    assert financeiro_routes.criar_forma_pagamento is (
        config_routes.criar_forma_pagamento
    )
    assert financeiro_routes.get_fluxo_caixa is fluxo_caixa_routes.get_fluxo_caixa
    assert financeiro_routes._agrupar_por_periodo is _agrupar_por_periodo
    assert financeiro_routes.get_historico_financeiro_cliente is (
        cliente_routes.get_historico_financeiro_cliente
    )
    assert financeiro_routes.get_resumo_financeiro_cliente is (
        cliente_routes.get_resumo_financeiro_cliente
    )


def test_financeiro_routes_stays_below_large_file_threshold_after_extraction():
    sources = [
        ROOT / "app" / "financeiro_routes.py",
        ROOT / "app" / "financeiro" / "config_routes.py",
        ROOT / "app" / "financeiro" / "fluxo_caixa_schemas.py",
        ROOT / "app" / "financeiro" / "fluxo_caixa_periodos.py",
        ROOT / "app" / "financeiro" / "fluxo_caixa_routes.py",
        ROOT / "app" / "financeiro" / "cliente_routes.py",
    ]

    assert len(sources[0].read_text(encoding="utf-8").splitlines()) < 120
    for source in sources[1:]:
        assert len(source.read_text(encoding="utf-8").splitlines()) < 700
