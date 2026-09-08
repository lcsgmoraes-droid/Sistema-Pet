"""Optional tests against an explicitly named, disposable local PostgreSQL 16."""

import importlib.util
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from types import SimpleNamespace
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.produto_identity_models import ProdutoSkuAlias
from app.produtos_models import Produto, ProdutoBlingSync, ProdutoBlingSyncQueue
from app.produtos_estoque_models import ProdutoBlingCostSyncQueue
from app.services.produto_alias_service import registrar_alias
from app.services.produto_alias_service import _lock_alias_namespace
from app.services.produto_merge_service import (
    executar_fusao_produtos,
    montar_preview_fusao_produtos,
)
from app.tenancy.context import set_current_tenant
from tests.unit.test_produto_alias_merge import case as _case_fixture
from tests.unit.test_produto_alias_merge import merge

case = _case_fixture

pytestmark = pytest.mark.skipif(
    not os.getenv("COREPET_MERGE_PG_URL"), reason="Requires disposable local PostgreSQL"
)


@pytest.mark.parametrize("commit", [False, True])
def test_stock_sale_and_bling_queue_share_transaction_without_self_deadlock(
    case, monkeypatch, commit
):
    from app.estoque.service import EstoqueService
    from app.services import bling_sync_queue

    opened = []

    def forbid_second_session():
        opened.append(True)
        raise AssertionError("Stock transaction must enqueue in its own session")

    monkeypatch.setattr(bling_sync_queue, "SessionLocal", forbid_second_session)
    result = EstoqueService.baixar_estoque(
        produto_id=case.primary.id,
        quantidade=1,
        motivo="venda",
        referencia_id=999,
        referencia_tipo="teste_fusao",
        user_id=1,
        db=case.db,
        tenant_id=case.tenant,
    )
    assert result["estoque_novo"] == 49
    assert not opened
    queued = case.db.query(ProdutoBlingSyncQueue).one()
    assert queued.estoque_novo == 49 and queued.status == "pendente"
    with Session(case.engine) as observer:
        assert observer.get(Produto, case.primary.id).estoque_atual == 50
        assert observer.query(ProdutoBlingSyncQueue).count() == 0
    if commit:
        case.db.commit()
    else:
        case.db.rollback()
    with Session(case.engine) as observer:
        assert observer.get(Produto, case.primary.id).estoque_atual == (
            49 if commit else 50
        )
        assert observer.query(ProdutoBlingSyncQueue).count() == int(commit)


def test_stock_queue_savepoint_failure_does_not_rollback_the_sale(case, monkeypatch):
    from app.estoque.service import EstoqueService
    from app.services.bling_sync_service import BlingSyncService

    def database_error(db, **kwargs):
        db.execute(text("SELECT 1 / 0"))

    monkeypatch.setattr(BlingSyncService, "queue_product_sync", database_error)
    result = EstoqueService.baixar_estoque(
        produto_id=case.primary.id,
        quantidade=1,
        motivo="venda",
        referencia_id=999,
        referencia_tipo="teste_fusao",
        user_id=1,
        db=case.db,
        tenant_id=case.tenant,
    )
    assert result["estoque_novo"] == 49 and case.db.is_active
    case.db.commit()
    with Session(case.engine) as observer:
        assert observer.get(Produto, case.primary.id).estoque_atual == 49
        assert observer.query(ProdutoBlingSyncQueue).count() == 0


