from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_contas_pagar_tem_atalhos_de_periodo():
    source = (REPO_ROOT / "frontend/src/components/ContasPagar.jsx").read_text(encoding="utf-8")

    assert "PERIODOS_RAPIDOS_CONTAS_PAGAR" in source
    assert "Hoje" in source
    assert "Amanha" in source
    assert "Semana" in source
    assert "Mes" in source
    assert "calcularIntervaloPeriodoRapido" in source
    assert "aplicarPeriodoRapido" in source
    assert "periodo_rapido" in source
    assert "filtros.periodo_rapido === periodo.value" in source


def test_contas_pagar_lista_abre_edicao_de_lancamento():
    source = (REPO_ROOT / "frontend/src/components/ContasPagar.jsx").read_text(encoding="utf-8")

    assert "const [contaEdicao, setContaEdicao]" in source
    assert "abrirModalEdicao" in source
    assert "api.get(`/contas-pagar/${conta.id}`)" in source
    assert "Editar" in source
    assert "contaEdicao={contaEdicao}" in source


def test_modal_conta_pagar_suporta_modo_edicao():
    source = (REPO_ROOT / "frontend/src/components/ModalNovaContaPagar.jsx").read_text(encoding="utf-8")

    assert "contaEdicao" in source
    assert "isEditando" in source
    assert "api.patch(`/contas-pagar/${contaEdicao.id}`" in source
    assert "Editar Conta a Pagar" in source
    assert "Salvar Alteracoes" in source
