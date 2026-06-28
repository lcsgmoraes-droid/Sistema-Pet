from pathlib import Path

from app import veterinario_internacao_routes as facade
from app.veterinario_internacao_routes_parts import (
    agenda_routes,
    historico_routes,
    listagem_config_routes,
    mutacao_routes,
)


def _route_pairs(router):
    return {
        (method, route.path)
        for route in router.routes
        for method in getattr(route, "methods", set())
    }


def test_veterinario_internacao_routes_preserva_endpoints_publicos():
    paths = _route_pairs(facade.router)

    assert ("GET", "/internacoes") in paths
    assert ("POST", "/internacoes") in paths
    assert ("GET", "/internacoes/config") in paths
    assert ("PUT", "/internacoes/config") in paths
    assert ("GET", "/internacoes/procedimentos-agenda") in paths
    assert ("POST", "/internacoes/{internacao_id}/procedimentos-agenda") in paths
    assert ("PATCH", "/internacoes/procedimentos-agenda/{agenda_id}/concluir") in paths
    assert ("DELETE", "/internacoes/procedimentos-agenda/{agenda_id}") in paths
    assert ("GET", "/internacoes/{internacao_id}") in paths
    assert ("POST", "/internacoes/{internacao_id}/evolucao") in paths
    assert ("POST", "/internacoes/{internacao_id}/procedimento") in paths
    assert ("PATCH", "/internacoes/{internacao_id}/alta") in paths
    assert ("GET", "/pets/{pet_id}/internacoes-historico") in paths


def test_veterinario_internacao_routes_mantem_rotas_estaticas_antes_da_dinamica():
    paths = [route.path for route in facade.router.routes if hasattr(route, "path")]

    assert paths.index("/internacoes/config") < paths.index(
        "/internacoes/{internacao_id}"
    )
    assert paths.index("/internacoes/procedimentos-agenda") < paths.index(
        "/internacoes/{internacao_id}"
    )


def test_veterinario_internacao_routes_fachada_e_modulos_abaixo_de_700_linhas():
    files = [
        Path(facade.__file__),
        Path(listagem_config_routes.__file__),
        Path(agenda_routes.__file__),
        Path(mutacao_routes.__file__),
        Path(historico_routes.__file__),
    ]

    for path in files:
        assert len(path.read_text(encoding="utf-8").splitlines()) < 700

    facade_source = Path(facade.__file__).read_text(encoding="utf-8")
    assert "@router.get" not in facade_source
    assert "@router.post" not in facade_source
    assert "router.include_router(listagem_config_router)" in facade_source
    assert "router.include_router(agenda_router)" in facade_source
    assert "router.include_router(mutacao_router)" in facade_source
    assert "router.include_router(historico_router)" in facade_source
