"""Campaign report must show spendable liability, not raw ledger arithmetic."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import insert

from app.campaigns.clientes_routes import relatorio_campanhas
from app.campaigns.models import CashbackSourceTypeEnum, CashbackTransaction


def test_report_does_not_call_expiration_a_redemption(db_session, tenant_context):
    tenant_id = uuid4()
    now = datetime.now(timezone.utc)
    tenant_context(tenant_id)
    db_session.execute(
        insert(CashbackTransaction),
        [
            {
                "id": 801,
                "tenant_id": tenant_id,
                "customer_id": 42,
                "amount": Decimal("7.00"),
                "source_type": CashbackSourceTypeEnum.campaign,
                "source_id": 900,
                "tx_type": "credit",
                "expires_at": now + timedelta(days=1),
                "created_at": now - timedelta(hours=2),
            },
            {
                "id": 802,
                "tenant_id": tenant_id,
                "customer_id": 42,
                "amount": Decimal("-5.00"),
                "source_type": CashbackSourceTypeEnum.redemption,
                "source_id": 12,
                "tx_type": "debit",
                "created_at": now - timedelta(hours=1),
            },
            {
                "id": 803,
                "tenant_id": tenant_id,
                "customer_id": 42,
                "amount": Decimal("-7.00"),
                "source_type": CashbackSourceTypeEnum.expiration,
                "source_id": 801,
                "tx_type": "expired",
                "created_at": now - timedelta(minutes=30),
            },
        ],
    )
    db_session.flush()

    report = relatorio_campanhas(
        data_inicio=None,
        data_fim=None,
        tipo=None,
        db=db_session,
        user_and_tenant=(None, tenant_id),
    )

    assert [item["id"] for item in report["transacoes"]] == [803, 802, 801]
    assert report["transacoes"][0]["tipo"] == "expiracao"
    assert report["total_creditado"] == 7.0
    assert report["total_resgatado"] == 5.0
    assert report["saldo_total"] == 2.0
