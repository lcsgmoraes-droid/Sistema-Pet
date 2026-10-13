"""Reaberturas repetidas e recuperação real de flush abortado em PostgreSQL."""

import json
import os
import re
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import Enum, create_engine, func, update
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema, CreateTable, DropSchema

from app.campaigns import handlers, loyalty_service
from app.campaigns.engine import CampaignEngine
from app.campaigns.handlers.loyalty import LoyaltyHandler
from app.campaigns.loyalty_rewards import _append_note
from app.campaigns.models import (
    Campaign,
    CampaignEventQueue,
    CampaignRunLog,
    CampaignTypeEnum,
    LoyaltyStamp,
)
from app.campaigns.worker import CampaignWorker
from app.models import AuditLog
from app.tenancy.context import get_current_tenant


@pytest.mark.parametrize(
    "existing,message",
    [
        (None, "Reativado: último evento"),
        ("x" * 500, "Reativado: último evento"),
        ("Reativado: último evento", "Reativado: último evento"),
        (None, "ação " * 200),
        (" | ".join(f"Evento #{n}" for n in range(100)), "Reativado: último evento"),
    ],
)
def test_resumo_de_carimbo_respeita_limite_do_banco(existing, message):
    note = _append_note(existing, message)
    assert len(note) <= 500
    assert message[:500] in note


def test_handler_fidelidade_propagara_falha_para_recuperar_evento(monkeypatch):
    venda = SimpleNamespace(id=9, cliente_id=2, status="finalizada", total=20)

    class Query:
        def filter(self, *conditions):
            return self

        def first(self):
            return venda

    def failed_process(**kwargs):
        raise ValueError("Falha de fidelidade precisa de nova tentativa")

    handler = LoyaltyHandler()
    monkeypatch.setattr(handler, "_process", failed_process)
    with pytest.raises(ValueError, match="nova tentativa"):
        handler.run(
            SimpleNamespace(query=lambda *a: Query()),
            SimpleNamespace(
                campaign_type=CampaignTypeEnum.loyalty_stamp,
                tenant_id=uuid4(),
                params={},
            ),
            SimpleNamespace(
                id=1, event_type="purchase_completed", payload={"venda_id": 9}
            ),
        )


@pytest.fixture
def pg(monkeypatch, tenant_context):
    url = os.getenv("TEST_CAMPAIGNS_POSTGRES_URL")
    if not url:
        pytest.skip(
            "Informe TEST_CAMPAIGNS_POSTGRES_URL para o PostgreSQL descartável."
        )
    schema = "test_campaigns_" + uuid4().hex
    admin = create_engine(url)
    assert admin.url.host in {"localhost", "127.0.0.1"}
    assert admin.url.database == "corepet_test"
    with admin.begin() as conn:
        conn.execute(CreateSchema(schema))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    try:
        for model in (
            Campaign,
            CampaignEventQueue,
            CampaignRunLog,
            LoyaltyStamp,
            AuditLog,
        ):
            for column in model.__table__.columns:
                if isinstance(column.type, Enum):
                    column.type.create(engine, checkfirst=True)
            with engine.begin() as conn:
                conn.execute(
                    CreateTable(model.__table__, include_foreign_key_constraints=[])
                )

        def sync_rewards(db, *, campaign, customer_id, **kwargs):
            count = (
                db.query(func.count(LoyaltyStamp.id))
                .filter(
                    LoyaltyStamp.tenant_id == campaign.tenant_id,
                    LoyaltyStamp.customer_id == customer_id,
                    LoyaltyStamp.voided_at.is_(None),
                )
                .scalar()
            )
            return dict(
                total_stamps=count,
                available_stamps=count,
                converted_stamps=0,
                debt_stamps=0,
                awarded=0,
                revoked=0,
            )

        monkeypatch.setattr(
            loyalty_service, "sync_loyalty_rewards_for_customer", sync_rewards
        )
        yield SimpleNamespace(engine=engine, tenant_context=tenant_context)
    finally:
        engine.dispose()
        assert re.fullmatch(r"test_campaigns_[0-9a-f]{32}", schema)
        with admin.begin() as conn:
            conn.execute(DropSchema(schema, cascade=True))
        admin.dispose()


def _campaign_and_event(pg, tenant=None):
    tenant = tenant or uuid4()
    pg.tenant_context(tenant)
    with Session(pg.engine) as db:
        campaign = Campaign(
            tenant_id=tenant,
            name="Teste exclusivo",
            campaign_type="loyalty_stamp",
            params={"min_purchase_value": 10},
            priority=10,
        )
        event = CampaignEventQueue(
            tenant_id=tenant,
            event_type="daily_birthday_check",
            payload={"customer_id": 2},
            status="pending",
        )
        db.add_all([campaign, event])
        db.commit()
        return tenant, campaign.id, event.id


def _faulting_loyalty_handler(monkeypatch, fail_for_tenant):
    def run(*, db, campaign, event):
        result = loyalty_service.sync_loyalty_stamps_for_sale(
            db,
            campaign=campaign,
            customer_id=2,
            venda_id=9,
            venda_total=20,
            source_event_id=event.id,
            reason=f"Evento #{event.id}",
        )
        if fail_for_tenant(campaign.tenant_id):
            # Flush de SQL real falha no VARCHAR(500), depois de criar carimbos
            # e auditoria na mesma transação: nenhum deles pode sobreviver.
            db.execute(
                update(LoyaltyStamp)
                .where(LoyaltyStamp.tenant_id == campaign.tenant_id)
                .values(notes="x" * 501)
            )
        return dict(evaluated=1, rewarded=result["awarded"], errors=0)

    monkeypatch.setattr(handlers, "get_handler", lambda *a: SimpleNamespace(run=run))


