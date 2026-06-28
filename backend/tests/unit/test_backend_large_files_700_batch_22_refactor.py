import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from app import analise_racoes_routes as facade
from app.analise_racoes_routes_parts import (
    filtros_routes,
    produtos_routes,
    resumo_routes,
    segmentos_routes,
)


def _route_pairs(router):
    return {
        (method, route.path)
        for route in router.routes
        for method in getattr(route, "methods", set())
    }


def test_analise_racoes_routes_preserva_endpoints_publicos():
    paths = _route_pairs(facade.router)

    assert ("GET", "/racoes/analises/resumo") in paths
    assert ("POST", "/racoes/analises/margem-por-segmento") in paths
    assert ("POST", "/racoes/analises/comparacao-marcas") in paths
    assert ("GET", "/racoes/analises/ranking-vendas") in paths
    assert ("GET", "/racoes/analises/opcoes-filtros") in paths
    assert ("POST", "/racoes/analises/produtos-comparacao") in paths


def test_analise_racoes_routes_preserva_reexports_legados():
    assert facade.obter_resumo_dashboard is resumo_routes.obter_resumo_dashboard
    assert (
        facade.analisar_margem_por_segmento
        is segmentos_routes.analisar_margem_por_segmento
    )
    assert facade.comparar_marcas is segmentos_routes.comparar_marcas
    assert facade.obter_ranking_vendas is segmentos_routes.obter_ranking_vendas
    assert facade.obter_opcoes_filtros is filtros_routes.obter_opcoes_filtros
    assert (
        facade.obter_produtos_para_comparacao
        is produtos_routes.obter_produtos_para_comparacao
    )


def test_analise_racoes_routes_fachada_e_modulos_abaixo_de_700_linhas():
    files = [
        Path(facade.__file__),
        Path(resumo_routes.__file__),
        Path(segmentos_routes.__file__),
        Path(filtros_routes.__file__),
        Path(produtos_routes.__file__),
    ]

    for path in files:
        assert len(path.read_text(encoding="utf-8").splitlines()) < 700

    facade_source = Path(facade.__file__).read_text(encoding="utf-8")
    assert "@router." not in facade_source
    assert 'APIRouter(prefix="/racoes/analises"' in facade_source
    assert "router.include_router(resumo_router)" in facade_source
    assert "router.include_router(segmentos_router)" in facade_source
    assert "router.include_router(filtros_router)" in facade_source
    assert "router.include_router(produtos_router)" in facade_source
