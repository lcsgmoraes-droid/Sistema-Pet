from datetime import datetime
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException

from app.bling_sync import catalog_snapshots, config_routes, dashboard_routes
from app.bling_sync import operational_routes, routes_common
from app.produtos_models import Produto, ProdutoBlingSync, ProdutoBlingSyncQueue
from app.services import bling_sync_auto_link, bling_sync_queue, bling_sync_reprocess
from app.services import bling_sync_reconciliation
from app.services.bling_sync_service import BlingSyncService

TENANT = UUID("11111111-1111-4111-8111-111111111111")
OLD_ID = "16666308078"
ACTIVE_ID = "16430748715"


class Query:
    def __init__(self, value, db):
        self.value = value
        self.db = db

    def filter(self, *args):
        return self

    def outerjoin(self, *args):
        return self

    join = outerjoin
    order_by = filter
    limit = filter

    def populate_existing(self):
        self.db.refreshes += 1
        return self

    def with_for_update(self, **kwargs):
        self.db.locks.append(kwargs["of"])
        if self.db.on_lock:
            self.db.on_lock(kwargs["of"])
        return self

    def first(self):
        return self.value

    def all(self):
        return self.value

    def subquery(self):
        return SimpleNamespace()


class Db:
    def __init__(self, *values):
        self.values = list(values)
        self.added = []
        self.commits = 0
        self.refreshes = 0
        self.locks = []
        self.on_lock = None

    def query(self, *args):
        assert self.values, "Consulta inesperada depois da guarda"
        return Query(self.values.pop(0), self)

    def add(self, value):
        self.added.append(value)

    def commit(self):
        self.commits += 1

    def rollback(self):
        pass

    def refresh(self, value):
        pass

    def close(self):
        pass


def product(*, archived=False):
    return SimpleNamespace(
        id=4752,
        tenant_id=TENANT,
        codigo="5613",
        codigo_barras="7898396116978",
        nome="Tapete Mr Dry",
        tipo_produto="SIMPLES",
        estoque_atual=50,
        preco_custo=30,
        preco_venda=55,
        deleted_at=datetime(2026, 9, 7) if archived else None,
    )


def sync(*, retired=False, bling_id=ACTIVE_ID):
    # A guarda precisa vencer ate uma reativacao acidental do status/booleano.
    return SimpleNamespace(
        id=100,
        produto_id=4752,
        tenant_id=TENANT,
        bling_produto_id=bling_id,
        retirado_para_produto_id=4752 if retired else None,
        sincronizar=True,
        estoque_compartilhado=True,
        status="ativo",
    )


def forbid_api():
    raise AssertionError("Origem retirada nao deve chamar API externa")


def test_upsert_rejects_retired_id_without_changing_canonical():
    canonical = product()
    current = sync()
    db = Db(canonical, current, None, [(OLD_ID,)], [])
    with pytest.raises(HTTPException) as exc:
        routes_common._upsert_sync_vinculo(db, TENANT, canonical, OLD_ID)
    assert exc.value.status_code == 409
    assert current.bling_produto_id == ACTIVE_ID
    assert canonical.estoque_atual == 50
    assert not db.added


def test_upsert_reloads_product_archived_after_initial_read():
    stale_product = product()
    db = Db(product(archived=True), sync())
    with pytest.raises(HTTPException) as exc:
        routes_common._upsert_sync_vinculo(db, TENANT, stale_product, OLD_ID)
    assert exc.value.status_code == 409
    assert db.locks == [Produto, ProdutoBlingSync]
    assert db.refreshes == 2


def test_upsert_keeps_active_origin_available():
    canonical = product()
    current = sync()
    db = Db(canonical, current, None, [], [])
    routes_common._upsert_sync_vinculo(db, TENANT, canonical, ACTIVE_ID)
    assert current.bling_produto_id == ACTIVE_ID
    assert current.sincronizar is True


@pytest.mark.parametrize("entry", ["upsert", "config", "reconcile"])
def test_mutations_reload_retirement_under_product_then_sync_lock(monkeypatch, entry):
    canonical = product()
    current = sync(bling_id=OLD_ID)
    db = Db(canonical, current)

    def complete_merge_before_lock_returns(model):
        if model is ProdutoBlingSync:
            assert db.locks == [Produto, ProdutoBlingSync]
            assert db.refreshes == 2
            current.retirado_para_produto_id = 4752

    db.on_lock = complete_merge_before_lock_returns
    monkeypatch.setattr(config_routes, "BlingAPI", forbid_api)
    monkeypatch.setattr(operational_routes, "BlingAPI", forbid_api)
    with pytest.raises(HTTPException) as exc:
        if entry == "upsert":
            routes_common._upsert_sync_vinculo(db, TENANT, canonical, OLD_ID)
        elif entry == "config":
            config_routes.configurar_sincronizacao(
                SimpleNamespace(
                    produto_id=4752,
                    bling_produto_id=None,
                    sincronizar=True,
                    estoque_compartilhado=True,
                ),
                db,
                (SimpleNamespace(id=1), TENANT),
            )
        else:
            operational_routes.reconciliar_estoque(
                4752,
                origem="bling",
                valor_manual=None,
                db=db,
                user_and_tenant=(SimpleNamespace(id=1), TENANT),
            )
    assert exc.value.status_code == 409
    assert canonical.estoque_atual == 50
    assert current.bling_produto_id == OLD_ID
    assert not db.commits
    assert not db.added


