from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session, make_transient_to_detached

from app.bling_integration_parts.catalogo import BlingCatalogoMixin
from app.produtos_models import Produto
from app.services.bling_cost_sync_events import (
    _capture_changed_product_costs,
    _enqueue_captured_product_costs,
)
from app.services.bling_cost_sync_service import (
    BlingCostSyncConfigurationError,
    BlingCostSyncService,
    montar_payload_custo_produto_fornecedor,
    selecionar_produto_fornecedor_bling,
)


def test_catalog_client_lists_and_updates_product_supplier():
    calls = []
    client = BlingCatalogoMixin()
    client._request = lambda method, endpoint, data=None: calls.append(
        (method, endpoint, data)
    ) or {"data": []}

    client.listar_produtos_fornecedores("123", pagina=2, limite=150)
    client.atualizar_produto_fornecedor("456", {"precoCusto": 19.9})

    assert calls == [
        (
            "GET",
            "/produtos/fornecedores",
            {"idProduto": 123, "pagina": 2, "limite": 100},
        ),
        (
            "PUT",
            "/produtos/fornecedores/456",
            {"precoCusto": 19.9},
        ),
    ]


def test_selects_default_supplier_and_rejects_ambiguous_links():
    items = [
        {"id": 1, "padrao": False},
        {"id": 2, "padrao": True},
    ]
    assert selecionar_produto_fornecedor_bling(items)["id"] == 2

    assert (
        selecionar_produto_fornecedor_bling(
            [{"id": 7}, {"id": 8}],
            cached_id="8",
        )["id"]
        == 8
    )

    with pytest.raises(BlingCostSyncConfigurationError):
        selecionar_produto_fornecedor_bling([{"id": 7}, {"id": 8}])


def test_cost_payload_preserves_purchase_price_and_changes_only_cost():
    payload = montar_payload_custo_produto_fornecedor(
        {
            "id": 55,
            "descricao": "Produto Megazoo",
            "codigo": "MEGA-01",
            "precoCusto": 10.0,
            "precoCompra": 8.75,
            "padrao": True,
            "garantia": 3,
            "produto": {"id": 123},
            "fornecedor": {"id": 987},
        },
        bling_produto_id="123",
        custo=12.34567,
    )

    assert payload == {
        "descricao": "Produto Megazoo",
        "codigo": "MEGA-01",
        "precoCompra": 8.75,
        "padrao": True,
        "garantia": 3,
        "precoCusto": 12.3457,
        "produto": {"id": 123},
        "fornecedor": {"id": 987},
    }


def test_product_cost_change_is_captured_by_central_listener(monkeypatch):
    tenant_id = uuid4()
    product = Produto(
        id=42,
        tenant_id=tenant_id,
        codigo="MEGA-42",
        nome="Megazoo Teste",
        preco_custo=10.0,
    )
    make_transient_to_detached(product)
    session = Session()
    session.add(product)
    product.preco_custo = 12.5

    captured = {}

    def fake_queue(_cls, db, **kwargs):
        captured.update({"db": db, **kwargs})
        return {"ok": True}

    monkeypatch.setattr(
        BlingCostSyncService,
        "queue_product_cost_sync",
        classmethod(fake_queue),
    )

    _capture_changed_product_costs(session, None, None)
    _enqueue_captured_product_costs(session, None)

    assert captured["db"] is session
    assert captured["produto_id"] == 42
    assert captured["custo_novo"] == 12.5
    assert captured["origem"] == "evento_produto"
    assert captured["flush"] is False
    session.close()


class _FakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def join(self, *_args, **_kwargs):
        return self

    def outerjoin(self, *_args, **_kwargs):
        return self

    def filter(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def all(self):
        return self.rows


class _FakeDB:
    def __init__(self, rows):
        self.rows = rows

    def query(self, *_args, **_kwargs):
        return _FakeQuery(self.rows)


def _product(product_id, cost, *, parent=False):
    return SimpleNamespace(
        id=product_id,
        codigo=f"MEGA-{product_id}",
        nome=f"Produto {product_id}",
        preco_custo=cost,
        tipo_produto="PAI" if parent else "SIMPLES",
        is_parent=parent,
    )


def test_brand_preview_classifies_and_enqueues_only_eligible_products(monkeypatch):
    linked = SimpleNamespace(sincronizar=True, bling_produto_id="1001")
    unlinked = SimpleNamespace(sincronizar=True, bling_produto_id=None)
    rows = [
        (_product(1, 15.5), linked, None),
        (_product(2, 0), linked, None),
        (_product(3, 12), unlinked, None),
        (_product(4, 20, parent=True), linked, None),
    ]
    queued = []

    def fake_queue(_cls, _db, **kwargs):
        queued.append(kwargs["produto_id"])
        return {"ok": True, "queue_id": 77}

    monkeypatch.setattr(
        BlingCostSyncService,
        "queue_product_cost_sync",
        classmethod(fake_queue),
    )

    result = BlingCostSyncService.preview_or_enqueue_brand(
        _FakeDB(rows),
        tenant_id=uuid4(),
        brand_name="Megazoo",
        enqueue=True,
    )

    assert result["total_marca"] == 4
    assert result["elegiveis"] == 1
    assert result["enfileirados"] == 1
    assert result["custos_invalidos"] == 1
    assert result["sem_vinculo_bling"] == 1
    assert result["produtos_pai_ignorados"] == 1
    assert queued == [1]
