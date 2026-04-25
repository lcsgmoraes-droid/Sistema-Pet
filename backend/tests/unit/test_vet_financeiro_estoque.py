import os
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


class _FakeDb:
    def __init__(self, produtos):
        self.produtos = produtos
        self.added = []
        self._next_id = 100

    def query(self, model):
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
