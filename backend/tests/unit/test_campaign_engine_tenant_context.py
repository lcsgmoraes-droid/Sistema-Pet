from types import SimpleNamespace
from uuid import uuid4

from app.campaigns.engine import CampaignEngine
from app.tenancy.context import clear_current_tenant, get_current_tenant


class _Db:
    def __init__(self):
        self.committed = False

    def commit(self):
        self.committed = True


def test_campaign_engine_sets_tenant_context_while_processing_event():
    tenant_id = uuid4()
    db = _Db()
    checks = []

    class _Engine(CampaignEngine):
        def _get_active_campaigns(
            self, *, tenant_id: object, event_type: str, sale_channel=None
        ):
            checks.append(("list", get_current_tenant()))
            return [SimpleNamespace(id=1, campaign_type="loyalty_stamp")]

        def _run_campaign(self, campaign, event):
            checks.append(("run", get_current_tenant()))

    event = SimpleNamespace(
        id=123,
        tenant_id=tenant_id,
        event_type="daily_birthday_check",
        event_depth=0,
        payload={"canal": "loja_fisica"},
        retry_count=0,
        max_retries=3,
        status="pending",
        processed_at=None,
    )
    clear_current_tenant()

    _Engine(db=db).process_event(event)

    assert checks == [("list", tenant_id), ("run", tenant_id)]
    assert event.status == "done"
    assert db.committed is True
    assert get_current_tenant() is None


def test_purchase_without_sale_id_cannot_grant_quick_repurchase_coupon():
    tenant_id = uuid4()
    db = _Db()

    class _Engine(CampaignEngine):
        def _get_active_campaigns(self, **kwargs):
            raise AssertionError("Campanhas nao devem processar compra sem venda")

    event = SimpleNamespace(
        id=124,
        tenant_id=tenant_id,
        event_type="purchase_completed",
        event_depth=0,
        payload={"customer_id": 8, "venda_total": 100},
        retry_count=0,
        max_retries=3,
        status="pending",
        processed_at=None,
    )

    _Engine(db=db).process_event(event)

    assert event.status == "skipped"
    assert db.committed is True


def test_purchase_event_skips_campaigns_when_sale_blocks_benefits():
    tenant_id = uuid4()
    checks = []

    class _Query:
        def filter(self, *conditions):
            return self

        def first(self):
            return SimpleNamespace(nao_gerar_beneficios=True)

    class _BlockedSaleDb(_Db):
        def query(self, model):
            return _Query()

    class _Engine(CampaignEngine):
        def _get_active_campaigns(self, **kwargs):
            checks.append("campaigns")
            return []

    db = _BlockedSaleDb()
    event = SimpleNamespace(
        id=124,
        tenant_id=tenant_id,
        event_type="purchase_completed",
        event_depth=0,
        payload={"venda_id": 123, "customer_id": 456},
        status="pending",
        processed_at=None,
    )

    _Engine(db).process_event(event)

    assert event.status == "skipped"
    assert event.processed_at is not None
    assert db.committed is True
    assert checks == []
    assert get_current_tenant() is None
