from uuid import uuid4
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.campaigns.models import CashbackSourceTypeEnum, CashbackTransaction
from app.relatorio_vendas_preloads import _carregar_cashback_por_venda
from app.tenancy.context import tenant_context


def test_relatorio_vendas_nao_atribui_reversal_a_venda_com_id_coincidente():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    CashbackTransaction.__table__.create(engine)
    tenant_id = uuid4()
    outro_tenant = uuid4()
    with tenant_context(tenant_id), Session(engine) as db:
        db.execute(
            CashbackTransaction.__table__.insert(),
            [
                dict(
                    id=1,
                    tenant_id=tenant_id,
                    customer_id=10,
                    amount=-5,
                    source_type=CashbackSourceTypeEnum.reversal,
                    source_id=11,
                    created_at=datetime.now(timezone.utc),
                ),
                dict(
                    id=2,
                    tenant_id=tenant_id,
                    customer_id=10,
                    amount=-7,
                    source_type=CashbackSourceTypeEnum.redemption,
                    source_id=11,
                    created_at=datetime.now(timezone.utc),
                ),
                dict(
                    id=3,
                    tenant_id=outro_tenant,
                    customer_id=10,
                    amount=-9,
                    source_type=CashbackSourceTypeEnum.redemption,
                    source_id=11,
                    created_at=datetime.now(timezone.utc),
                ),
            ],
        )

        assert _carregar_cashback_por_venda(db, tenant_id, [11]) == {11: 7.0}
        assert _carregar_cashback_por_venda(db, tenant_id, [12]) == {}
