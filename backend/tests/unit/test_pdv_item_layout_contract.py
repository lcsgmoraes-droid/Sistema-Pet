from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE = REPO_ROOT / "frontend" / "src" / "components" / "pdv" / "PDVProdutosCard.jsx"
SUBTOTAL_SOURCE = REPO_ROOT / "frontend" / "src" / "components" / "SubtotalInput.jsx"


def test_pdv_item_do_carrinho_contem_nome_preco_e_acoes():
    source = SOURCE.read_text(encoding="utf-8")

    assert "data-testid=\"pdv-cart-item\"" in source
    assert "className=\"flex min-w-0 flex-1 items-start gap-2" in source
    assert "className=\"flex min-w-0 max-w-full flex-1 items-start gap-2" in source
    assert "title={item.produto_nome}" in source
    assert "className=\"flex w-full shrink-0 flex-wrap items-center justify-end gap-2 sm:w-auto" in source
    assert "className=\"shrink-0\"" in source


def test_pdv_sugestao_de_produto_nao_empurra_preco_para_fora():
    source = SOURCE.read_text(encoding="utf-8")

    assert "className=\"flex min-w-0 flex-1 items-start gap-3" in source
    assert "className=\"min-w-0 flex-1" in source
    assert "className=\"min-w-0 truncate" in source
    assert "className=\"flex shrink-0 flex-row items-center" in source


def test_subtotal_input_nao_expande_o_item_do_pdv():
    source = SUBTOTAL_SOURCE.read_text(encoding="utf-8")

    assert "className=\"w-24 shrink-0" in source
    assert "className=\"flex shrink-0 items-center gap-1" in source
