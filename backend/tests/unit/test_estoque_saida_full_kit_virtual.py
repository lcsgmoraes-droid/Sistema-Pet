from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app import estoque_saida_full_routes as routes
from app.estoque_saida_full_routes import SaidaFullNFItemRequest, SaidaFullNFRequest
from app.produtos_models import Produto, ProdutoKitComponente


class _ProdutoQuery:
    def __init__(self, db):
        self.db = db

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.db.produtos.pop(0)


class _ComponentesQuery:
    def __init__(self, db):
        self.db = db

    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return list(self.db.componentes)


class _FakeDB:
    def __init__(self, *, produtos, componentes=None):
        self.produtos = list(produtos)
        self.componentes = list(componentes or [])
        self.added = []

    def query(self, model):
        if model is Produto:
            return _ProdutoQuery(self)
        if model is ProdutoKitComponente:
            return _ComponentesQuery(self)
        raise AssertionError(f"Modelo inesperado: {model}")

    def add(self, obj):
        self.added.append(obj)


def _produto(**overrides):
    dados = {
        "id": 1,
        "tenant_id": 10,
        "codigo": "SKU",
        "nome": "Produto",
        "tipo_produto": "SIMPLES",
        "tipo_kit": None,
        "estoque_atual": 0,
        "preco_custo": 0,
    }
    dados.update(overrides)
    return SimpleNamespace(**dados)


def test_validacao_saida_full_usa_estoque_virtual_do_kit(monkeypatch):
    kit = _produto(
        id=6936,
        codigo="RA1091-3",
        nome="KIT 3 GOLD PAPA FILHOTE REFIL 400G - REINO DAS AVES",
        tipo_produto="KIT",
        tipo_kit="VIRTUAL",
        estoque_atual=-1,
    )
    db = _FakeDB(produtos=[kit])

    monkeypatch.setattr(
        routes,
        "KitEstoqueService",
        SimpleNamespace(calcular_estoque_virtual_kit=lambda *args, **kwargs: 31),
        raising=False,
    )

    problemas = routes._problemas_estoque_saida_full_nf(
        db,
        tenant_id=10,
        itens=[SaidaFullNFItemRequest(sku="RA1091-3", quantidade=31)],
    )

    assert problemas == []


def test_processar_saida_full_kit_virtual_baixa_componentes_e_registra_fluxo_virtual(
    monkeypatch,
):
    kit = _produto(
        id=6936,
        codigo="RA1091-3",
        nome="KIT 3 GOLD PAPA FILHOTE REFIL 400G - REINO DAS AVES",
        tipo_produto="KIT",
        tipo_kit="VIRTUAL",
        estoque_atual=-1,
        preco_custo=54.99,
    )
    componente = _produto(
        id=1091,
        codigo="RA1091",
        nome="GOLD PAPA FILHOTE REFIL 400G - REINO DAS AVES",
        estoque_atual=95,
        preco_custo=18.33,
    )
    composicao = SimpleNamespace(
        kit_id=kit.id,
        produto_componente_id=componente.id,
        quantidade=3,
    )
    db = _FakeDB(produtos=[kit, componente], componentes=[composicao])

    monkeypatch.setattr(
        routes,
        "KitEstoqueService",
        SimpleNamespace(
            calcular_estoque_virtual_kit=lambda *args, **kwargs: int(
                componente.estoque_atual // 3
            )
        ),
        raising=False,
    )

    resultado = routes._processar_item_saida_full_nf(
        db,
        tenant_id=10,
        item=SaidaFullNFItemRequest(sku="RA1091-3", quantidade=3),
        numero_nf="FULL-123",
        observacao_movimentacao="Saida FULL por NF FULL-123",
        current_user=SimpleNamespace(id=99),
    )

    assert componente.estoque_atual == 86
    assert kit.estoque_atual == -1
    assert resultado["estoque_anterior"] == 31
    assert resultado["estoque_novo"] == 28
    assert resultado["componentes_baixados"] == [
        {
            "produto_id": componente.id,
            "sku": componente.codigo,
            "nome": componente.nome,
            "quantidade": 9,
            "estoque_anterior": 95,
            "estoque_novo": 86,
        }
    ]

    movimento_componente = next(m for m in db.added if m.produto_id == componente.id)
    movimento_kit = next(m for m in db.added if m.produto_id == kit.id)

    assert movimento_componente.quantidade == 9
    assert movimento_componente.quantidade_anterior == 95
    assert movimento_componente.quantidade_nova == 86
    assert movimento_componente.valor_total == 9 * componente.preco_custo
    assert movimento_kit.quantidade == 3
    assert movimento_kit.quantidade_anterior == 31
    assert movimento_kit.quantidade_nova == 28
    assert movimento_kit.valor_total == 0


def test_processar_saida_full_simples_bloqueia_negativo_por_padrao():
    produto = _produto(
        id=101, codigo="SKU-NEG", nome="Produto sem saldo", estoque_atual=1
    )
    db = _FakeDB(produtos=[produto])

    with pytest.raises(HTTPException) as excinfo:
        routes._processar_item_saida_full_nf(
            db,
            tenant_id=10,
            item=SaidaFullNFItemRequest(sku="SKU-NEG", quantidade=3),
            numero_nf="FULL-NEG",
            observacao_movimentacao="Saida FULL por NF FULL-NEG",
            current_user=SimpleNamespace(id=99),
        )

    assert excinfo.value.status_code == 400
    assert produto.estoque_atual == 1
    assert db.added == []


def test_payload_saida_full_aceita_confirmacao_para_estoque_negativo():
    payload = SaidaFullNFRequest(
        numero_nf="FULL-NEG",
        plataforma="full",
        itens=[SaidaFullNFItemRequest(sku="SKU-NEG", quantidade=3)],
        permitir_estoque_negativo=True,
    )

    assert payload.permitir_estoque_negativo is True


def test_processar_saida_full_simples_permite_negativo_com_confirmacao():
    produto = _produto(
        id=101,
        codigo="SKU-NEG",
        nome="Produto sem saldo",
        estoque_atual=1,
        preco_custo=12.5,
    )
    db = _FakeDB(produtos=[produto])

    resultado = routes._processar_item_saida_full_nf(
        db,
        tenant_id=10,
        item=SaidaFullNFItemRequest(sku="SKU-NEG", quantidade=3),
        numero_nf="FULL-NEG",
        observacao_movimentacao="Saida FULL por NF FULL-NEG",
        current_user=SimpleNamespace(id=99),
        permitir_estoque_negativo=True,
    )

    assert produto.estoque_atual == -2
    assert resultado["estoque_anterior"] == 1
    assert resultado["estoque_novo"] == -2
    assert resultado["estoque_negativo"] is True
    assert resultado["faltante"] == 2

    movimento = db.added[0]
    assert movimento.quantidade_anterior == 1
    assert movimento.quantidade_nova == -2
    assert movimento.valor_total == 3 * produto.preco_custo
