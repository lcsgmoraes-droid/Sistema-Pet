import os
import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

os.environ["DEBUG"] = "false"

from app import veterinario_financeiro as financeiro
from app.veterinario_financeiro import (
    _aplicar_baixa_estoque_itens,
    _aplicar_baixa_estoque_procedimento,
)


class _FakeQuery:
    def __init__(self, items):
        self.items = items

    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return self.items

    def order_by(self, *args, **kwargs):
        return self

    def with_for_update(self):
        return self


class _FakeDb:
    def __init__(self, produtos, lotes=None):
        self.produtos = produtos
        self.lotes = lotes or []
        self.added = []
        self._next_id = 100

    def query(self, model):
        if model is financeiro.ProdutoLote:
            return _FakeQuery(self.lotes)
        return _FakeQuery(self.produtos)

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        if self.added and getattr(self.added[-1], "id", None) is None:
            self.added[-1].id = self._next_id
            self._next_id += 1


def _produto(**overrides):
    base = {
        "id": 10,
        "nome": "Seringa",
        "unidade": "un",
        "ativo": True,
        "estoque_atual": 5.0,
        "preco_custo": 2.5,
        "controle_lote": False,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


class _FakeMovimentacao:
    def __init__(self, **kwargs):
        self.id = None
        for chave, valor in kwargs.items():
            setattr(self, chave, valor)


def test_baixa_estoque_itens_movimenta_produto_e_enriquece_item(monkeypatch):
    monkeypatch.setattr(financeiro, "EstoqueMovimentacao", _FakeMovimentacao)
    produto = _produto()
    db = _FakeDb([produto])

    itens, movimentacoes_ids = _aplicar_baixa_estoque_itens(
        db,
        tenant_id="tenant-a",
        user_id=7,
        itens=[{"produto_id": 10, "quantidade": 2}],
        motivo="procedimento_veterinario",
        referencia_id=33,
        referencia_tipo="procedimento_veterinario",
        documento="44",
        observacao="Baixa automática",
    )

    assert produto.estoque_atual == 3.0
    assert movimentacoes_ids == [100]
    assert itens[0]["nome"] == "Seringa"
    assert itens[0]["custo_unitario"] == 2.5
    assert itens[0]["custo_total"] == 5.0
    assert db.added[0].produto_id == 10
    assert db.added[0].quantidade == 2.0


def test_baixa_estoque_procedimento_atualiza_flags_do_procedimento(monkeypatch):
    monkeypatch.setattr(financeiro, "EstoqueMovimentacao", _FakeMovimentacao)
    produto = _produto(estoque_atual=8)
    db = _FakeDb([produto])
    procedimento = SimpleNamespace(
        id=22,
        consulta_id=9,
        nome="Aplicação",
        realizado=True,
        estoque_baixado=False,
        estoque_movimentacao_ids=[],
        insumos=[{"produto_id": 10, "quantidade": 1}],
    )

    _aplicar_baixa_estoque_procedimento(db, procedimento, "tenant-a", 7)

    assert procedimento.estoque_baixado is True
    assert procedimento.estoque_movimentacao_ids == [100]
    assert procedimento.insumos[0]["custo_total"] == 2.5
    assert produto.estoque_atual == 7.0


def test_baixa_estoque_itens_bloqueia_estoque_insuficiente():
    db = _FakeDb([_produto(estoque_atual=1)])

    with pytest.raises(HTTPException) as exc:
        _aplicar_baixa_estoque_itens(
            db,
            tenant_id="tenant-a",
            user_id=7,
            itens=[{"produto_id": 10, "quantidade": 2}],
            motivo="procedimento_veterinario",
            referencia_id=33,
            referencia_tipo="procedimento_veterinario",
            documento="44",
            observacao="Baixa automática",
        )

    assert exc.value.status_code == 400
    assert "Estoque insuficiente" in exc.value.detail


def test_baixa_estoque_itens_registra_lote_clinico_consumido(monkeypatch):
    monkeypatch.setattr(financeiro, "EstoqueMovimentacao", _FakeMovimentacao)
    produto = _produto(estoque_atual=20, controle_lote=True, unidade="ML")
    lote = SimpleNamespace(
        id=55,
        produto_id=10,
        nome_lote="CL-12-ABC",
        data_validade=None,
        ordem_entrada=1,
        quantidade_disponivel=20,
        status="ativo",
    )
    db = _FakeDb([produto], [lote])

    itens, _ = _aplicar_baixa_estoque_itens(
        db,
        tenant_id="tenant-a",
        user_id=7,
        itens=[{"produto_id": 10, "quantidade": 3}],
        motivo="procedimento_veterinario",
        referencia_id=33,
        referencia_tipo="procedimento_veterinario",
        documento="44",
        observacao="Baixa automatica",
    )

    assert lote.quantidade_disponivel == 17
    assert itens[0]["lotes_consumidos"][0]["lote_id"] == 55
    assert json.loads(db.added[0].lotes_consumidos)[0]["quantidade"] == 3


def test_baixa_clinica_bloqueia_quando_lotes_validos_nao_cobrem_consumo():
    produto = _produto(estoque_atual=20, controle_lote=True, unidade="ML")
    lote = SimpleNamespace(
        id=55,
        produto_id=10,
        nome_lote="CL-12-ABC",
        data_validade=None,
        ordem_entrada=1,
        quantidade_disponivel=2,
        status="ativo",
    )
    db = _FakeDb([produto], [lote])

    with pytest.raises(HTTPException) as exc:
        _aplicar_baixa_estoque_itens(
            db,
            tenant_id="tenant-a",
            user_id=7,
            itens=[{"produto_id": 10, "quantidade": 3}],
            motivo="procedimento_veterinario",
            referencia_id=33,
            referencia_tipo="procedimento_veterinario",
            documento="44",
            observacao="Baixa automatica",
        )

    assert exc.value.status_code == 400
    assert "Lotes validos" in exc.value.detail
    assert produto.estoque_atual == 20
