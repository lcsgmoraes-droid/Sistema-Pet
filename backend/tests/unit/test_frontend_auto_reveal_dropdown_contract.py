from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
FRONTEND = ROOT / "frontend" / "src"


def _frontend_source(relative_path: str) -> str:
    return (FRONTEND / relative_path).read_text(encoding="utf-8")


def test_seletores_principais_usam_reveal_de_painel_flutuante():
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


def test_modal_pagamento_revela_alerta_margem_e_justificativa():
    fonte = _frontend_source("components/ModalPagamento.jsx")

    assert "useRevealFloatingPanel" in fonte
    assert "statusMargemRef" in fonte
    assert "justificativaRef" in fonte
    assert "mostrarCampoJustificativa" in fonte