@pytest.mark.parametrize(
    "operation", ["stock_worker", "cost_worker", "config", "reconcile"]
)
def test_retirement_refreshes_stale_objects_after_merge_lock(
    case, monkeypatch, operation
):
    from fastapi import HTTPException
    from app.bling_sync import config_routes, operational_routes
    from app.services import bling_sync_queue
    from app.services.bling_sync_service import BlingSyncService
    from app.services.bling_cost_sync_service import BlingCostSyncService

    queue = ProdutoBlingSyncQueue(
        tenant_id=case.tenant,
        produto_id=case.duplicate.id,
        sync_id=case.b.id,
        estoque_novo=2,
        status="falha_final",
        tentativas=1,
    )
    case.db.add(queue)
    cost_queue = ProdutoBlingCostSyncQueue(
        tenant_id=case.tenant,
        produto_id=case.duplicate.id,
        preco_custo_novo=1,
        status="falha_final",
    )
    case.db.add(cost_queue)
    case.db.commit()
    queue_id, cost_queue_id, duplicate_id = queue.id, cost_queue.id, case.duplicate.id
    attempted_api = []

    def forbid_api(*args, **kwargs):
        attempted_api.append(True)
        raise AssertionError("Retired origin must not call a remote API")

    for module in (config_routes, operational_routes, bling_sync_queue):
        monkeypatch.setattr(module, "BlingAPI", forbid_api)
    monkeypatch.setattr(BlingCostSyncService, "_send_cost", forbid_api)
    _lock_alias_namespace(case.db, case.tenant)
    case.db.query(Produto).filter(
        Produto.id.in_([case.primary.id, duplicate_id])
    ).order_by(Produto.id).with_for_update().all()
    waiting = Event()

    def query_started(conn, cursor, statement, parameters, context, many):
        if "FOR UPDATE" in statement and "produtos" in statement:
            waiting.set()

    event.listen(case.engine, "before_cursor_execute", query_started)

    def competing_operation():
        set_current_tenant(case.tenant)
        with Session(case.engine) as db:
            # These ORM instances intentionally represent the pre-merge state.
            stale_product = db.get(Produto, duplicate_id)
            stale_sync = (
                db.query(ProdutoBlingSync).filter_by(produto_id=duplicate_id).one()
            )
            assert stale_product.deleted_at is None and stale_sync.sincronizar
            try:
                if operation == "cost_worker":
                    result = BlingCostSyncService.process_queue_item(
                        db, db.get(ProdutoBlingCostSyncQueue, cost_queue_id)
                    )
                    db.commit()
                    return result["ok"]
                if operation == "stock_worker":
                    result = BlingSyncService.process_queue_item(
                        db, db.get(ProdutoBlingSyncQueue, queue_id)
                    )
                    db.commit()
                    return result["ok"]
                if operation == "config":
                    config_routes.configurar_sincronizacao(
                        SimpleNamespace(
                            produto_id=duplicate_id,
                            bling_produto_id="NEW-REMOTE",
                            sincronizar=True,
                            estoque_compartilhado=True,
                        ),
                        db,
                        (SimpleNamespace(id=1), case.tenant),
                    )
                else:
                    operational_routes.reconciliar_estoque(
                        duplicate_id,
                        origem="bling",
                        valor_manual=None,
                        db=db,
                        user_and_tenant=(SimpleNamespace(id=1), case.tenant),
                    )
            except HTTPException as exc:
                return exc.status_code

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(competing_operation)
        assert waiting.wait(3)
        assert not future.done()
        merge(case)
        assert future.result(timeout=5) == (
            False if operation.endswith("worker") else 409
        )
    event.remove(case.engine, "before_cursor_execute", query_started)
    case.db.expire_all()
    assert not attempted_api
    assert case.b.bling_produto_id == "BLING-B"
    assert case.b.retirado_para_produto_id == case.primary.id
    assert case.primary.estoque_atual == 50 and case.duplicate.estoque_atual == 0


