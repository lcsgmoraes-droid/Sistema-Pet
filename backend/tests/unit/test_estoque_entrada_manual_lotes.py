from types import SimpleNamespace

import pytest

import app.estoque_entrada_manual_routes as estoque_entrada_manual_routes
from app.estoque_entrada_manual_routes import _registrar_lote_entrada


class _FakeQuery:
    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return None


class _FakeDB:
    def __init__(self):
        self.last_added = None

    def query(self, model):
        return _FakeQuery()

    def add(self, obj):
        self.last_added = obj

    def flush(self):
        if self.last_added is not None and getattr(self.last_added, "id", None) is None:
            self.last_added.id = 901


def test_registrar_lote_entrada_usa_codigo_quando_produto_nao_tem_sku(monkeypatch):
    class ProdutoLoteFake:
        produto_id = object()
        nome_lote = object()

        def __init__(self, **kwargs):
            for chave, valor in kwargs.items():
                setattr(self, chave, valor)
            self.id = None

    monkeypatch.setattr(estoque_entrada_manual_routes, "ProdutoLote", ProdutoLoteFake)

    produto = SimpleNamespace(
        id=5497,
        codigo="PROD-5497",
        codigo_barras="7890000000000",
        preco_custo=12.5,
        controle_lote=False,
    )
    db = _FakeDB()

    lote, lote_id = _registrar_lote_entrada(
        db=db,
        produto=produto,
        quantidade=1.0,
        custo_unitario=13.0,
        numero_lote=None,
        data_fabricacao=None,
        data_validade="2026-12-31",
    )

    assert produto.controle_lote is True
    assert lote is db.last_added
    assert lote_id == 901
    assert lote.nome_lote.startswith("PROD-5497-")
    assert lote.quantidade_inicial == pytest.approx(1.0)
    assert lote.quantidade_disponivel == pytest.approx(1.0)
