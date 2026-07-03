from types import SimpleNamespace

import app.services.bling_sync_auto_link as bling_sync_auto_link
from app.services.bling_sync_service import (
    BlingSyncService,
    _buscar_item_bling_para_produto,
)


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


class FakeQuery:
    def __init__(self, db, kind):
        self.db = db
        self.kind = kind

    def filter(self, *args, **kwargs):
        return self

    def outerjoin(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def limit(self, value):
        return self

    def subquery(self):
        return []

    def all(self):
        if self.kind == "produto":
            return list(self.db.produtos)
        return []

    def first(self):
        return None


class FakeSession:
    def __init__(self):
        self.produtos = [
            SimpleNamespace(
                id=14002,
                tenant_id="tenant-1",
                codigo="NTDRTR00026",
                nome="Traqueia",
                tipo_produto="SIMPLES",
            )
        ]
        self.added = []
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def query(self, *entities):
        name = getattr(entities[0], "__name__", "")
        if name == "Produto":
            return FakeQuery(self, "produto")
        if name == "ProdutoBlingSync":
            return FakeQuery(self, "sync")
        return FakeQuery(self, "subquery")

    def add(self, value):
        self.added.append(value)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


def test_auto_link_by_sku_marca_tentativa_sem_match_para_nao_travar_fila(monkeypatch):
    db = FakeSession()
    bling = FakeBling({"codigo": [], "sku": []})

    monkeypatch.setattr(bling_sync_auto_link, "SessionLocal", lambda: db)
    monkeypatch.setattr(bling_sync_auto_link, "BlingAPI", lambda: bling)

    resultado = BlingSyncService._auto_link_by_sku_for_tenant("tenant-1", limit=1)

    assert resultado["nao_encontrados"] == 1, resultado
    assert db.commits == 1
    assert db.added
    sync = db.added[0]
    assert sync.produto_id == 14002
    assert sync.tenant_id == "tenant-1"
    assert sync.bling_produto_id in (None, "")
    assert sync.sincronizar is False
    assert sync.status == "sem_vinculo"
