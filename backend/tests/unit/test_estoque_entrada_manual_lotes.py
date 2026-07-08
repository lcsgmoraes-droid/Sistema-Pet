from types import SimpleNamespace

import pytest
from sqlalchemy import column

import app.estoque_entrada_manual_routes as estoque_entrada_manual_routes
from app.estoque_entrada_manual_routes import (
    EntradaEstoqueRequest,
    _registrar_lote_entrada,
    entrada_estoque,
)
from app.produtos_models import Produto


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


class _RouteQuery:
    def __init__(self, item=None):
        self.item = item

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def first(self):
        return self.item


class _EntradaRouteDB:
    def __init__(self, produto):
        self.produto = produto
        self.added = []
        self.commits = 0

    def query(self, model):
        if model is Produto:
            return _RouteQuery(self.produto)
        if model is estoque_entrada_manual_routes.EstoqueMovimentacao:
            return _RouteQuery(None)
        return _RouteQuery(None)

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        return None

    def commit(self):
        self.commits += 1

    def refresh(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = 321
        if getattr(obj, "created_at", None) is None:
            obj.created_at = "2026-07-08T15:00:00"


class _FakeMovimentacao:
    produto_id = column("produto_id")
    tipo = column("tipo")
    custo_unitario = column("custo_unitario")
    id = column("id")
    created_at = column("created_at")

    def __init__(self, **kwargs):
        for chave, valor in kwargs.items():
            setattr(self, chave, valor)
        self.id = None
        self.created_at = None


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


def test_entrada_manual_notifica_pendencias_do_pdv_quando_estoque_volta(monkeypatch):
    ecommerce_calls = []
    pendencia_calls = []

    monkeypatch.setattr(
        "app.routes.ecommerce_notify_routes.notificar_clientes_estoque_disponivel",
        lambda *args, **kwargs: ecommerce_calls.append((args, kwargs)) or 0,
    )
    monkeypatch.setattr(
        "app.services.pendencia_estoque_service.verificar_e_notificar_pendencias",
        lambda *args, **kwargs: pendencia_calls.append((args, kwargs))
        or {"notificacoes_enviadas": 1},
    )
    monkeypatch.setattr(
        estoque_entrada_manual_routes,
        "sincronizar_bling_background",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        estoque_entrada_manual_routes,
        "EstoqueMovimentacao",
        _FakeMovimentacao,
    )

    tenant_id = "11111111-1111-4111-8111-111111111111"
    produto = SimpleNamespace(
        id=10,
        tenant_id=tenant_id,
        nome="Racao Teste",
        codigo="RACAO-TESTE",
        codigo_barras=None,
        estoque_atual=0,
        preco_custo=12.0,
        preco_venda=42.9,
        is_parent=False,
        tipo_produto="SIMPLES",
        tipo_kit=None,
        e_granel=False,
    )
    db = _EntradaRouteDB(produto)

    response = entrada_estoque(
        EntradaEstoqueRequest(
            produto_id=produto.id,
            quantidade=3,
            custo_unitario=13,
            motivo="compra",
        ),
        db=db,
        user_and_tenant=(SimpleNamespace(id=5, nome="Lucas"), tenant_id),
    )

    assert response["quantidade_anterior"] == 0
    assert response["quantidade_nova"] == 3
    assert ecommerce_calls
    assert pendencia_calls
    assert pendencia_calls[0][1] == {
        "db": db,
        "tenant_id": tenant_id,
        "produto_id": produto.id,
        "quantidade_entrada": 3,
    }
