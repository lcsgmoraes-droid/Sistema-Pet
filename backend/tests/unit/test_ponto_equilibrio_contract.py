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
    assert "ponto_equilibrio = despesas_fixas / margem_contribuicao_percentual" in source
    assert "custos_variaveis = cmv_estimado + despesas_variaveis" in source
    assert "Produto.preco_custo" in source
    assert "TipoDespesa.e_custo_fixo" in source
    assert "DRESubcategoria.custo_pe" in source
    assert "DRESubcategoria.tipo_custo" in source
    assert "_classificar_conta_ponto_equilibrio" in source
    assert "_calcular_complemento_folha_gerencial" in source
    assert "despesas_estoque_excluidas" in source
    assert "_conta_eh_compra_estoque_para_pe" in source
    assert "detalhes_classificacao" in source


def test_frontend_tem_tela_financeira_de_ponto_equilibrio():
    app = _frontend_source("src/App.jsx")
    menu = _frontend_source("src/components/layout/menuConfig.js")
    page = _frontend_source("src/pages/PontoEquilibrio.jsx")
    dashboard = _frontend_source("src/pages/DashboardFinanceiro.jsx")

    assert 'const PontoEquilibrio = lazy(() => import("./pages/PontoEquilibrio"))' in app
    assert 'path="financeiro/ponto-equilibrio"' in app
    assert 'path: "/financeiro/ponto-equilibrio"' in menu
    assert 'label: "Ponto de Equilibrio"' in menu
    assert "Ponto de Equilibrio" in page
    assert "custos fixos / margem de contribuicao" in page
    assert "Origem dos valores" in page
    assert "Despesas fixas" in page
    assert "Despesas variaveis" in page
    assert "Fora do PE" in page
    assert "Calculadora de impacto" in page
    assert "Impacto mensal no custo fixo" in page
    assert "Novo ponto minimo" in page
    assert "Vendas a mais/menos" in page
    assert "fimMesAtual" in page
    assert "data_fim: fimMesAtual()" in page
    assert "Ponto de Equilíbrio —" not in dashboard
