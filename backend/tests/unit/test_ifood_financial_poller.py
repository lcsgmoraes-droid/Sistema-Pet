"""Worker DEV com provedor mockado; nenhuma rede ou massa oficial forjada."""

from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, insert, select
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateTable

from app import caixa_models, financeiro_models  # noqa: F401 - tipos das FKs legadas
from app.config import Settings, settings
from app.ifood_financial_cost_models import IfoodFinancialSaleLink
from app.ifood_financial_models import (
    IfoodFinancialEvent,
    IfoodFinancialOrderCosts,
    IfoodFinancialSnapshot,
)
from app.ifood_integration_models import IfoodMerchantConfig
from app.ifood_order_models import IfoodOrder, IfoodPdvBridge
from app.integrations.ifood import financial_poller as worker
from app.integrations.ifood.client import IfoodClientError
from app.integrations.ifood.pdv_pilot import _validated_pilot_values
from app.integrations.ifood.sale_financials import resolve_sale_financials
from app.models import User
from app.produtos_models import Produto
from app.tenancy.context import tenant_context
from app.vendas_devolucoes_models import VendaDevolucao
from app.vendas_models import Venda, VendaItem


def _bag(order, merchant):
    return {
        "id": order,
        "test": True,
        "merchant": {"id": merchant},
        "operationMode": {"type": "TAKEOUT"},
        "bag": {
            "items": [
                {
                    "uniqueId": "pilot-item",
                    "name": "Megazoo teste",
                    "ean": "7898401961203",
                    "quantity": 1,
                    "product": {"isVariableWeight": False},
                    "unavailable": False,
                    "prices": {"unitValue": {"value": 6500}},
                }
            ],
            "prices": {"grossValue": {"value": 6500}},
        },
        "payment": {
            "methods": [
                {
                    "name": "Cash",
                    "inPerson": True,
                    "amount": {"value": 6500},
                }
            ]
        },
    }


