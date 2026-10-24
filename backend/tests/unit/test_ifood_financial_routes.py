from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateTable
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_user_and_tenant
from app.config import settings
from app.db import Base, get_session
from app.ifood_financial_cost_models import IfoodFinancialSaleLink
from app.ifood_financial_models import (
    IfoodFinancialEvent,
    IfoodFinancialOrderCosts,
    IfoodFinancialSnapshot,
)
from app.ifood_integration_models import IfoodMerchantConfig
from app.ifood_payout_models import IfoodPayoutSnapshot, IfoodReconciliationJob
from app.integrations.ifood.client import IfoodClientError
from app.routes import ifood_financial_routes as routes
from app.security import permissions_decorator, permissions_service
from app.tenancy.context import tenant_context


@pytest.fixture
def api(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(
        engine,
        tables=[
            model.__table__
            for model in (
                IfoodMerchantConfig,
                IfoodFinancialSnapshot,
                IfoodFinancialEvent,
                IfoodFinancialOrderCosts,
                IfoodPayoutSnapshot,
                IfoodReconciliationJob,
            )
        ],
    )
    with engine.begin() as connection:
        connection.execute(
            CreateTable(
                IfoodFinancialSaleLink.__table__, include_foreign_key_constraints=[]
            )
        )
    db = Session(engine)
    tenant, other = uuid4(), uuid4()
    merchant, other_merchant = str(uuid4()), str(uuid4())
    state = dict(tenant=tenant, merchant=merchant, denied=set(), calls=0, fail=None)
    for tid, mid in ((tenant, merchant), (other, other_merchant)):
        with tenant_context(tid):
            db.add(
                IfoodMerchantConfig(
                    tenant_id=tid,
                    merchant_id=mid,
                    active=False,
                    commission_merchant_percent=6,
                )
            )
            db.commit()

    def permission(_db, _user, code, _tenant, **_kwargs):
        if code in state["denied"]:
            raise HTTPException(403, "Sem permissao")

    monkeypatch.setattr(permissions_decorator, "check_permission", permission)
    monkeypatch.setattr(permissions_service, "check_permission", permission)
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(settings, "IFOOD_FINANCIAL_READ_ENABLED", True)
    monkeypatch.setattr(settings, "IFOOD_CLIENT_ID", "test-client")
    monkeypatch.setattr(settings, "IFOOD_CLIENT_SECRET", "test-secret")
    monkeypatch.setattr(settings, "IFOOD_CATALOG_WRITE_ENABLED", False)
    monkeypatch.setattr(settings, "IFOOD_ORDER_OPERATIONS_ENABLED", False)
    monkeypatch.setattr(settings, "IFOOD_ORDER_POLLING_ENABLED", False)

    class ReadOnlyProvider:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            pass

        def fetch_settlements(self, mid, begin, end, basis):
            state["calls"] += 1
            if state["fail"]:
                raise IfoodClientError(
                    "Acesso Financial recusado.", status_code=state["fail"]
                )
            return dict(
                merchantId=mid,
                beginDate=str(begin),
                endDate=str(end),
                balance="91",
                settlements=[
                    dict(
                        startDateCalculation=str(begin),
                        endDateCalculation=str(end),
                        closingItems=[
                            dict(
                                id="title-1",
                                type="REPASSE",
                                amount="91",
                                status="SUCCEED",
                                paymentDate=str(end),
                            )
                        ],
                    )
                ],
            )

        def create_reconciliation(self, mid, competence):
            state["calls"] += 1
            return dict(
                merchant_id=mid,
                competence=competence,
                request_id="request-1",
                status="created",
            )

        def get_reconciliation(self, mid, request_id, competence):
            state["calls"] += 1
            return dict(
                merchant_id=mid,
                competence=competence,
                request_id=request_id,
                status="enqueue",
            )

        def fetch_financial_pages(self, mid, begin, end):
            state["calls"] += 1
            if state["fail"]:
                raise IfoodClientError(
                    "Acesso Financial recusado.", status_code=state["fail"]
                )

            def event(name, value, transfer=True):
                return dict(
                    name=name,
                    trigger="SALE_CONCLUDED",
                    period={"beginDate": str(begin), "endDate": str(end)},
                    reference={"type": "ORDER", "id": "dev-sale-1"},
                    receiver={"businessType": "MERCHANT", "businessId": mid},
                    amount={"value": value},
                    hasTransferImpact=transfer,
                )

            return [
                dict(
                    page=1,
                    size=100,
                    hasNextPage=False,
                    financialEvents=[
                        event("ORDER_PAYMENT", "100"),
                        event("ORDER_COMMISSION", "-6"),
                        event("PAYMENT_TRANSACTION_FEE", "-3"),
                    ],
                )
            ]

    monkeypatch.setattr(routes, "IfoodFinancialClient", ReadOnlyProvider)
    app = FastAPI()
    app.include_router(routes.router)
    app.dependency_overrides[get_current_user_and_tenant] = lambda: (
        SimpleNamespace(id=7),
        state["tenant"],
    )

    def session():
        yield db

    app.dependency_overrides[get_session] = session
    with TestClient(app) as client:
        yield SimpleNamespace(
            client=client,
            db=db,
            tenant=tenant,
            merchant=merchant,
            other=other,
            other_merchant=other_merchant,
            state=state,
        )
    db.close()
    engine.dispose()


BASE = "/integracoes/ifood/financeiro"
PERIOD = {"begin_date": "2026-10-05", "end_date": "2026-10-11"}


def test_sync_persists_evidence_and_manual_contribution_without_enabling_operations(
    api,
):
    assert api.client.get(BASE + "/status").json()["can_sync"] is True
    result = api.client.post(BASE + "/sincronizar", json=PERIOD)
    assert result.status_code == 200, result.text
    order = result.json()["orders"][0]
    assert order["totals"]["fees"] == "-9.00"
    assert not order["contribution"]["calculated"]
    costs = api.client.put(
        BASE + "/pedidos/dev-sale-1/custos",
        json={
            "revenue": "100.00",
            "cmv": "60.00",
            "tax": "4.00",
            "other_costs": "1.00",
            "source_note": "Custos ficticios para DEV",
        },
    )
    assert costs.status_code == 200, costs.text
    assert costs.json()["contribution"]["amount"] == "26.00"
    report = api.client.get(BASE + "/relatorio", params=PERIOD).json()
    assert report["orders"][0]["manual_costs"]["version"] == 1
    with tenant_context(api.tenant):
        config = api.db.query(IfoodMerchantConfig).first()
        assert config.active is False and config.commission_merchant_percent == 6
    assert not settings.IFOOD_CATALOG_WRITE_ENABLED
    assert not settings.IFOOD_ORDER_OPERATIONS_ENABLED
    assert not settings.IFOOD_ORDER_POLLING_ENABLED


def test_read_permission_does_not_grant_import_or_manual_cost_edits(api):
    api.state["denied"].add("configuracoes.editar")
    status = api.client.get(BASE + "/status").json()
    assert not status["can_edit_costs"] and not status["can_sync"]
    assert api.client.get(BASE + "/relatorio", params=PERIOD).status_code == 200
    assert api.client.post(BASE + "/sincronizar", json=PERIOD).status_code == 403
    assert (
        api.client.put(
            BASE + "/pedidos/dev-sale-1/custos", json={"source_note": "Ficticio"}
        ).status_code
        == 403
    )
    assert api.state["calls"] == 0


def test_financial_permission_is_required_even_for_catalogue_reader(api):
    api.state["denied"].add("relatorios.financeiro")
    for path in ("/status", "/relatorio"):
        assert api.client.get(BASE + path, params=PERIOD).status_code == 403
    assert api.client.post(BASE + "/sincronizar", json=PERIOD).status_code == 403
    assert api.state["calls"] == 0


def test_provider_failure_keeps_previous_snapshot_and_corepet_session(api):
    first = api.client.post(BASE + "/sincronizar", json=PERIOD).json()
    api.state["fail"] = 403
    failed = api.client.post(BASE + "/sincronizar", json=PERIOD)
    assert failed.status_code == 502
    assert api.client.get(BASE + "/relatorio", params=PERIOD).json() == first
    api.state["fail"] = 429
    assert api.client.post(BASE + "/sincronizar", json=PERIOD).status_code == 429


def test_financial_cannot_be_enabled_in_production_or_by_extra_body_fields(
    api, monkeypatch
):
    assert (
        api.client.post(
            BASE + "/sincronizar", json=PERIOD | {"mode": "production"}
        ).status_code
        == 422
    )
    assert (
        api.client.post(
            BASE + "/sincronizar", json=PERIOD | {"tenant_id": str(api.other)}
        ).status_code
        == 422
    )
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    assert api.client.get(BASE + "/status").status_code == 409
    assert api.client.get(BASE + "/relatorio", params=PERIOD).status_code == 409
    assert api.client.post(BASE + "/sincronizar", json=PERIOD).status_code == 409
    assert (
        api.client.put(
            BASE + "/pedidos/dev-sale-1/custos", json={"source_note": "Ficticio"}
        ).status_code
        == 409
    )
    assert api.state["calls"] == 0


def test_changing_selected_tenant_hides_other_merchants_orders(api):
    assert api.client.post(BASE + "/sincronizar", json=PERIOD).status_code == 200
    api.state["tenant"] = api.other
    result = api.client.get(BASE + "/relatorio", params=PERIOD)
    assert result.status_code == 200 and result.json()["orders"] == []
    missing = api.client.put(
        BASE + "/pedidos/dev-sale-1/custos", json={"source_note": "Teste isolado"}
    )
    assert missing.status_code == 404
    assert api.client.post(BASE + "/sincronizar", json=PERIOD).status_code == 200
    assert (
        api.client.get(BASE + "/relatorio", params=PERIOD).json()["merchant_id"]
        == api.other_merchant
    )


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-1", "1.001", True])
def test_cost_body_rejects_invalid_money(api, value):
    result = api.client.put(
        BASE + "/pedidos/dev-sale-1/custos",
        json={"cmv": value, "source_note": "Ficticio DEV"},
    )
    assert result.status_code == 422


def new_requests(api):
    return [
        lambda: api.client.get(BASE + "/repasses", params=PERIOD),
        lambda: api.client.post(BASE + "/repasses/sincronizar", json=PERIOD),
        lambda: api.client.get(
            BASE + "/conciliacao/status", params={"competence": "2026-10"}
        ),
        lambda: api.client.post(
            BASE + "/conciliacao/sincronizar", json={"competence": "2026-10"}
        ),
        lambda: api.client.get(BASE + "/pedidos/dev-sale-1/vendas-candidatas"),
        lambda: api.client.put(
            BASE + "/pedidos/dev-sale-1/vinculo-venda",
            json={"venda_id": 1, "source_note": "Confirmação DEV"},
        ),
    ]


def test_new_surfaces_are_all_dev_only(api, monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    assert [request().status_code for request in new_requests(api)] == [409] * 6
    assert api.state["calls"] == 0


def test_new_surfaces_require_financial_permission(api):
    api.state["denied"].add("relatorios.financeiro")
    assert [request().status_code for request in new_requests(api)] == [403] * 6
    assert api.state["calls"] == 0


def test_new_mutations_require_edit_permission(api):
    api.state["denied"].add("configuracoes.editar")
    requests = new_requests(api)
    assert [requests[i]().status_code for i in (1, 3, 4, 5)] == [403] * 4
    assert requests[0]().status_code == requests[2]().status_code == 200
    assert not api.client.get(BASE + "/status").json()["can_sync_payouts"]
    assert api.state["calls"] == 0


def test_payout_import_job_cache_and_scope_do_not_enable_ifood_operations(api):
    result = api.client.post(BASE + "/repasses/sincronizar", json=PERIOD)
    assert result.status_code == 200, result.text
    assert result.json()["titles"][0]["bank_status"] == "not_checked"
    assert result.json()["titles"][0]["reconciliation_status"] == "pending"
    month = {"competence": "2026-10"}
    first = api.client.post(BASE + "/conciliacao/sincronizar", json=month)
    assert first.status_code == 200, first.text
    assert first.json()["job"]["status"] == "created"
    assert (
        api.client.post(BASE + "/conciliacao/sincronizar", json=month).json()["job"][
            "id"
        ]
        == first.json()["job"]["id"]
    )
    assert api.state["calls"] == 2
    assert api.client.get(BASE + "/conciliacao/status", params=month).status_code == 200
    assert api.state["calls"] == 2
    api.state["tenant"] = api.other
    assert not api.client.get(BASE + "/repasses", params=PERIOD).json()["imported"]
    assert (
        api.client.get(BASE + "/conciliacao/status", params=month).json()["job"] is None
    )
    assert (
        not settings.IFOOD_CATALOG_WRITE_ENABLED
        and not settings.IFOOD_ORDER_OPERATIONS_ENABLED
    )


@pytest.mark.parametrize(
    "extra",
    [
        dict(tenant_id="other"),
        dict(merchant_id="other"),
        dict(mode="production"),
        dict(download_url="https://localhost"),
    ],
)
def test_provider_scope_and_download_cannot_be_supplied_by_user(api, extra):
    assert (
        api.client.post(BASE + "/repasses/sincronizar", json=PERIOD | extra).status_code
        == 422
    )
    assert (
        api.client.post(
            BASE + "/conciliacao/sincronizar", json={"competence": "2026-10"} | extra
        ).status_code
        == 422
    )
    assert api.state["calls"] == 0


def test_failed_payout_refresh_keeps_prior_snapshot_and_financial_session(api):
    first = api.client.post(BASE + "/repasses/sincronizar", json=PERIOD).json()
    api.state["fail"] = 403
    assert (
        api.client.post(BASE + "/repasses/sincronizar", json=PERIOD).status_code == 502
    )
    assert api.client.get(BASE + "/repasses", params=PERIOD).json() == first
    api.state["fail"] = 429
    assert (
        api.client.post(BASE + "/repasses/sincronizar", json=PERIOD).status_code == 429
    )
