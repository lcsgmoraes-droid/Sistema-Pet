from pathlib import Path

from app import comissoes_avancadas_routes as facade
from app.comissoes_avancadas import conferencia_routes, pagamento_routes


def _route_pairs(router):
    return {
        (method, route.path)
        for route in router.routes
        for method in getattr(route, "methods", set())
    }


def test_comissoes_avancadas_routes_preserva_endpoints_publicos():
    paths = _route_pairs(facade.router)

    assert ("GET", "/comissoes/conferencia-avancada/{funcionario_id}") in paths
    assert ("GET", "/comissoes/formas-pagamento") in paths
    assert ("POST", "/comissoes/fechar-com-pagamento") in paths


def test_comissoes_avancadas_routes_preserva_reexports_legados():
    assert (
        facade.conferencia_com_filtros_avancados
        is conferencia_routes.conferencia_com_filtros_avancados
    )
    assert facade.listar_formas_pagamento is pagamento_routes.listar_formas_pagamento
    assert (
        facade.fechar_com_pagamento_parcial
        is pagamento_routes.fechar_com_pagamento_parcial
    )


def test_comissoes_avancadas_routes_fachada_e_modulos_abaixo_700():
    files = [
        Path(facade.__file__),
        Path(conferencia_routes.__file__),
        Path(pagamento_routes.__file__),
    ]

    for path in files:
        source = path.read_text(encoding="utf-8")
        assert len(source.splitlines()) < 700

    facade_source = Path(facade.__file__).read_text(encoding="utf-8")
    assert "@router.get" not in facade_source
    assert "@router.post" not in facade_source