@pytest.fixture
def pilot(monkeypatch):
    for key in ("APP_ENV", "ENV", "ENVIRONMENT"):
        monkeypatch.delenv(key, raising=False)
    tenant, merchant, order = uuid4(), str(uuid4()), str(uuid4())
    for key, value in {
        "ENVIRONMENT": "test",
        "IFOOD_FINANCIAL_READ_ENABLED": True,
        "IFOOD_FINANCIAL_POLLING_ENABLED": True,
        "IFOOD_FINANCIAL_POLLING_INTERVAL_SECONDS": 900,
        "IFOOD_CLIENT_ID": "mock-client",
        "IFOOD_CLIENT_SECRET": "mock-secret",
        "IFOOD_PDV_PILOT_ENABLED": True,
        "IFOOD_PDV_PILOT_TENANT_ID": str(tenant),
        "IFOOD_PDV_PILOT_MERCHANT_ID": merchant,
        "IFOOD_PDV_PILOT_ORDER_ID": order,
        "IFOOD_PDV_PILOT_SKU": "018631.1",
    }.items():
        monkeypatch.setattr(settings, key, value)
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        for model in (
            User,
            Produto,
            Venda,
            VendaItem,
            VendaDevolucao,
            IfoodMerchantConfig,
            IfoodOrder,
            IfoodPdvBridge,
            IfoodFinancialSaleLink,
            IfoodFinancialSnapshot,
            IfoodFinancialEvent,
            IfoodFinancialOrderCosts,
        ):
            connection.execute(
                CreateTable(model.__table__, include_foreign_key_constraints=[])
            )
        # CreateTable nao inclui indexes; a constraint de uma revisao ativa e
        # essencial para detectar acumulacao silenciosa durante este ensaio.
        for index in IfoodFinancialSnapshot.__table__.indexes:
            index.create(connection)
    now = datetime.now(timezone.utc)

    class Clock:
        @classmethod
        def now(cls, _tz):
            return cls.current

    Clock.current = now
    monkeypatch.setattr(worker, "datetime", Clock)
    payload = _bag(order, merchant)
    values = _validated_pilot_values(
        SimpleNamespace(payload=payload, ifood_order_id=order, merchant_id=merchant)
    )
    with engine.begin() as connection:
        connection.execute(
            insert(User.__table__).values(
                id=7, tenant_id=tenant, email="mock@example.test"
            )
        )
        connection.execute(
            insert(Produto.__table__).values(
                id=10,
                tenant_id=tenant,
                user_id=7,
                codigo="018631.1",
                nome="Produto DEV",
                estoque_atual=31,
                preco_venda=65,
            )
        )
        connection.execute(
            insert(Venda.__table__).values(
                id=2,
                tenant_id=tenant,
                numero_venda="DEV-1420",
                vendedor_id=7,
                user_id=7,
                subtotal=65,
                total=65,
                status="finalizada",
                canal="ifood",
                data_venda=now,
            )
        )
        connection.execute(
            insert(VendaItem.__table__).values(
                id=20,
                tenant_id=tenant,
                venda_id=2,
                produto_id=10,
                tipo="produto",
                quantidade=1,
                preco_unitario=65,
                subtotal=65,
            )
        )
        connection.execute(
            insert(IfoodMerchantConfig.__table__).values(
                tenant_id=tenant, merchant_id=merchant, active=False
            )
        )
        connection.execute(
            insert(IfoodOrder.__table__).values(
                tenant_id=tenant,
                merchant_id=merchant,
                ifood_order_id=order,
                display_id="1420",
                status="CONCLUDED",
                payload=payload,
                placed_at=now,
            )
        )
        connection.execute(
            insert(IfoodPdvBridge.__table__).values(
                tenant_id=tenant,
                merchant_id=merchant,
                ifood_order_id=order,
                sale_id=2,
                reservation_id=3,
                product_id=10,
                quantity=1,
                unit_price=65,
                evidence_hash=values["evidence_hash"],
                status="sold",
                actor_id=7,
                stock_decreased_at=now,
            )
        )
    state = SimpleNamespace(
        tenant=tenant,
        merchant=merchant,
        order=order,
        engine=engine,
        clock=Clock,
        pages=[{"page": 1, "size": 100, "hasNextPage": False, "financialEvents": []}],
        error=None,
        calls=[],
    )

    class Client:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            pass

        def fetch_financial_pages(self, merchant, begin, end):
            state.calls.append((merchant, begin, end))
            if state.error:
                raise state.error
            return deepcopy(state.pages)

    monkeypatch.setattr(worker, "SessionLocal", lambda: Session(engine))
    monkeypatch.setattr(worker, "IfoodFinancialClient", Client)
    worker._retry_state.clear()
    yield state
    worker._retry_state.clear()
    engine.dispose()


def _event(pilot, name, value, *, begin=None, end=None):
    day = pilot.clock.current.date().isoformat()
    return {
        "name": name,
        "trigger": "SALE_CONCLUDED",
        "period": {"beginDate": begin or day, "endDate": end or day},
        "reference": {"type": "ORDER", "id": pilot.order},
        "hasTransferImpact": True,
        "amount": {"value": value},
        "receiver": {"merchantId": pilot.merchant},
    }


def _current(pilot):
    with tenant_context(pilot.tenant), Session(pilot.engine) as db:
        return resolve_sale_financials(db, pilot.tenant, 2)


def _step(pilot):
    pilot.clock.current += timedelta(seconds=901)
    return worker.poll_ifood_financial_once()


def test_absent_partial_complete_revision_updates_read_model_without_business_writes(
    pilot,
):
    assert _current(pilot)["charges"] == []
    assert worker.poll_ifood_financial_once()["status"] == "imported"
    assert not _current(pilot)["complete"]
    pilot.pages[0]["financialEvents"] = [_event(pilot, "ORDER_COMMISSION", "-10.00")]
    assert _step(pilot)["status"] == "imported"
    partial = _current(pilot)
    assert partial["fee_known_total"] == 10 and not partial["complete"]
    assert [item["code"] for item in partial["pending_components"]] == [
        "PAYMENT_TRANSACTION_FEE"
    ]
    pilot.pages[0]["financialEvents"].append(
        _event(pilot, "PAYMENT_TRANSACTION_FEE", "-2.00")
    )
    assert _step(pilot)["status"] == "imported"
    assert _current(pilot)["fee_total"] == 12
    assert _step(pilot)["status"] == "unchanged"
    pilot.pages[0]["financialEvents"][0]["amount"]["value"] = "-9.00"
    assert _step(pilot)["status"] == "imported"
    assert _current(pilot)["fee_total"] == 11
    with tenant_context(pilot.tenant), Session(pilot.engine) as db:
        snapshots = (
            db.query(IfoodFinancialSnapshot).order_by(IfoodFinancialSnapshot.id).all()
        )
        assert [row.revision for row in snapshots] == [1, 2, 3, 4]
        assert sum(row.active for row in snapshots) == 1
        assert all(
            row.actor_id == 7 and row.mode == "homologation" for row in snapshots
        )
        assert db.execute(select(Produto.estoque_atual)).scalar_one() == 31
        assert db.execute(select(Venda.total)).scalar_one() == 65
        assert db.execute(select(VendaItem.quantidade)).scalar_one() == 1
        assert db.execute(select(IfoodPdvBridge.evidence_hash)).scalar_one()


