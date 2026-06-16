from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
FRONTEND = ROOT / "frontend" / "src"


def _frontend_source(relative_path: str) -> str:
    return (FRONTEND / relative_path).read_text(encoding="utf-8")


def test_seletores_flutuantes_revelam_lista_de_sugestoes():
    arquivos = [
        "components/pdv/PDVComissaoCard.jsx",
        "components/ui/AutocompleteSelect.jsx",
        "components/clientes/PessoaSelector.jsx",
        "components/produtos/ProdutoSelector.jsx",
    ]

    for arquivo in arquivos:
        fonte = _frontend_source(arquivo)
        assert "useRevealFloatingPanel" in fonte
        assert "panelRef" in fonte


def test_modal_pagamento_leva_para_justificativa_obrigatoria():
    fonte = _frontend_source("components/ModalPagamento.jsx")

    assert "modalPagamentoContentRef" in fonte
    assert "justificativaTextareaRef" in fonte
    assert "revelarJustificativaObrigatoria" in fonte
    assert 'data-testid="justificativa-margem-obrigatoria"' in fonte


def test_modal_pagamento_tem_adicionar_pagamento_no_rodape_quando_forma_selecionada():
    fonte = _frontend_source("components/ModalPagamento.jsx")

    assert 'data-testid="modal-pagamento-footer-adicionar"' in fonte
    assert "Adicionar Pagamento" in fonte
