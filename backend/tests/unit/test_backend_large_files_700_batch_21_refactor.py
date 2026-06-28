import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from app import formas_pagamento_routes as facade
from app.formas_pagamento_routes_parts import analise_routes, impostos_routes
from app.formas_pagamento_routes_parts import schemas as schemas_parts
from app.formas_pagamento_routes_parts import taxas_routes


def _route_pairs(router):
    return {
        (method, route.path)
        for route in router.routes
        for method in getattr(route, "methods", set())
    }


def test_formas_pagamento_routes_preserva_endpoints_publicos():
    paths = _route_pairs(facade.router)

    assert ("POST", "/formas-pagamento/taxas") in paths
    assert ("GET", "/formas-pagamento/taxas/{forma_pagamento_id}") in paths
    assert ("PUT", "/formas-pagamento/taxas/{taxa_id}") in paths
    assert ("DELETE", "/formas-pagamento/taxas/{taxa_id}") in paths
    assert ("POST", "/formas-pagamento/analisar-venda") in paths
    assert ("GET", "/formas-pagamento/impostos") in paths
    assert ("POST", "/formas-pagamento/impostos") in paths
    assert ("PUT", "/formas-pagamento/impostos/{imposto_id}/padrao") in paths


def test_formas_pagamento_routes_preserva_reexports_legados():
    assert facade.criar_taxa is taxas_routes.criar_taxa
    assert facade.listar_taxas is taxas_routes.listar_taxas
    assert facade.atualizar_taxa is taxas_routes.atualizar_taxa
    assert facade.deletar_taxa is taxas_routes.deletar_taxa
    assert facade.analisar_venda is analise_routes.analisar_venda
    assert facade.listar_impostos is impostos_routes.listar_impostos
    assert facade.criar_imposto is impostos_routes.criar_imposto
    assert facade.definir_imposto_padrao is impostos_routes.definir_imposto_padrao

    assert facade.FormaPagamentoTaxaCreate is schemas_parts.FormaPagamentoTaxaCreate
    assert facade.FormaPagamentoTaxaResponse is schemas_parts.FormaPagamentoTaxaResponse
    assert facade.ItemAnaliseVenda is schemas_parts.ItemAnaliseVenda
    assert facade.FormaPagamentoAnalise is schemas_parts.FormaPagamentoAnalise
    assert facade.AnaliseVendaRequest is schemas_parts.AnaliseVendaRequest
    assert facade.AlertaAnalise is schemas_parts.AlertaAnalise
    assert facade.DetalhamentoComissao is schemas_parts.DetalhamentoComissao
    assert facade.AnaliseVendaResponse is schemas_parts.AnaliseVendaResponse


def test_formas_pagamento_routes_fachada_e_modulos_abaixo_de_700_linhas():
    files = [
        Path(facade.__file__),
        Path(taxas_routes.__file__),
        Path(analise_routes.__file__),
        Path(impostos_routes.__file__),
        Path(schemas_parts.__file__),
    ]

    for path in files:
        assert len(path.read_text(encoding="utf-8").splitlines()) < 700

    facade_source = Path(facade.__file__).read_text(encoding="utf-8")
    assert "@router." not in facade_source
    assert 'APIRouter(prefix="/formas-pagamento"' in facade_source
    assert "router.include_router(taxas_router)" in facade_source
    assert "router.include_router(analise_router)" in facade_source
    assert "router.include_router(impostos_router)" in facade_source
