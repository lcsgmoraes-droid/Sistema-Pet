from types import SimpleNamespace

from app.vendas import estoque_baixa


def _produto():
    return SimpleNamespace(
        id=10,
        nome="Racao teste",
        controlar_estoque=True,
        tipo_produto="SIMPLES",
    )


def _baixar(monkeypatch, lotes):
    monkeypatch.setattr(
        estoque_baixa.EstoqueService,
        "baixar_estoque",
        lambda **_kwargs: {
            "produto_nome": "Racao teste",
            "estoque_anterior": 10,
            "estoque_novo": 9,
            "lotes_consumidos": lotes,
        },
    )
    item = SimpleNamespace(lote_id=None)
    estoque_baixa.processar_baixa_estoque_item(
        produto=_produto(),
        quantidade_vendida=1,
        venda_id=20,
        user_id=1,
        tenant_id="tenant-1",
        db=SimpleNamespace(),
        venda_item=item,
    )
    return item


def test_venda_item_recebe_lote_unico_realmente_consumido(monkeypatch):
    item = _baixar(
        monkeypatch,
        [{"lote_id": 2057, "quantidade": 1, "nome_lote": "NF46270-4"}],
    )

    assert item.lote_id == 2057


def test_venda_item_nao_escolhe_lote_quando_fifo_consumiu_mais_de_um(monkeypatch):
    item = _baixar(
        monkeypatch,
        [
            {"lote_id": 2057, "quantidade": 0.4},
            {"lote_id": 2088, "quantidade": 0.6},
        ],
    )

    assert item.lote_id is None
