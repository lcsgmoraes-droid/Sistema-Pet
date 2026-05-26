from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = REPO_ROOT / "backend"


def _backend_source(relative_path: str) -> str:
    return (BACKEND_ROOT / relative_path).read_text(encoding="utf-8")


def _frontend_source(relative_path: str) -> str:
    return (REPO_ROOT / "frontend" / relative_path).read_text(encoding="utf-8")


def test_api_ponto_equilibrio_usa_formula_de_margem_de_contribuicao():
    source = _backend_source("app/dashboard_routes.py")

    assert '@router.get("/financeiro/ponto-equilibrio")' in source
    assert "margem_contribuicao_percentual" in source
    assert "fonte_margem" in source
    assert "MARGEM_PONTO_EQUILIBRIO_OPCOES" in source
    assert "_calcular_margem_referencia_ponto_equilibrio" in source
    assert "margem_usada_percentual" in source
    assert "margem_periodo_percentual" in source
    assert "ponto_equilibrio = despesas_fixas / margem_usada_decimal" in source
    assert "Produto.preco_custo" in source
    assert "build_venda_rentabilidade_snapshot" in source
    assert "_preparar_snapshots_margem_vendas_pe" in source
    assert "_bulk_estoque_custos_por_venda" in source
    assert "_bulk_comissoes_por_venda" in source
    assert "_bulk_cupons_por_venda" in source
    assert "_bulk_cashback_por_venda" in source
    assert "_bulk_taxa_operacional_por_venda" in source
    assert "_somar_componentes_margem_vendas_pe" in source
    assert "_conta_variavel_ja_coberta_pelo_snapshot_pe" in source
    assert "detalhes_margem" in source
    assert "modo_custo_fiscal" in source
    assert "TipoDespesa.e_custo_fixo" in source
    assert "DRESubcategoria.custo_pe" in source
    assert "DRESubcategoria.tipo_custo" in source
    assert "_classificar_conta_ponto_equilibrio" in source
    assert "_calcular_complemento_folha_gerencial" in source
    assert "despesas_estoque_excluidas" in source
    assert "_conta_eh_compra_estoque_para_pe" in source
    assert "detalhes_classificacao" in source


def test_api_ponto_equilibrio_tem_detalhes_lazy_para_nao_pesar_resumo():
    source = _backend_source("app/dashboard_routes.py")

    assert '@router.get("/financeiro/ponto-equilibrio/detalhes")' in source
    assert "incluir_detalhes: bool = False" in source
    assert "incluir_detalhes=incluir_detalhes" in source
    assert "_paginar_detalhes_ponto_equilibrio" in source
    assert "page_size" in source
    assert '"detalhes_margem"' in source
    assert '"detalhes_classificacao"' in source


def test_frontend_tem_tela_financeira_de_ponto_equilibrio():
    app = _frontend_source("src/App.jsx")
    menu = _frontend_source("src/components/layout/menuConfig.js")
    page = _frontend_source("src/pages/PontoEquilibrio.jsx")
    impact_utils = _frontend_source("src/pages/pontoEquilibrioImpactoUtils.js")
    dashboard = _frontend_source("src/pages/DashboardFinanceiro.jsx")

    assert 'const PontoEquilibrio = lazy(() => import("./pages/PontoEquilibrio"))' in app
    assert 'path="financeiro/ponto-equilibrio"' in app
    assert 'path: "/financeiro/ponto-equilibrio"' in menu
    assert 'label: "Ponto de Equilibrio"' in menu
    assert "Ponto de Equilibrio" in page
    assert "Fonte da margem" in page
    assert "fonte_margem" in page
    assert "Visao de custo" in page
    assert "modo_custo_fiscal" in page
    assert "Media 12 meses fechados" in page
    assert "Somente documentos emitidos" in page
    assert "margem_usada_percentual" in page
    assert "custos fixos / margem de contribuicao" in page
    assert "Origem das contas e custos fixos" in page
    assert "Despesas fixas" in page
    assert "Outros variaveis" in page
    assert "Fora do PE" in page
    assert "Detalhamento da margem" in page
    assert "abrirDetalhesPontoEquilibrio" in page
    assert "/financeiro/ponto-equilibrio/detalhes" in page
    assert "linhaDetalhe" in page
    assert "detalhesLinha" in page
    assert "Lancamentos do ponto de equilibrio" in page
    assert "Calculadora de impacto" in page
    assert "Impacto mensal no custo fixo" in page
    assert "Faturamento projetado" in page
    assert "Resultado projetado do mes" in page
    assert "Novo ponto minimo" in page
    assert "Vendas a mais/menos" in page
    assert '{ id: "simulador", label: "Simulador" }' in page
    assert '{ id: "detalhamento", label: "Detalhamento" }' in page
    assert '{ id: "graficos", label: "Graficos" }' in page
    assert 'abaAtiva === "detalhamento"' in page
    assert 'abaAtiva === "simulador"' in page
    assert 'abaAtiva === "graficos"' in page
    assert "Analise dos custos" in page
    assert "Parecer gerencial" in page
    assert "Aluguel sobre faturamento" in impact_utils
    assert "Folha e pro-labore" in impact_utils
    assert "Porte do petshop" in page
    assert "Pequeno" in page
    assert "Medio" in page
    assert "Grande" in page
    assert "Faixas gerenciais mensais" in page
    assert "fimMesAtual" in page
    assert "data_fim: fimMesAtual()" in page
    assert "Ponto de Equilíbrio —" not in dashboard
