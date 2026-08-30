from __future__ import annotations

from types import SimpleNamespace

from app.produtos_models import ProdutoBlingSyncQueue
from app.services import bling_sync_reprocess
from app.services.bling_sync_reprocess import BlingSyncReprocessMixin


class FakeQuery:
    def join(self, *_args, **_kwargs):
        return self

    def filter(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def all(self):
        return []


class FakeSession:
    def query(self, *_args, **_kwargs):
        return FakeQuery()

    def commit(self):
        return None

    def rollback(self):
        return None

    def close(self):
        return None


class ServiceTeste(BlingSyncReprocessMixin):
    @classmethod
    def normalize_sync_states_from_latest_queue(cls, *_args, **_kwargs):
        return {"repaired_active": 0, "repaired_error": 0}


def test_preflight_de_reprocessamento_usa_escopo_de_catalogo(monkeypatch):
    chamadas = []

    class FakeBlingAPI:
        def listar_produtos(self, **kwargs):
            chamadas.append(("produtos", kwargs))
            return {"data": []}

        def listar_naturezas_operacoes(self):
            raise AssertionError("preflight de estoque nao deve exigir escopo fiscal")

    latest_ids = SimpleNamespace(
        c=SimpleNamespace(
            queue_id=ProdutoBlingSyncQueue.id,
            produto_id=ProdutoBlingSyncQueue.produto_id,
        )
    )
    monkeypatch.setattr(bling_sync_reprocess, "BlingAPI", FakeBlingAPI)
    monkeypatch.setattr(bling_sync_reprocess, "SessionLocal", FakeSession)
    monkeypatch.setattr(
        bling_sync_reprocess,
        "_latest_queue_ids_subquery",
        lambda *_args, **_kwargs: latest_ids,
    )

    resultado = ServiceTeste.reprocess_failed_syncs(limit=0)

    assert chamadas == [("produtos", {"limite": 1})]
    assert resultado["auth_invalid"] is False
