"""The customer benefits endpoint must not deduct spent cashback twice."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import insert

from app.campaigns.models import CashbackSourceTypeEnum, CashbackTransaction
from app.routes import ecommerce_auth_beneficios


def test_meus_beneficios_ignores_expiration_of_spent_credit(
    db_session, tenant_context, monkeypatch
):
    tenant_id = uuid4()
    now = datetime.now(timezone.utc)
    tenant_context(tenant_id)
    db_session.execute(
        insert(CashbackTransaction),
        [
            {
                "id": 901,
                "tenant_id": tenant_id,
                "customer_id": 42,
                "amount": Decimal("7.00"),
                "source_type": CashbackSourceTypeEnum.campaign,
                "source_id": 900,
                "tx_type": "credit",
                "expires_at": now - timedelta(days=1),
                "created_at": now - timedelta(days=10),
            },
            {
                "id": 902,
                "tenant_id": tenant_id,
                "customer_id": 42,
                "amount": Decimal("-7.00"),
                "source_type": CashbackSourceTypeEnum.redemption,
                "source_id": 12,
                "tx_type": "debit",
                "created_at": now - timedelta(days=2),
            },
            {
                "id": 903,
                "tenant_id": tenant_id,
                "customer_id": 42,
                "amount": Decimal("-7.00"),
                "source_type": CashbackSourceTypeEnum.expiration,
                "source_id": 901,
                "tx_type": "expired",
                "created_at": now - timedelta(days=1),
            },
            {
                "id": 904,
                "tenant_id": tenant_id,
                "customer_id": 42,
                "amount": Decimal("2.77"),
                "source_type": CashbackSourceTypeEnum.manual,
                "tx_type": "credit",
                "created_at": now - timedelta(hours=1),
            },
        ],
    )
    db_session.flush()
    monkeypatch.setattr(
        ecommerce_auth_beneficios,
        "_get_or_create_cliente_for_user",
        lambda *a, **k: SimpleNamespace(id=42),
    )
    monkeypatch.setattr(
        "app.campaigns.loyalty_service.summarize_loyalty_balances_for_customer",
        lambda *a, **k: {},
    )

    result = ecommerce_auth_beneficios.meus_beneficios(
        current_user=SimpleNamespace(tenant_id=tenant_id), db=db_session
    )

    assert result["cashback"]["saldo"] == 2.77