def test_failure_backoff_and_incomplete_pages_preserve_previous_evidence(pilot):
    pilot.pages[0]["financialEvents"] = [_event(pilot, "ORDER_COMMISSION", "-10.00")]
    assert worker.poll_ifood_financial_once()["status"] == "imported"
    pilot.error = IfoodClientError("Nao registrar conteudo remoto", status_code=429)
    assert _step(pilot) == {"status": "deferred", "status_code": 429}
    assert worker.poll_ifood_financial_once()["status"] == "backoff"
    assert len(pilot.calls) == 2
    pilot.clock.current += timedelta(seconds=1801)
    pilot.error = None
    pilot.pages[0]["hasNextPage"] = True
    assert worker.poll_ifood_financial_once()["status"] == "deferred"
    assert _current(pilot)["fee_known_total"] == 10
    with tenant_context(pilot.tenant), Session(pilot.engine) as db:
        assert db.query(IfoodFinancialSnapshot).count() == 1
        assert db.query(IfoodFinancialSnapshot).one().active


@pytest.mark.parametrize(
    "key,value",
    [
        ("IFOOD_FINANCIAL_READ_ENABLED", False),
        ("IFOOD_FINANCIAL_POLLING_ENABLED", False),
        ("IFOOD_PDV_PILOT_ENABLED", False),
        ("IFOOD_PDV_PILOT_SKU", "other"),
        ("ENVIRONMENT", "production"),
        ("ENVIRONMENT", "staging"),
        ("IFOOD_CLIENT_ID", ""),
    ],
)
def test_flags_and_environment_block_before_database_or_provider(
    pilot, monkeypatch, key, value
):
    monkeypatch.setattr(settings, key, value)
    factory = MagicMock(side_effect=AssertionError("Nao abrir banco quando bloqueado"))
    monkeypatch.setattr(worker, "SessionLocal", factory)
    assert worker.poll_ifood_financial_once()["status"] == "disabled"
    assert not worker.register_financial_poll_job(MagicMock())
    factory.assert_not_called()
    assert pilot.calls == []


def test_alias_environment_production_is_not_overridden_by_dev_setting(
    pilot, monkeypatch
):
    monkeypatch.setenv("APP_ENV", "production")
    assert worker.poll_ifood_financial_once()["status"] == "disabled"
    assert pilot.calls == []


def test_cross_tenant_merchant_and_other_order_are_not_discovered(pilot, monkeypatch):
    for key in (
        "IFOOD_PDV_PILOT_TENANT_ID",
        "IFOOD_PDV_PILOT_MERCHANT_ID",
        "IFOOD_PDV_PILOT_ORDER_ID",
    ):
        original = getattr(settings, key)
        monkeypatch.setattr(settings, key, str(uuid4()))
        assert worker.poll_ifood_financial_once()["status"] == "no_eligible_bridge"
        monkeypatch.setattr(settings, key, original)
        worker._retry_state.clear()
    assert pilot.calls == []