def test_product_lock_serializes_stock_change_and_rejects_old_preview(case):
    args = dict(
        tenant_id=case.tenant,
        principal_id=case.primary.id,
        duplicado_id=case.duplicate.id,
        estrategia_estoque="manter_principal",
    )
    preview = montar_preview_fusao_produtos(case.db, **args)
    case.db.query(Produto).filter(Produto.id == case.primary.id).with_for_update().all()
    waiting = Event()

    def query_started(conn, cursor, statement, parameters, context, many):
        if "FOR UPDATE" in statement and "produtos" in statement:
            waiting.set()

    event.listen(case.engine, "before_cursor_execute", query_started)

    def run_merge():
        set_current_tenant(case.tenant)
        with Session(case.engine) as db:
            try:
                executar_fusao_produtos(
                    db,
                    **args,
                    decisoes_campos={},
                    user_id=1,
                    observacao="Saldo confirmado em cinquenta unidades.",
                    preview_token=preview["preview_token"],
                    preservar_vinculo_bling_duplicado=True,
                )
            except ValueError as exc:
                return str(exc)

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(run_merge)
        assert waiting.wait(3)
        assert not future.done()
        case.primary.estoque_atual = 49
        case.db.commit()
        assert "alterado" in future.result(timeout=5)
    event.remove(case.engine, "before_cursor_execute", query_started)
    assert case.duplicate.deleted_at is None and case.primary.estoque_atual == 49
    assert case.db.query(ProdutoSkuAlias).count() == 0


@pytest.mark.parametrize("by_item", [False, True])
def test_autocreate_never_waits_for_namespace_while_invoice_holds_product_lock(
    case, monkeypatch, by_item
):
    from app.services.bling_nf import autocadastro

    remote = {
        "id": "UNREGISTERED",
        "codigo": "MISSING-SKU",
        "nome": "Synthetic product",
    }
    monkeypatch.setattr(autocadastro, "_buscar_produto_bling_por_sku", lambda _: remote)
    _lock_alias_namespace(case.db, case.tenant)

    def process_invoice_item():
        set_current_tenant(case.tenant)
        with Session(case.engine) as db:
            db.query(Produto).filter(
                Produto.id == case.primary.id
            ).with_for_update().all()
            try:
                if by_item:
                    autocadastro.criar_produto_automatico_do_bling_por_item(
                        db, case.tenant, remote
                    )
                else:
                    autocadastro.criar_produto_automatico_do_bling(
                        db, case.tenant, "MISSING-SKU"
                    )
            except ValueError as exc:
                return str(exc)

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(process_invoice_item)
        try:
            assert "repetir o autocadastro" in future.result(timeout=3)
        finally:
            case.db.rollback()
    assert case.db.query(Produto).count() == 2


@pytest.mark.parametrize("operation", ["alias", "create_sku"])
def test_alias_namespace_serializes_conflicting_concurrent_registration(
    case, operation
):
    registrar_alias(
        case.db,
        tenant_id=case.tenant,
        produto_id=case.primary.id,
        sku="COLLISION",
        user_id=1,
        motivo="Confirmed identity",
    )
    waiting = Event()

    def query_started(conn, cursor, statement, parameters, context, many):
        if "pg_advisory_xact_lock" in statement:
            waiting.set()

    event.listen(case.engine, "before_cursor_execute", query_started)

    def competing_alias():
        set_current_tenant(case.tenant)
        with Session(case.engine) as db:
            try:
                if operation == "create_sku":
                    from app.produtos.validators import _validar_sku_unico
                    from fastapi import HTTPException

                    try:
                        _validar_sku_unico(db, "COLLISION", case.tenant)
                    except HTTPException as exc:
                        return exc.detail
                registrar_alias(
                    db,
                    tenant_id=case.tenant,
                    produto_id=case.duplicate.id,
                    sku="collision",
                    user_id=1,
                    motivo="Different mapping",
                )
                db.commit()
            except ValueError as exc:
                return str(exc)

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(competing_alias)
        assert waiting.wait(3)
        assert not future.done()
        case.db.commit()
        assert "outro produto" in future.result(timeout=5)
    event.remove(case.engine, "before_cursor_execute", query_started)
    assert case.db.query(ProdutoSkuAlias).count() == 1


