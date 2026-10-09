from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, insert
from sqlalchemy.orm import Session

from app.campaigns import clientes_routes
from app.campaigns.models import CampaignEventQueue


@pytest.fixture
def saldo_db(monkeypatch):
    from tests.conftest_infra import _get_db_dependencies

    _get_db_dependencies()
    engine = create_engine("sqlite://")
    CampaignEventQueue.__table__.create(engine)
    tenant_a, tenant_b = uuid4(), uuid4()
    with Session(engine) as session:
        rows = [
            (tenant_a, 35, "pending", "purchase_completed"),
            (tenant_a, 35, "processing", "purchase_completed"),
            (tenant_a, "35", "pending", "purchase_completed"),
            (tenant_a, 36, "pending", "purchase_completed"),
            (tenant_b, 35, "processing", "purchase_completed"),
            (tenant_a, 35, "done", "purchase_completed"),
            (tenant_a, 35, "failed", "purchase_completed"),
            (tenant_a, 35, "skipped", "purchase_completed"),
            (tenant_a, 35, "pending", "customer_registered"),
        ]
        session.execute(
            insert(CampaignEventQueue.__table__),
            [
                {
                    "id": index,
                    "tenant_id": tenant,
                    "event_type": kind,
                    "status": status,
                    "payload": {"customer_id": customer},
                }
                for index, (tenant, customer, status, kind) in enumerate(rows, 1)
            ],
        )
        session.commit()
        sequence = []

        class DbProxy:
            def query(self, *entities):
                if entities[0] is CampaignEventQueue.id:
                    sequence.append("fila")
                    return session.query(*entities)
                query = MagicMock()
                query.filter.return_value = query
                query.order_by.return_value = query
                query.limit.return_value = query
                query.all.return_value = []
                query.first.return_value = None
                return query

        def wallet(*args, **kwargs):
            assert sequence[-1] == "fila", "fila precisa ser lida antes dos saldos"
            sequence.append("saldo")
            return SimpleNamespace(available=Decimal("10.00"))

        monkeypatch.setattr(clientes_routes, "get_cashback_wallet", wallet)
        monkeypatch.setattr(
            clientes_routes, "cashback_use_limit_percent", lambda *a: None
        )
        monkeypatch.setattr(
            clientes_routes,
            "summarize_loyalty_balances_for_customer",
            lambda *a, **kw: {
                "total_carimbos": 0,
                "total_carimbos_brutos": 10,
                "carimbos_comprometidos_total": 10,
                "carimbos_em_debito": 0,
                "carimbos_convertidos": 10,
                "ciclos_concluidos": 1,
            },
        )
        yield DbProxy(), session, tenant_a, tenant_b
    engine.dispose()


@pytest.mark.parametrize(
    "tenant,customer,esperado", [(0, 35, 3), (0, 36, 1), (1, 35, 1), (0, 999, 0)]
)
def test_saldo_informa_fila_apenas_do_cliente_e_tenant(
    saldo_db, tenant_context, tenant, customer, esperado
):
    proxy, _, tenant_a, tenant_b = saldo_db
    tenant_id = [tenant_a, tenant_b][tenant]
    tenant_context(tenant_id)
    resposta = clientes_routes.saldo_cliente(customer, proxy, (None, tenant_id))
    assert resposta["beneficios_pendentes"] == esperado
    assert resposta["beneficios_em_processamento"] is (esperado > 0)
    assert resposta["saldo_cashback"] == 10.0
    assert resposta["total_carimbos_brutos"] == 10
    assert resposta["total_carimbos"] == 0


def test_conclusao_da_fila_desliga_sinal_na_proxima_consulta(saldo_db, tenant_context):
    proxy, session, tenant_a, _ = saldo_db
    tenant_context(tenant_a)
    resposta = clientes_routes.saldo_cliente(35, proxy, (None, tenant_a))
    assert resposta["beneficios_em_processamento"] is True
    for event_id in [1, 2, 3]:
        session.get(CampaignEventQueue, event_id).status = "done"
    session.commit()
    resposta = clientes_routes.saldo_cliente(35, proxy, (None, tenant_a))
    assert resposta["beneficios_em_processamento"] is False
    assert resposta["beneficios_pendentes"] == 0
