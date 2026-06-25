from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
FRONTEND = ROOT / "frontend" / "src" / "components"


def _source(relative_path: str) -> str:
    return (FRONTEND / relative_path).read_text(encoding="utf-8")


def _line_count(source: str) -> int:
    return len(source.splitlines())


def test_modal_pagamento_publico_orquestra_controller_e_view():
    source = _source("ModalPagamento.jsx")

    assert 'ModalPagamentoView from "./modalPagamento/ModalPagamentoView"' in source
    assert (
        'useModalPagamentoController from "./modalPagamento/useModalPagamentoController"'
        in source
    )
    assert _line_count(source) < 80


def test_controller_preserva_fluxos_criticos_de_recebimento():
    controller = _source("modalPagamento/useModalPagamentoController.js")
    utils = _source("modalPagamentoUtils.js")

    assert "api.get(`/financeiro/formas-pagamento`)" in controller
    assert "finalizarVenda" in controller
    assert "emitirNotaFiscalAssistida" in controller
    assert "useRevealFloatingPanel" in controller
    assert "vendedor_id: venda.funcionario_id || null" in utils
    assert _line_count(controller) < 900


def test_view_concentra_shell_resumo_rodape_e_credito_excedente():
    source = _source("modalPagamento/ModalPagamentoView.jsx")

    assert "ModalPagamentoFormaPanel" in source
    assert 'data-testid="modal-pagamento-footer-adicionar"' in source
    assert "ModalAdicionarCredito" in source
    assert _line_count(source) < 700


def test_painel_concentra_formulario_da_forma_de_pagamento():
    source = _source("modalPagamento/ModalPagamentoFormaPanel.jsx")

    assert "CurrencyInput" in source
    assert "PaymentMethodIcon" in source
    assert "BANDEIRAS_CARTAO" in source
    assert _line_count(source) < 700
