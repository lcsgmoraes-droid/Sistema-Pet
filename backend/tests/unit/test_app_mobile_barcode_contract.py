from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_barcode_route_returns_only_products_sellable_in_app_cart():
    source = (BACKEND_ROOT / "app/routes/app_mobile_routes.py").read_text(encoding="utf-8")
    assert "Produto.ativo == True" in source
    assert "Produto.situacao.is_not(False)" in source
    assert 'Produto.tipo_produto.in_(["SIMPLES", "VARIACAO", "KIT"])' in source
    assert "Produto.is_sellable == True" in source
    assert "Produto.anunciar_app == True" in source
