from app.services.bling_sync_service import _buscar_item_bling_para_produto


class FakeBling:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def listar_produtos(self, **params):
        self.calls.append(params)
        key = next((name for name in ("codigo", "sku", "nome") if name in params), "")
        return {"data": self.responses.get(key, [])}


def test_buscar_item_bling_para_produto_nao_usa_nome_para_auto_link():
    bling = FakeBling(
        {
            "codigo": [],
            "sku": [],
            "nome": [{"id": "999", "codigo": "OUTRO-SKU", "nome": "Mesmo nome"}],
        }
    )

    assert _buscar_item_bling_para_produto(bling, "SKU-1", "Mesmo nome") is None
    assert all("nome" not in call for call in bling.calls)


def test_buscar_item_bling_para_produto_nao_retorna_primeiro_sem_sku_igual():
    bling = FakeBling(
        {
            "codigo": [{"id": "999", "codigo": "SKU-999", "nome": "Outro"}],
            "sku": [],
        }
    )

    assert _buscar_item_bling_para_produto(bling, "SKU-1", "Produto") is None
