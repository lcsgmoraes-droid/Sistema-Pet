from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_barcode_route_returns_only_products_sellable_in_app_cart():
    source = (BACKEND_ROOT / "app/routes/app_mobile_routes.py").read_text(encoding="utf-8")
    assert "Produto.ativo == True" in source
    assert "Produto.situacao.is_not(False)" in source
    assert "Produto.is_sellable == True" in source
    assert "Produto.anunciar_app == True" in source
    assert "prioridade_estoque" in source
    assert "Produto.estoque_atual" in source
    assert ".order_by(prioridade_estoque.asc(), Produto.is_parent.asc(), Produto.id.asc())" in source


def test_cart_stock_error_explains_existing_cart_quantity():
    source = (BACKEND_ROOT / "app/routes/ecommerce_cart.py").read_text(encoding="utf-8")

    assert "Voce ja tem " in source
    assert "unidade(s) desse produto no carrinho" in source
    assert "Estoque disponivel" in source