def test_migration_upgrade_rls_uniqueness_and_downgrade():
    url = make_url(os.environ["COREPET_MERGE_PG_URL"])
    assert (url.host, url.port, url.database) == (
        "127.0.0.1",
        55487,
        "corepet_merge_test",
    )
    engine = create_engine(url)
    migration_path = (
        Path(__file__).parents[2]
        / "alembic/versions/zzk20260907a1_produto_sku_alias_fusao.py"
    )
    spec = importlib.util.spec_from_file_location("alias_migration", migration_path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    a, b = str(uuid4()), str(uuid4())
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.execute(
            text(
                "CREATE TABLE produtos(id integer PRIMARY KEY,tenant_id uuid NOT NULL)"
            )
        )
        conn.execute(text("CREATE TABLE users(id integer PRIMARY KEY)"))
        conn.execute(
            text(
                "CREATE TABLE produto_bling_sync(id integer PRIMARY KEY,produto_id integer REFERENCES produtos(id))"
            )
        )
        with Operations.context(MigrationContext.configure(conn)):
            migration.upgrade()
        conn.execute(
            text(
                "INSERT INTO produtos VALUES (1,CAST(:a AS uuid)),(2,CAST(:b AS uuid))"
            ),
            {"a": a, "b": b},
        )
        conn.execute(text("INSERT INTO users VALUES (1)"))
        conn.execute(
            text(
                "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='corepet_merge_limited') THEN CREATE ROLE corepet_merge_limited NOLOGIN; END IF; END $$"
            )
        )
        conn.execute(text("GRANT USAGE ON SCHEMA public TO corepet_merge_limited"))
        conn.execute(text("GRANT SELECT ON produtos,users TO corepet_merge_limited"))
        conn.execute(
            text(
                "GRANT SELECT,INSERT ON produto_sku_aliases,produto_fusao_logs TO corepet_merge_limited"
            )
        )
        conn.execute(
            text(
                "GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA public TO corepet_merge_limited"
            )
        )
    insert = text(
        "INSERT INTO produto_sku_aliases(tenant_id,produto_id,sku,sku_normalizado,origem,motivo,user_id) VALUES(CAST(:tenant AS uuid),:product,'OLD','old','manual','Confirmed identity',1)"
    )
    with engine.begin() as conn:
        conn.execute(text("SET LOCAL ROLE corepet_merge_limited"))
        conn.execute(text("SELECT set_config('app.tenant_id',:a,true)"), {"a": a})
        conn.execute(insert, {"tenant": a, "product": 1})
        for params, sqlstate in (
            ({"tenant": a, "product": 2}, "42501"),
            ({"tenant": b, "product": 2}, "42501"),
            ({"tenant": a, "product": 1}, "23505"),
        ):
            with pytest.raises(DBAPIError) as error:
                with conn.begin_nested():
                    conn.execute(insert, params)
            assert error.value.orig.pgcode == sqlstate
        conn.execute(text("SELECT set_config('app.tenant_id',:b,true)"), {"b": b})
        assert (
            conn.execute(text("SELECT count(*) FROM produto_sku_aliases")).scalar() == 0
        )
        conn.execute(insert, {"tenant": b, "product": 2})
        assert (
            conn.execute(text("SELECT count(*) FROM produto_sku_aliases")).scalar() == 1
        )
    with engine.begin() as conn:
        with Operations.context(MigrationContext.configure(conn)):
            migration.downgrade()
        assert (
            conn.execute(text("SELECT to_regclass('produto_sku_aliases')")).scalar()
            is None
        )
        assert (
            conn.execute(
                text(
                    "SELECT count(*) FROM information_schema.columns WHERE table_name='produto_bling_sync' AND column_name='retirado_para_produto_id'"
                )
            ).scalar()
            == 0
        )
        with Operations.context(MigrationContext.configure(conn)):
            migration.upgrade()
    engine.dispose()
