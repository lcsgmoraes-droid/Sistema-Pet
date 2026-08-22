from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
import app.produtos_catalogo_models  # noqa: F401 - registra Produto
import app.produtos_estoque_models  # noqa: F401 - completa relacionamentos do catalogo
from app.ifood_integration_models import IfoodMerchantConfig
from app.ifood_order_models import IfoodEvent, IfoodOrder
from app.integrations.ifood.orders import order_detail, process_order_events
from app.tenancy.context import tenant_context


class FakeIfoodClient:
    def __init__(self):
        self.order_reads = 0
        self.acknowledgments: list[list[str]] = []

    def poll_events(self, merchant_ids):
        assert merchant_ids == ["00000000-0000-0000-0000-000000000001"]
        return [
            {
                "id": "event-1",
                "code": "PLC",
                "fullCode": "PLACED",
                "orderId": "order-1",
                "merchantId": merchant_ids[0],
                "createdAt": "2026-08-16T20:00:00Z",
            }
        ]

    def get_order(self, order_id):
        self.order_reads += 1
        assert order_id == "order-1"
        return {
            "id": order_id,
            "displayId": "1010",
            "status": "PLACED",
            "orderType": "DELIVERY",
            "orderTiming": "IMMEDIATE",
            "createdAt": "2026-08-16T20:00:00Z",
            "delivery": {"deliveredBy": "MERCHANT"},
            "total": {"orderAmount": 42.5},
            "customer": {"name": "Cliente Teste"},
            "items": [{"name": "Racao", "quantity": 1}],
        }

    def acknowledge_events(self, event_ids):
        self.acknowledgments.append(event_ids)
        return {"status_code": 202}


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            IfoodMerchantConfig.__table__,
            IfoodOrder.__table__,
            IfoodEvent.__table__,
        ],
    )
    return sessionmaker(bind=engine)()


def test_events_are_persisted_before_ack_and_placed_is_idempotent():
    db = _session()
    tenant_id = uuid4()
    config = IfoodMerchantConfig(
        tenant_id=tenant_id,
        merchant_id="00000000-0000-0000-0000-000000000001",
        active=True,
        catalog_source="ecommerce",
        default_markup_percent=0,
        stock_safety=0,
        status="connected",
    )
    client = FakeIfoodClient()
    with tenant_context(tenant_id):
        db.add(config)
        db.commit()
        first = process_order_events(
            db,
            tenant_id=tenant_id,
            config=config,
            client=client,
        )
        second = process_order_events(
            db,
            tenant_id=tenant_id,
            config=config,
            client=client,
        )

        assert first == {
            "received": 1,
            "acknowledged": 1,
            "failed": 0,
            "created_orders": 1,
            "updated_orders": 0,
        }
        assert second["created_orders"] == 0
        assert client.order_reads == 1
        assert client.acknowledgments == [["event-1"], ["event-1"]]
        assert db.query(IfoodEvent).count() == 1
        assert db.query(IfoodOrder).count() == 1
        stored = db.query(IfoodOrder).one()
        assert stored.status == "PLACED"
        assert stored.delivered_by == "MERCHANT"
        assert stored.total == 42.5
        assert stored.last_event_at.replace(tzinfo=timezone.utc) == datetime(
            2026, 8, 16, 20, 0, tzinfo=timezone.utc
        )
        assert order_detail(stored)["customer_name"] == "Cliente Teste"