def test_system_reconciliation_service_blocks_retired_origin_before_remote_get(
    monkeypatch,
):
    db = Db(product(), sync(retired=True, bling_id=OLD_ID))
    monkeypatch.setattr(bling_sync_reconciliation, "SessionLocal", lambda: db)
    monkeypatch.setattr(bling_sync_reconciliation, "BlingAPI", forbid_api)
    result = BlingSyncService.reconcile_product(4752, force_sync=True)
    assert result["ok"] is False
    assert db.locks == [Produto, ProdutoBlingSync]
    assert db.refreshes == 2
    assert not db.commits


@pytest.mark.parametrize("automatic", [False, True])
def test_config_cannot_reactivate_retired_id(monkeypatch, automatic):
    canonical = product()
    current = sync()
    db = Db(canonical, current, [(OLD_ID,)], [])
    candidate_api = SimpleNamespace(
        listar_produtos=lambda **_: {"data": [{"id": OLD_ID}]}
    )
    monkeypatch.setattr(config_routes, "BlingAPI", lambda: candidate_api)
    config = SimpleNamespace(
        produto_id=4752,
        bling_produto_id=None if automatic else OLD_ID,
        sincronizar=True,
        estoque_compartilhado=True,
    )
    with pytest.raises(HTTPException) as exc:
        config_routes.configurar_sincronizacao(
            config, db, (SimpleNamespace(id=1), TENANT)
        )
    assert exc.value.status_code == 409
    assert current.bling_produto_id == ACTIVE_ID
    assert current.status == "ativo"
    assert db.commits == 0
    assert db.locks == [Produto, ProdutoBlingSync]
    assert db.refreshes == 2


@pytest.mark.parametrize("retired_marker", [False, True])
def test_retired_bling_balance_cannot_overwrite_canonical_50(
    monkeypatch, retired_marker
):
    canonical = product()
    current = sync(retired=retired_marker, bling_id=OLD_ID)
    values = [canonical, current] + ([] if retired_marker else [[(OLD_ID,)], []])
    db = Db(*values)
    monkeypatch.setattr(operational_routes, "BlingAPI", forbid_api)
    with pytest.raises(HTTPException) as exc:
        operational_routes.reconciliar_estoque(
            4752,
            origem="bling",
            valor_manual=None,
            db=db,
            user_and_tenant=(SimpleNamespace(id=1), TENANT),
        )
    assert exc.value.status_code == 409
    assert (canonical.estoque_atual, canonical.preco_custo, canonical.preco_venda) == (
        50,
        30,
        55,
    )
    assert db.commits == 0
    assert db.locks == [Produto, ProdutoBlingSync]
    assert db.refreshes == 2


def test_dashboard_rejects_retired_snapshot_before_fetch_or_autocreate(monkeypatch):
    monkeypatch.setattr(dashboard_routes, "BlingAPI", forbid_api)
    with pytest.raises(HTTPException) as exc:
        dashboard_routes.criar_produto_local_para_faltante_bling(
            SimpleNamespace(bling_id=OLD_ID),
            Db([(OLD_ID,)], []),
            (SimpleNamespace(id=1), TENANT),
        )
    assert exc.value.status_code == 409


def test_auto_link_cannot_assign_retired_id(monkeypatch):
    canonical = product()
    current = sync(bling_id=None)
    db = Db([canonical], canonical, current, [(OLD_ID,)], [])
    monkeypatch.setattr(bling_sync_auto_link, "SessionLocal", lambda: db)
    monkeypatch.setattr(bling_sync_auto_link, "BlingAPI", lambda: object())
    monkeypatch.setattr(
        bling_sync_auto_link,
        "_buscar_item_bling_para_produto",
        lambda *args, **kwargs: {"id": OLD_ID, "codigo": "5613"},
    )
    result = BlingSyncService._auto_link_by_sku_for_tenant(TENANT, 1)
    assert result["vinculados"] == 0
    assert result["erros"] == 1
    assert current.bling_produto_id is None
    assert db.locks == [Produto, ProdutoBlingSync]
    assert db.refreshes == 2


@pytest.mark.parametrize("retired", [False, True])
def test_auto_link_reloads_origin_and_never_replaces_link_created_during_get(retired):
    stale_product = product()
    current = sync(retired=retired, bling_id=OLD_ID if retired else ACTIVE_ID)
    db = Db(product(archived=retired), current)
    with pytest.raises(ValueError):
        BlingSyncService._get_or_create_sync(db, stale_product)
    assert current.bling_produto_id == (OLD_ID if retired else ACTIVE_ID)
    assert db.locks == [Produto, ProdutoBlingSync]
    assert db.refreshes == 2
    assert not db.added


