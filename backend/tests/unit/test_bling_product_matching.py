from app.bling_sync import product_matching


def test_chave_sku_estrita_preserva_pontuacao_operacional():
    assert product_matching._chave_sku_estrita("  AbC.1  ") == "abc.1"
    assert product_matching._chave_sku_estrita("ABC-1") != product_matching._chave_sku_estrita("ABC1")
    assert product_matching._chave_sku_estrita("ABC.1") != product_matching._chave_sku_estrita("ABC1")


def test_item_bling_tem_sku_estrito_usa_codigo_e_sku_sem_colapsar_pontuacao():
    item = {"codigo": "ABC.1", "sku": "ABC.1"}

    assert product_matching._item_bling_tem_sku_estrito(item, " abc.1 ") is True
    assert product_matching._item_bling_tem_sku_estrito(item, "ABC1") is False
