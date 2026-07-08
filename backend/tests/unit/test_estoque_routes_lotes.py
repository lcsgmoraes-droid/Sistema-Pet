from pathlib import Path
from types import SimpleNamespace

import pytest

from app import estoque_entrada_manual_routes
from app.estoque_entrada_manual_routes import _registrar_lote_entrada


ROOT = Path(__file__).resolve().parents[2]


class _FakeQuery:
    def __init__(self, resultado):
        self.resultado = resultado

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.resultado


class _FakeDB:
    def __init__(self, lote_existente=None):
        self.lote_existente = lote_existente
        self.last_added = None

    def query(self, model):
        return _FakeQuery(self.lote_existente)

    def add(self, obj):
        self.last_added = obj

    def flush(self):
        if self.last_added is not None and getattr(self.last_added, "id", None) is None:
            self.last_added.id = 501


def test_registrar_lote_entrada_ativa_controle_lote_e_atualiza_lote_existente():
    produto = SimpleNamespace(
        id=6745,
        sku="026370.1",
        codigo="026370.1",
        preco_custo=49.9,
        controle_lote=False,
    )
    lote_existente = SimpleNamespace(
        id=77,
        quantidade_inicial=2.0,
        quantidade_disponivel=1.0,
        quantidade_reservada=0.0,
        data_fabricacao=None,
        data_validade=None,
        custo_unitario=40.0,
        status="esgotado",
    )
    db = _FakeDB(lote_existente=lote_existente)

    lote, lote_id = _registrar_lote_entrada(
        db=db,
        produto=produto,
        quantidade=3.0,
        custo_unitario=55.0,
        numero_lote="LOTE-123",
        data_fabricacao="2026-03-29",
        data_validade="2026-10-30",
    )

    assert produto.controle_lote is True
    assert lote is lote_existente
    assert lote_id == 77
    assert lote.quantidade_inicial == pytest.approx(5.0)
    assert lote.quantidade_disponivel == pytest.approx(4.0)
    assert lote.custo_unitario == pytest.approx(55.0)
    assert lote.status == "ativo"
    assert lote.data_validade is not None


def test_registrar_lote_entrada_cria_lote_novo_quando_nao_existe(monkeypatch):
    class ProdutoLoteFake:
        produto_id = object()
        nome_lote = object()

        def __init__(self, **kwargs):
            for chave, valor in kwargs.items():
                setattr(self, chave, valor)
            self.id = None

    monkeypatch.setattr(estoque_entrada_manual_routes, "ProdutoLote", ProdutoLoteFake)

    produto = SimpleNamespace(
        id=6745,
        sku="026370.1",
        codigo="026370.1",
        preco_custo=49.9,
        controle_lote=False,
    )
    db = _FakeDB(lote_existente=None)

    lote, lote_id = _registrar_lote_entrada(
        db=db,
        produto=produto,
        quantidade=2.0,
        custo_unitario=60.0,
        numero_lote="LOTE-NOVO",
        data_fabricacao="2026-03-29",
        data_validade="2026-12-31",
    )

    assert produto.controle_lote is True
    assert lote is db.last_added
    assert lote_id == 501
    assert lote.nome_lote == "LOTE-NOVO"
    assert lote.quantidade_inicial == pytest.approx(2.0)
    assert lote.quantidade_disponivel == pytest.approx(2.0)
    assert lote.data_validade is not None


def test_entrada_produto_por_lote_notifica_pendencias_do_pdv():
    source = (ROOT / "app" / "produtos" / "lotes_routes.py").read_text(
        encoding="utf-8"
    )
    entrada_start = source.index("def entrada_estoque(")
    entrada_source = source[entrada_start : source.index("def saida_estoque_fifo(", entrada_start)]

    assert "verificar_e_notificar_pendencias" in entrada_source
    assert "quantidade_entrada=entrada.quantidade" in entrada_source