def test_hash_change_and_conflicting_sale_link_fail_before_provider(pilot):
    with pilot.engine.begin() as connection:
        connection.execute(
            insert(IfoodFinancialSaleLink.__table__).values(
                tenant_id=pilot.tenant,
                merchant_id=pilot.merchant,
                mode="homologation",
                order_id=str(uuid4()),
                venda_id=2,
                source="explicit_confirmation",
                source_note="Mock conflict",
                actor_id=7,
                item_manifest=[],
            )
        )
    assert worker.poll_ifood_financial_once() == {
        "status": "deferred",
        "status_code": 409,
    }
    assert pilot.calls == []
    worker._retry_state.clear()
    with pilot.engine.begin() as connection:
        connection.execute(IfoodFinancialSaleLink.__table__.delete())
        connection.execute(
            IfoodPdvBridge.__table__.update().values(evidence_hash="different")
        )
    assert worker.poll_ifood_financial_once() == {
        "status": "deferred",
        "status_code": 409,
    }
    assert pilot.calls == []


def test_existing_window_is_reused_and_recent_snapshot_throttles_after_restart(pilot):
    begin = pilot.clock.current.date() - timedelta(days=2)
    end = pilot.clock.current.date()
    with pilot.engine.begin() as connection:
        connection.execute(
            insert(IfoodFinancialSnapshot.__table__).values(
                tenant_id=pilot.tenant,
                merchant_id=pilot.merchant,
                mode="homologation",
                begin_date=begin,
                end_date=end,
                revision=1,
                active=True,
                source="synthetic",
                payload_hash="mock",
                page_count=1,
                event_count=0,
                actor_id=7,
                created_at=pilot.clock.current,
            )
        )
    assert worker.poll_ifood_financial_once()["status"] == "recent_snapshot"
    assert pilot.calls == []
    worker._retry_state.clear()  # Simula reinicio do processo lider.
    assert worker.poll_ifood_financial_once()["status"] == "recent_snapshot"
    assert _step(pilot)["status"] == "imported"
    assert pilot.calls == [(pilot.merchant, begin, end)]
    with tenant_context(pilot.tenant), Session(pilot.engine) as db:
        assert db.query(IfoodFinancialSnapshot).filter_by(active=True).count() == 1


def test_ambiguous_window_and_old_order_do_not_fetch(pilot):
    day = pilot.clock.current.date()
    with pilot.engine.begin() as connection:
        for offset in (0, 1):
            connection.execute(
                insert(IfoodFinancialSnapshot.__table__).values(
                    tenant_id=pilot.tenant,
                    merchant_id=pilot.merchant,
                    mode="homologation",
                    begin_date=day - timedelta(days=offset),
                    end_date=day,
                    revision=1,
                    active=True,
                    source="synthetic",
                    payload_hash="mock",
                    page_count=1,
                    event_count=0,
                    actor_id=7,
                )
            )
    assert worker.poll_ifood_financial_once() == {
        "status": "deferred",
        "status_code": 409,
    }
    assert pilot.calls == []
    worker._retry_state.clear()
    pilot.clock.current += timedelta(days=34)
    assert worker.poll_ifood_financial_once() == {
        "status": "deferred",
        "status_code": 409,
    }
    assert pilot.calls == []


def test_scheduler_uses_existing_instance_and_clamps_interval(pilot, monkeypatch):
    monkeypatch.setattr(settings, "IFOOD_FINANCIAL_POLLING_INTERVAL_SECONDS", 1)
    scheduler = MagicMock()
    assert worker.register_financial_poll_job(scheduler)
    args, kwargs = scheduler.add_job.call_args
    assert args == (worker.poll_ifood_financial_once, "interval")
    assert kwargs["seconds"] == 900
    assert kwargs["max_instances"] == 1 and kwargs["coalesce"]
    assert "next_run_time" not in kwargs
    assert pilot.calls == []


def test_busy_advisory_lock_skips_provider(pilot, monkeypatch):
    monkeypatch.setattr(worker, "_advisory_lock", lambda *_args: False)
    assert worker.poll_ifood_financial_once()["status"] == "busy"
    assert pilot.calls == []


@pytest.mark.parametrize(
    "target,last",
    [
        (date(2026, 10, 25), 31),
        (date(2026, 2, 15), 28),
        (date(2028, 2, 15), 29),
    ],
)
def test_new_window_is_fixed_month_including_leap_february(pilot, target, last):
    with tenant_context(pilot.tenant), Session(pilot.engine) as db:
        begin, end, current = worker._window(
            db,
            pilot.tenant,
            pilot.merchant,
            target,
            datetime.combine(target, datetime.min.time(), tzinfo=timezone.utc),
        )
    assert begin == target.replace(day=1)
    assert end == target.replace(day=last)
    assert current is None
    assert (end - begin).days <= 30