def _queue_state(pg, event_id):
    with Session(pg.engine) as db:
        event = db.get(CampaignEventQueue, event_id)
        return str(event.status.value), event.retry_count, event.error_message


def test_muitos_ciclos_respeitam_varchar_e_preservam_auditoria_integral(pg):
    tenant, campaign_id, _ = _campaign_and_event(pg)
    reasons = []
    with Session(pg.engine) as db:
        campaign = db.get(Campaign, campaign_id)
        for cycle in range(25):
            for total in (80, 0):
                reason = f"Ciclo {cycle}, total {total}: " + "á" * 600
                reasons.append(reason)
                loyalty_service.sync_loyalty_stamps_for_sale(
                    db,
                    campaign=campaign,
                    customer_id=2,
                    venda_id=9,
                    venda_total=total,
                    source_event_id=cycle,
                    reason=reason,
                )
                db.commit()
        campaign.params = {"min_purchase_value": 50}
        result = loyalty_service.sync_loyalty_stamps_for_sale(
            db,
            campaign=campaign,
            customer_id=2,
            venda_id=9,
            venda_total=80,
            source_event_id=99,
            reason="Refinalização com regra histórica",
        )
        db.commit()
        stamps = db.query(LoyaltyStamp).filter(LoyaltyStamp.tenant_id == tenant).all()
        assert len(stamps) == 8
        assert all(s.voided_at is None and len(s.notes) <= 500 for s in stamps)
        assert all(s.stamp_value_snapshot == Decimal("10") for s in stamps)
        assert result["stamps_reactivated"] == 8
        audit = db.query(AuditLog).order_by(AuditLog.id).all()
        assert len(audit) == 51
        recorded = [json.loads(row.new_value)["metadata"]["reason"] for row in audit]
        assert recorded[:-1] == reasons
        assert recorded[-1] == "Refinalização com regra histórica"


def test_flush_abortado_volta_para_fila_e_proxima_tentativa_nao_duplica(
    pg, monkeypatch
):
    tenant, _, event_id = _campaign_and_event(pg)
    state = {"fail": True}
    _faulting_loyalty_handler(monkeypatch, lambda tenant_id: state["fail"])
    worker = CampaignWorker(lambda: Session(pg.engine))
    assert worker.process_batch() == 1
    status, retries, error = _queue_state(pg, event_id)
    assert (status, retries) == ("pending", 1)
    assert "character varying(500)" in error
    assert get_current_tenant() is None
    pg.tenant_context(tenant)
    with Session(pg.engine) as db:
        assert db.query(LoyaltyStamp).count() == 0
        assert db.query(AuditLog).count() == 0
        assert db.query(CampaignRunLog).count() == 0
    state["fail"] = False
    assert worker.process_batch() == 1
    assert _queue_state(pg, event_id)[:2] == ("done", 1)
    worker._process_one(event_id)  # replay do mesmo evento continua idempotente
    pg.tenant_context(tenant)
    with Session(pg.engine) as db:
        assert db.query(LoyaltyStamp).count() == 2
        assert db.query(AuditLog).count() == 1


def test_falhas_repetidas_respeitam_limite_de_tentativas(pg, monkeypatch):
    _, _, event_id = _campaign_and_event(pg)
    _faulting_loyalty_handler(monkeypatch, lambda tenant_id: True)
    worker = CampaignWorker(lambda: Session(pg.engine))
    for retry in range(1, 4):
        assert worker.process_batch() == 1
        assert _queue_state(pg, event_id)[:2] == (
            "failed" if retry == 3 else "pending",
            retry,
        )
        assert get_current_tenant() is None
    assert worker.process_batch() == 0


def test_falha_de_um_tenant_nao_impede_outro_no_mesmo_batch(pg, monkeypatch):
    tenant_a, _, event_a = _campaign_and_event(pg)
    tenant_b, _, event_b = _campaign_and_event(pg)
    _faulting_loyalty_handler(monkeypatch, lambda tenant_id: tenant_id == tenant_a)
    worker = CampaignWorker(lambda: Session(pg.engine))
    assert worker.process_batch() == 2
    assert _queue_state(pg, event_a)[:2] == ("pending", 1)
    assert _queue_state(pg, event_b)[:2] == ("done", 0)
    for tenant, expected in ((tenant_a, 0), (tenant_b, 2)):
        pg.tenant_context(tenant)
        with Session(pg.engine) as db:
            assert (
                db.query(LoyaltyStamp).filter(LoyaltyStamp.tenant_id == tenant).count()
                == expected
            )


def test_commit_confirmado_nao_perde_estado_terminal_apos_erro_de_resposta(
    pg, monkeypatch
):
    tenant, _, event_id = _campaign_and_event(pg)
    _faulting_loyalty_handler(monkeypatch, lambda tenant_id: False)

    class AckLostSession(Session):
        def commit(self):
            should_fail = any(
                isinstance(row, CampaignEventQueue) and row.status == "done"
                for row in self.identity_map.values()
            )
            super().commit()
            if should_fail:
                raise RuntimeError("Resposta perdida depois do commit confirmado")

    with AckLostSession(pg.engine) as db:
        event = db.get(CampaignEventQueue, event_id)
        with pytest.raises(RuntimeError, match="commit confirmado"):
            CampaignEngine(db).process_event(event)
    assert _queue_state(pg, event_id)[:2] == ("done", 0)
    assert get_current_tenant() is None
    pg.tenant_context(tenant)
    with Session(pg.engine) as db:
        assert db.query(LoyaltyStamp).count() == 2