@pytest.mark.parametrize("queue_status", ["pendente", "sucesso", "falha_final"])
def test_worker_never_publishes_retired_origin_even_if_reenabled(
    monkeypatch, queue_status
):
    canonical = product()
    current = sync(retired=True, bling_id=OLD_ID)
    row = SimpleNamespace(
        id=1, sync_id=100, produto_id=4752, estoque_novo=2, status=queue_status
    )
    monkeypatch.setattr(bling_sync_queue, "BlingAPI", forbid_api)
    db = Db(canonical, current)
    result = BlingSyncService.process_queue_item(db, row)
    assert result["ok"] is False
    assert row.status == (
        "cancelado_fusao" if queue_status == "pendente" else queue_status
    )
    assert current.status == "ativo"
    assert canonical.estoque_atual == 50
    assert db.locks == [Produto, ProdutoBlingSync]
    assert db.refreshes == 2
    assert db.commits == 0


def test_queue_creation_rejects_retired_origin():
    db = Db(product(), sync(retired=True, bling_id=OLD_ID))
    result = BlingSyncService.queue_product_sync(
        db, produto_id=4752, estoque_novo=2, motivo="teste"
    )
    assert result["ok"] is False
    assert not db.added
    assert db.locks == [Produto, ProdutoBlingSync]
    assert db.refreshes == 2


def latest_query_stub():
    return SimpleNamespace(
        c=SimpleNamespace(
            queue_id=ProdutoBlingSyncQueue.id,
            produto_id=ProdutoBlingSyncQueue.produto_id,
        )
    )


@pytest.mark.parametrize("last_status", ["sucesso", "erro", "falha_final"])
def test_normalizer_preserves_retirement_marker_and_status(monkeypatch, last_status):
    current = sync(retired=True)
    current.status = "retirado_fusao"
    row = SimpleNamespace(status=last_status)
    monkeypatch.setattr(
        bling_sync_queue,
        "_latest_queue_ids_subquery",
        lambda *a, **k: latest_query_stub(),
    )
    result = BlingSyncService.normalize_sync_states_from_latest_queue(
        Db([(current, row)]), TENANT
    )
    assert result == {"repaired_active": 0, "repaired_error": 0}
    assert current.status == "retirado_fusao"


def test_reprocess_does_not_reopen_historical_retired_failure(monkeypatch):
    current = sync(retired=True)
    current.status = "retirado_fusao"
    row = SimpleNamespace(id=1, sync_id=100, produto_id=4752, status="falha_final")
    db = Db([row], current, [])
    monkeypatch.setattr(bling_sync_reprocess, "SessionLocal", lambda: db)
    monkeypatch.setattr(
        bling_sync_reprocess,
        "BlingAPI",
        lambda: SimpleNamespace(listar_produtos=lambda **k: {}),
    )
    monkeypatch.setattr(
        bling_sync_reprocess,
        "_latest_queue_ids_subquery",
        lambda *a, **k: latest_query_stub(),
    )

    class Service(BlingSyncService):
        @classmethod
        def normalize_sync_states_from_latest_queue(cls, *args, **kwargs):
            return {"repaired_active": 0, "repaired_error": 0}

    result = Service.reprocess_failed_syncs(1, TENANT)
    assert result["reprocessados"] == 0
    assert row.status == "falha_final"
    assert current.status == "retirado_fusao"


@pytest.mark.parametrize(
    "key,getter,base",
    [
        ("id", "_get_snapshot_faltantes_bling", "_get_snapshot_faltantes_bling_base"),
        (
            "bling_id",
            "_get_snapshot_sem_vinculo_com_match_bling",
            "_get_snapshot_sem_vinculo_com_match_bling_base",
        ),
    ],
)
def test_cached_snapshot_filters_retired_ids_per_tenant(monkeypatch, key, getter, base):
    payload = {"items": [{key: OLD_ID, "estoque": 2}, {key: ACTIVE_ID}], "total": 2}
    monkeypatch.setattr(catalog_snapshots, base, lambda *args: payload)
    monkeypatch.setattr(
        catalog_snapshots,
        "ids_bling_retirados",
        lambda db, tenant: {OLD_ID} if tenant == TENANT else set(),
    )
    result = getattr(catalog_snapshots, getter)(object(), TENANT)
    assert result["items"] == [{key: ACTIVE_ID}]
    assert result["total"] == 1
    assert len(payload["items"]) == 2
    assert getattr(catalog_snapshots, getter)(object(), "other-tenant")["total"] == 2


def test_catalog_missing_snapshot_cannot_offer_retired_product():
    db = Db([(OLD_ID,)], [], [])
    result = catalog_snapshots._calcular_snapshot_faltantes_bling(
        db,
        TENANT,
        [{"id": OLD_ID, "codigo": "PCTPMD00003", "saldoFisicoTotal": 2}],
        True,
    )
    assert result["items"] == []
    assert result["total_bling"] == 0