def test_other_active_days_prevent_overlapping_month_import_before_network(pilot):
    day = pilot.clock.current.date()
    # O dia anterior nao contem o pedido, mas a janela mensal nova o sobreporia.
    with pilot.engine.begin() as connection:
        connection.execute(
            insert(IfoodFinancialSnapshot.__table__).values(
                tenant_id=pilot.tenant,
                merchant_id=pilot.merchant,
                mode="homologation",
                begin_date=day - timedelta(days=1),
                end_date=day - timedelta(days=1),
                revision=1,
                active=True,
                source="synthetic",
                payload_hash="mock",
                page_count=1,
                event_count=0,
                actor_id=7,
            )
        )
    assert worker.poll_ifood_financial_once() == {
        "status": "deferred",
        "status_code": 409,
    }
    assert pilot.calls == []


def test_scope_changed_while_fetching_does_not_import(pilot, monkeypatch):
    original = worker._pilot_target
    calls = []

    def target(*args):
        calls.append(1)
        return original(*args) if len(calls) == 1 else None

    monkeypatch.setattr(worker, "_pilot_target", target)
    assert worker.poll_ifood_financial_once() == {
        "status": "deferred",
        "status_code": 409,
    }
    assert len(pilot.calls) == 1
    with tenant_context(pilot.tenant), Session(pilot.engine) as db:
        assert db.query(IfoodFinancialSnapshot).count() == 0


def test_wrong_merchant_response_keeps_previous_partial_and_sanitizes_logs(
    pilot, caplog
):
    pilot.pages[0]["financialEvents"] = [_event(pilot, "ORDER_COMMISSION", "-10.00")]
    assert worker.poll_ifood_financial_once()["status"] == "imported"
    pilot.pages[0]["financialEvents"][0]["receiver"]["merchantId"] = str(uuid4())
    assert _step(pilot)["status"] == "deferred"
    assert _current(pilot)["fee_known_total"] == 10
    pilot.clock.current += timedelta(seconds=1801)
    pilot.error = IfoodClientError(
        "secret-sentinel-token-must-never-be-logged", status_code=403
    )
    assert worker.poll_ifood_financial_once()["status"] == "deferred"
    assert "secret-sentinel" not in caplog.text


def test_actor_in_another_tenant_and_extra_service_item_block_target(pilot):
    with pilot.engine.begin() as connection:
        connection.execute(User.__table__.update().values(tenant_id=uuid4()))
    assert worker.poll_ifood_financial_once()["status"] == "no_eligible_bridge"
    worker._retry_state.clear()
    with pilot.engine.begin() as connection:
        connection.execute(User.__table__.update().values(tenant_id=pilot.tenant))
        connection.execute(
            insert(VendaItem.__table__).values(
                id=21,
                tenant_id=pilot.tenant,
                venda_id=2,
                produto_id=None,
                tipo="servico",
                quantidade=1,
                preco_unitario=1,
                subtotal=1,
            )
        )
    assert worker.poll_ifood_financial_once()["status"] == "no_eligible_bridge"
    assert pilot.calls == []


def test_postgres_lock_uses_stable_key_isolated_by_tenant_and_merchant():
    db = MagicMock()
    db.get_bind.return_value.dialect.name = "postgresql"
    db.execute.return_value.scalar.return_value = True
    tenant, merchant = uuid4(), str(uuid4())
    assert worker._advisory_lock(db, tenant, merchant)
    first = db.execute.call_args.args[1]["key"]
    assert worker._advisory_lock(db, tenant, merchant)
    assert db.execute.call_args.args[1]["key"] == first
    assert worker._advisory_lock(db, uuid4(), merchant)
    assert db.execute.call_args.args[1]["key"] != first
    assert worker._advisory_lock(db, tenant, str(uuid4()))
    assert db.execute.call_args.args[1]["key"] != first


def test_financial_read_and_poll_defaults_remain_disabled():
    assert Settings.model_fields["IFOOD_FINANCIAL_READ_ENABLED"].default is False
    assert Settings.model_fields["IFOOD_FINANCIAL_POLLING_ENABLED"].default is False
