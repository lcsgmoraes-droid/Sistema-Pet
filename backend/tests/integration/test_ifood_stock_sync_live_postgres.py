"""Modo LIVE com PostgreSQL descartavel, RLS real e provedor sem rede.

Nenhum tenant, credencial ou dado de producao e usado. Somente a impressao
digital do tenant e substituida; produto, SKU, EAN e merchant seguem o escopo
fixo do piloto. O transporte real nunca e instanciado.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from hashlib import sha256
import re
from threading import Event
from uuid import uuid4

from alembic.migration import MigrationContext
from alembic.operations import Operations
import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from tests.integration.test_ifood_pdv_pilot_postgres import pg_engine  # noqa: F401
from tests.integration.test_ifood_stock_sync_postgres import (
    BARCODE,
    START,
    _assert_protected,
    _live_migration,
    _restricted_engine,
    _snapshot,
    _stock,
    _tick,
    stock_pg_engine,  # noqa: F401
    stock_pilot,  # noqa: F401
)


def _guard_local_schema(conn):
    assert (
        conn.exec_driver_sql("SELECT current_database()").scalar_one()
        == "ifood_pdv_test"
    )
    assert re.fullmatch(
        r"ifood_pdv_[a-f0-9]{32}",
        conn.exec_driver_sql("SELECT current_schema()").scalar_one(),
    )


def _rows(conn, table):
    assert table in {"ifood_stock_sync_states", "ifood_catalog_submissions"}
    return {
        row["id"]: dict(row)
        for row in conn.exec_driver_sql(f"SELECT * FROM {table} ORDER BY id").mappings()
    }


def _foreign_evidence(c):
    from app.ifood_catalog_models import (
        IfoodCatalogLink,
        IfoodCatalogSubmission,
        IfoodStockSyncState,
    )
    from app.tenancy.context import tenant_context

    with tenant_context(c.other_tenant), Session(c.engine) as db:
        link = db.get(IfoodCatalogLink, c.other_link_id)
        db.add(
            IfoodStockSyncState(
                tenant_id=c.other_tenant,
                merchant_id=link.merchant_id,
                link_id=link.id,
                link_revision=1,
                desired_stock=41,
                last_accepted_stock=41,
                status="accepted",
                failure_count=0,
                provider_mode="local_simulator",
            )
        )
        db.add(
            IfoodCatalogSubmission(
                tenant_id=c.other_tenant,
                link_id=link.id,
                merchant_id=link.merchant_id,
                barcode=BARCODE,
                request_key=str(uuid4()),
                operation="update",
                source="auto_stock",
                provider_mode="local_simulator",
                fields=["stock"],
                payload_hash="0" * 64,
                evidence={"stock": 41},
                status="accepted",
                actor_id=link.portal_checked_by,
                http_status=202,
            )
        )
        db.commit()


def test_real_mode_migration_preserves_manual_dev_and_foreign_history(stock_pilot):  # noqa: F811
    c = stock_pilot
    assert _tick(c)["status"] == "unchanged"
    _stock(c, 20)
    assert _tick(c, 36)["status"] == "accepted"
    _foreign_evidence(c)
    with c.engine.begin() as conn:
        _guard_local_schema(conn)
        before_submissions = _rows(conn, "ifood_catalog_submissions")
        before_states = _rows(conn, "ifood_stock_sync_states")
        # Reproduz exatamente o schema v: source existia, provider_mode nao.
        for table, constraint in (
            ("ifood_catalog_submissions", "ck_ifood_catalog_submission_provider_mode"),
            ("ifood_stock_sync_states", "ck_ifood_stock_sync_provider_mode"),
        ):
            conn.exec_driver_sql(f"ALTER TABLE {table} DROP CONSTRAINT {constraint}")
            conn.exec_driver_sql(f"ALTER TABLE {table} DROP COLUMN provider_mode")
        with Operations.context(MigrationContext.configure(conn)):
            _live_migration()["upgrade"]()
        after_submissions = _rows(conn, "ifood_catalog_submissions")
        after_states = _rows(conn, "ifood_stock_sync_states")
        assert after_submissions.keys() == before_submissions.keys()
        assert after_states.keys() == before_states.keys()
        assert {row["source"] for row in before_submissions.values()} == {
            "manual",
            "auto_stock",
        }
        for row_id, row in after_submissions.items():
            assert row.pop("provider_mode") == (
                "local_simulator" if row["source"] == "auto_stock" else "ifood_api"
            )
            before_submissions[row_id].pop("provider_mode")
            assert row == before_submissions[row_id]
        for row_id, row in after_states.items():
            assert row.pop("provider_mode") == "local_simulator"
            before_states[row_id].pop("provider_mode")
            assert row == before_states[row_id]

    with _restricted_engine(c) as restricted, restricted.connect() as conn:
        conn.execute(
            text("SELECT set_config('app.tenant_id',:tenant,true)"),
            {"tenant": str(c.tenant_id)},
        )
        for table in ("ifood_stock_sync_states", "ifood_catalog_submissions"):
            enabled, forced = conn.exec_driver_sql(
                f"SELECT relrowsecurity,relforcerowsecurity FROM pg_class WHERE oid='{table}'::regclass"
            ).one()
            assert enabled and forced
            assert (
                conn.execute(
                    text(f"SELECT count(*) FROM {table} WHERE tenant_id=:tenant"),
                    {"tenant": c.other_tenant},
                ).scalar_one()
                == 0
            )
            assert (
                conn.execute(
                    text(
                        f"UPDATE {table} SET provider_mode='ifood_api' WHERE tenant_id=:tenant"
                    ),
                    {"tenant": c.other_tenant},
                ).rowcount
                == 0
            )
            with pytest.raises(IntegrityError), conn.begin_nested():
                conn.execute(
                    text(
                        f"UPDATE {table} SET provider_mode='unknown' WHERE tenant_id=:tenant"
                    ),
                    {"tenant": c.tenant_id},
                )
    _assert_protected(c)


@pytest.mark.parametrize(
    "live_table", ["ifood_stock_sync_states", "ifood_catalog_submissions"]
)
def test_mode_downgrade_refuses_to_erase_real_attempt_or_state(stock_pilot, live_table):  # noqa: F811
    c = stock_pilot
    assert _tick(c)["status"] == "unchanged"
    _stock(c, 20)
    assert _tick(c, 36)["status"] == "accepted"
    with c.engine.begin() as conn:
        _guard_local_schema(conn)
        conn.execute(
            text(
                f"UPDATE {live_table} SET provider_mode='ifood_api' WHERE tenant_id=:tenant"
            ),
            {"tenant": c.tenant_id},
        )
        with (
            Operations.context(MigrationContext.configure(conn)),
            pytest.raises(RuntimeError, match="historico real"),
        ):
            _live_migration()["downgrade"]()
        assert "provider_mode" in {
            column["name"] for column in inspect(conn).get_columns(live_table)
        }
        assert (
            conn.execute(
                text(f"SELECT provider_mode FROM {live_table} WHERE tenant_id=:tenant"),
                {"tenant": c.tenant_id},
            ).scalar_one()
            == "ifood_api"
        )


def test_live_stock_sale_cancel_replenishment_concurrency_and_rls(
    stock_pilot,
    monkeypatch,  # noqa: F811
):
    from app.config import settings
    from app.estoque_entrada_manual_routes import EntradaEstoqueRequest, entrada_estoque
    from app.ifood_catalog_models import (
        IfoodCatalogConfirmation,
        IfoodCatalogSubmission,
        IfoodStockSyncState,
    )
    from app.integrations.ifood import stock_sync as sync
    from app.models import User
    from app.tenancy.context import tenant_context
    from app.vendas.service import VendaService

    c = stock_pilot
    # O ORM descarta IDs externos na insercao. Somente no schema descartavel,
    # move o produto efemero para o ID fixo antes de criar qualquer tentativa.
    with c.engine.begin() as conn:
        _guard_local_schema(conn)
        conn.execute(
            text(
                "UPDATE produtos SET id=:fixed WHERE id=:original AND tenant_id=:tenant"
            ),
            {
                "fixed": sync.LIVE_PRODUCT_ID,
                "original": c.product_id,
                "tenant": c.tenant_id,
            },
        )
        conn.execute(
            text(
                "UPDATE ifood_catalog_links SET product_id=:product,merchant_id=:merchant WHERE id=:link AND tenant_id=:tenant"
            ),
            {
                "product": sync.LIVE_PRODUCT_ID,
                "merchant": sync.LIVE_MERCHANT_ID,
                "link": c.link_id,
                "tenant": c.tenant_id,
            },
        )
        conn.execute(
            text(
                "UPDATE ifood_merchant_configs SET merchant_id=:merchant WHERE tenant_id=:tenant"
            ),
            {"merchant": sync.LIVE_MERCHANT_ID, "tenant": c.tenant_id},
        )
    c.product_id = sync.LIVE_PRODUCT_ID
    c.merchant_id = sync.LIVE_MERCHANT_ID
    c.before = _snapshot(c)
    for name in ("APP_ENV", "ENV", "ENVIRONMENT"):
        monkeypatch.setenv(name, "production")
    monkeypatch.setattr(
        sync, "LIVE_TENANT_SHA256", sha256(str(c.tenant_id).encode()).hexdigest()
    )
    for name, value in {
        "ENVIRONMENT": "production",
        "IFOOD_STOCK_SYNC_LIVE_ENABLED": True,
        "IFOOD_STOCK_SYNC_DEV_ENABLED": False,
        "IFOOD_STOCK_SYNC_PRODUCT_ID": c.product_id,
        "IFOOD_STOCK_SYNC_MERCHANT_ID": c.merchant_id,
        "IFOOD_API_BASE_URL": "https://merchant-api.ifood.com.br",
    }.items():
        monkeypatch.setattr(settings, name, value)
    monkeypatch.setattr(
        sync,
        "_client",
        lambda **kwargs: pytest.fail("No real transport in PostgreSQL tests"),
    )

    with _restricted_engine(c) as restricted:

        def tick(minutes):
            return sync.poll_ifood_stock_once(
                client_factory=c.provider.factory,
                session_factory=lambda: Session(restricted),
                now=START + timedelta(minutes=minutes),
            )

        assert tick(0)["status"] == "unchanged"
        with tenant_context(c.tenant_id), Session(c.engine) as db:
            count = db.query(IfoodCatalogConfirmation).count()
            sale = VendaService.criar_venda(
                {
                    "tenant_id": c.tenant_id,
                    "canal": "loja_fisica",
                    "caixa_id": c.caixa_id,
                    "itens": [
                        {
                            "produto_id": c.product_id,
                            "tipo": "produto",
                            "quantidade": 1,
                            "preco_unitario": 142.9,
                            "subtotal": 142.9,
                        }
                    ],
                },
                c.user_id,
                db,
            )
            VendaService.finalizar_venda(
                sale["id"],
                [{"forma_pagamento": "Dinheiro", "valor": 142.9}],
                c.user_id,
                "PG LIVE fake",
                c.tenant_id,
                db,
                caixa_id=c.caixa_id,
            )
        c.provider.entered, c.provider.release = Event(), Event()
        with ThreadPoolExecutor(max_workers=2) as pool:
            sending = pool.submit(tick, 36)
            assert c.provider.entered.wait(timeout=15)
            duplicate = pool.submit(tick, 36)
            try:
                assert duplicate.result(timeout=10)["status"] in {
                    "busy",
                    "uncertain",
                    "cooldown",
                }
            finally:
                c.provider.release.set()
            assert sending.result(timeout=15)["sent_stock"] == 20
        assert len(c.provider.calls) == 1
        with tenant_context(c.tenant_id), Session(c.engine) as db:
            VendaService.cancelar_venda(
                sale["id"], "Teste PG LIVE sem rede", c.user_id, c.tenant_id, db
            )
        assert tick(37)["status"] == "cooldown"
        assert tick(72)["sent_stock"] == 21
        with tenant_context(c.tenant_id), Session(c.engine) as db:
            entrada_estoque(
                EntradaEstoqueRequest(
                    produto_id=c.product_id,
                    quantidade=2,
                    motivo="ajuste",
                    custo_unitario=None,
                ),
                db=db,
                user_and_tenant=(db.get(User, c.user_id), c.tenant_id),
            )
        assert tick(108)["sent_stock"] == 23
        assert tick(144)["status"] == "unchanged"
    with tenant_context(c.tenant_id), Session(c.engine) as db:
        state = db.query(IfoodStockSyncState).one()
        assert state.provider_mode == "ifood_api" and state.last_accepted_stock == 23
        submissions = db.query(IfoodCatalogSubmission).all()
        assert len(submissions) == 3
        assert all(
            row.provider_mode == "ifood_api"
            and row.source == "auto_stock"
            and row.http_status == 202
            for row in submissions
        )
        assert db.query(IfoodCatalogConfirmation).count() == count
        view = sync.stock_sync_view(db, c.tenant_id, c.merchant_id, c.product_id)
        assert view["environment"] == "production" and not view["external_confirmed"]
    _assert_protected(c)
