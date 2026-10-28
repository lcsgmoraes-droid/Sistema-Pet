"""Exercise opaque machine auth with the real request/ORM tenant boundary."""

import hashlib
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import get_session
from app.ecommerceai_fiscal import routes
from app.ecommerceai_fiscal.models import ExternalFiscalOrder, FiscalAccount
from app.ecommerceai_integration_models import (
    EcommerceAIConnection,
    EcommerceAIConnectionRequest,
)
from app.middlewares.tenant_middleware import TenantSecurityMiddleware
from app.models import Tenant
from app.tenancy.context import (
    TenantContextMiddleware,
    clear_current_tenant,
    get_current_tenant,
    tenant_context,
)
from app.tenancy.filters import register_tenant_filter_once


PREFIX = "/api/integracoes/ecommerceai/fiscal"


@pytest.fixture
def machine_http():
    register_tenant_filter_once()
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    for model in (
        Tenant,
        EcommerceAIConnectionRequest,
        EcommerceAIConnection,
        FiscalAccount,
        ExternalFiscalOrder,
    ):
        model.__table__.create(engine)
    tenants = (uuid4(), uuid4())
    tokens = [f"cp_eai_fixture_{uuid4().hex}" for _ in range(4)]
    with Session(engine, expire_on_commit=False) as db:
        db.add_all(
            Tenant(
                id=str(tenant_id),
                name=f"Synthetic tenant {index}",
                name_normalized=f"synthetic tenant {index}",
                status="active",
            )
            for index, tenant_id in enumerate(tenants)
        )
        connections = []
        for index, raw in enumerate(tokens):
            connection = EcommerceAIConnection(
                public_id=str(uuid4()),
                request_id=str(uuid4()),
                tenant_id=tenants[index % 2],
                ecommerceai_user_id="synthetic-operator",
                status="connected",
                token_hash=hashlib.sha256(raw.encode()).hexdigest(),
                token_prefix="cp_eai_fixture",
                scopes=["fiscal:read"] if index != 2 else ["catalog:read"],
                revoked_at=datetime.now(timezone.utc) if index == 3 else None,
            )
            db.add(connection)
            connections.append(connection)
        db.flush()
        with tenant_context(tenants[1]):
            # Another tenant has a configured seller and an existing fiscal job.
            # The empty authority of tenant 0 must not expose either record.
            db.add(
                FiscalAccount(
                    tenant_id=tenants[1],
                    channel="amazon",
                    seller_id="PRIVATE_OTHER_SELLER",
                    marketplace_id="A2Q3Y263D00KWC",
                    emitter_cnpj="11222333000181",
                    approved_by_user_id=77,
                )
            )
            order = ExternalFiscalOrder(
                tenant_id=tenants[1],
                connection_id=connections[1].id,
                channel="amazon",
                seller_id="PRIVATE_OTHER_SELLER",
                external_order_id="999-1234567-7654321",
                source_revision=1,
                source_hash="a" * 64,
                source={
                    "totals": {
                        "products": "10.00",
                        "discount": "0.00",
                        "freight": "0.00",
                        "invoice_total": "10.00",
                    }
                },
                purchased_at=datetime.now(timezone.utc),
                status="blocked",
                blockers=[],
            )
            db.add(order)
            db.commit()
            order_id = order.id
    clear_current_tenant()
    observed_tenants = []

    @event.listens_for(engine, "before_cursor_execute")
    def observe_tenant(_conn, _cursor, statement, _params, _context, _many):
        if statement.lstrip().upper().startswith("SELECT") and (
            "FROM ecommerceai_fiscal_accounts" in statement
            or "FROM ecommerceai_fiscal_orders" in statement
        ):
            observed_tenants.append(get_current_tenant())

    def fixture_session():
        with Session(engine, expire_on_commit=False) as db:
            yield db

    app = FastAPI()
    app.add_middleware(TenantContextMiddleware)
    app.add_middleware(TenantSecurityMiddleware)
    app.include_router(routes.router, prefix="/api")
    app.dependency_overrides[get_session] = fixture_session
    # No override of machine_connection, scope checks, get_tenant or ORM hooks.
    try:
        with TestClient(app) as client:
            yield SimpleNamespace(
                client=client,
                engine=engine,
                tokens=tokens,
                tenants=tenants,
                order_id=order_id,
                observed_tenants=observed_tenants,
            )
    finally:
        clear_current_tenant()
        engine.dispose()


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_real_bearer_propagates_tenant_into_configuration_handler(machine_http):
    ctx = machine_http
    assert get_current_tenant() is None
    response = ctx.client.get(
        PREFIX + "/configuration/accounts", headers=bearer(ctx.tokens[0])
    )
    assert response.status_code == 200, response.text
    assert response.json()["schema_version"] == "1.1"
    assert response.json()["accounts"] == []
    assert ctx.observed_tenants == [ctx.tenants[0]]
    assert get_current_tenant() is None


def test_real_bearer_isolates_jobs_and_does_not_leak_between_requests(machine_http):
    ctx = machine_http
    path = PREFIX + f"/orders/{ctx.order_id}"
    own = ctx.client.get(path, headers=bearer(ctx.tokens[1]))
    assert own.status_code == 200, own.text
    assert own.json()["external_order_id"] == "999-1234567-7654321"
    other = ctx.client.get(path, headers=bearer(ctx.tokens[0]))
    assert other.status_code == 404
    own_again = ctx.client.get(path, headers=bearer(ctx.tokens[1]))
    assert own_again.status_code == 200
    assert ctx.observed_tenants == [ctx.tenants[1], ctx.tenants[0], ctx.tenants[1]]
    assert get_current_tenant() is None


@pytest.mark.parametrize("token_index, expected", [(None, 401), (2, 403), (3, 401)])
def test_machine_configuration_keeps_auth_scope_and_revocation_guards(
    machine_http, token_index, expected
):
    ctx = machine_http
    headers = bearer(ctx.tokens[token_index]) if token_index is not None else {}
    response = ctx.client.get(PREFIX + "/configuration/accounts", headers=headers)
    assert response.status_code == expected
    assert ctx.observed_tenants == []
    assert get_current_tenant() is None


def test_orm_still_rejects_direct_fiscal_query_without_tenant(machine_http):
    assert get_current_tenant() is None
    with Session(machine_http.engine) as db:
        with pytest.raises(RuntimeError, match="ORM FAIL-FAST.*sem tenant_id"):
            db.query(FiscalAccount).all()
