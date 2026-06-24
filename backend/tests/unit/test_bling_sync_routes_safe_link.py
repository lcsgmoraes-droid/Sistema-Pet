from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException

from app.bling_sync_routes import _buscar_item_bling_para_vinculo, _upsert_sync_vinculo


TENANT_ID = UUID("11111111-1111-4111-8111-111111111111")


class FakeQuery:
    def __init__(self, result):
        self.result = result

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.result


class FakeDb:
    def __init__(self, results):
        self.results = list(results)
        self.added = []

    def query(self, *args, **kwargs):
        result = self.results.pop(0) if self.results else None
        return FakeQuery(result)

    def add(self, value):
        self.added.append(value)


def test_upsert_sync_vinculo_bloqueia_bling_id_ja_vinculado_a_outro_produto():
    conflito = SimpleNamespace(
        produto_id=99,
        tenant_id=TENANT_ID,
        bling_produto_id="123456",
    )
    produto = SimpleNamespace(
        id=10,
        tenant_id=TENANT_ID,
        tipo_produto="SIMPLES",
    )
    db = FakeDb([conflito])

    with pytest.raises(HTTPException) as exc:
        _upsert_sync_vinculo(db, TENANT_ID, produto, "123456")

    assert exc.value.status_code == 409
    assert "ja esta vinculado" in exc.value.detail


class FakeBling:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def listar_produtos(self, **params):
        self.calls.append(params)
        key = next((name for name in ("codigo", "sku", "nome") if name in params), "")
        return {"data": self.responses.get(key, [])}


def test_buscar_item_bling_para_vinculo_nao_usa_nome_para_auto_link():
    bling = FakeBling(
        {
            "codigo": [],
            "sku": [],
            "nome": [{"id": "999", "codigo": "OUTRO-SKU", "nome": "Mesmo nome"}],
        }
    )

    item = _buscar_item_bling_para_vinculo(bling, "SKU-1", "Mesmo nome")

    assert item is None
    assert all("nome" not in call for call in bling.calls)


def test_buscar_item_bling_para_vinculo_nao_colapsa_pontuacao_do_sku():
    bling = FakeBling(
        {
            "codigo": [{"id": "999", "codigo": "ABC1", "sku": "ABC1"}],
            "sku": [],
        }
    )

    item = _buscar_item_bling_para_vinculo(bling, "ABC.1", "")

    assert item is None
