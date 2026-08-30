from __future__ import annotations

import base64
import json
from uuid import uuid4

from app.services.bling_connection_service import (
    extract_bling_company_id,
    get_bling_connection,
    load_bling_credentials,
    resolve_bling_webhook_tenant,
    save_bling_stock_deposit_id,
    save_bling_tokens,
)


def _jwt_with_company(company_id: str) -> str:
    def encode(value: dict) -> str:
        raw = json.dumps(value, separators=(",", ":")).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

    return f"{encode({'alg': 'none'})}.{encode({'companyId': company_id})}.signature"


def test_extract_bling_company_id_from_jwt():
    assert extract_bling_company_id(_jwt_with_company("bling-company-42")) == (
        "bling-company-42"
    )
    assert extract_bling_company_id("token-opaco") is None


def test_extract_bling_company_id_from_nested_jwt_claim():
    def encode(value: dict) -> str:
        raw = json.dumps(value, separators=(",", ":")).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

    token = (
        f"{encode({'alg': 'none'})}."
        f"{encode({'context': {'empresa': {'id': 987654}}})}.signature"
    )

    assert extract_bling_company_id(token) == "987654"


def test_tokens_are_encrypted_and_resolved_by_company(
    db_session, tenant_context, monkeypatch
):
    monkeypatch.setenv("PAYMENT_CONFIG_ENCRYPTION_KEY", "bling-test-master-key")
    tenant_id = uuid4()
    other_tenant_id = uuid4()
    access_token = _jwt_with_company("company-gabi")

    connection = save_bling_tokens(
        tenant_id=tenant_id,
        access_token=access_token,
        refresh_token="refresh-gabi",
        expires_in=3600,
        db=db_session,
    )

    assert connection.tenant_id == tenant_id
    assert connection.company_id == "company-gabi"
    assert connection.access_token == access_token
    assert connection.refresh_token == "refresh-gabi"
    assert connection._access_token_encrypted.startswith("fernet:")
    assert access_token not in connection._access_token_encrypted
    assert connection._refresh_token_encrypted.startswith("fernet:")
    assert "refresh-gabi" not in connection._refresh_token_encrypted

    tenant_context(tenant_id)
    assert get_bling_connection(tenant_id, db=db_session).id == connection.id

    tenant_context(other_tenant_id)
    assert get_bling_connection(other_tenant_id, db=db_session) is None

    assert (
        resolve_bling_webhook_tenant({"companyId": "company-gabi"}, db=db_session)
        == tenant_id
    )


def test_company_cannot_be_linked_to_two_tenants(db_session, monkeypatch):
    monkeypatch.setenv("PAYMENT_CONFIG_ENCRYPTION_KEY", "bling-test-master-key")
    access_token = _jwt_with_company("company-exclusive")
    first_tenant_id = uuid4()
    save_bling_tokens(
        tenant_id=first_tenant_id,
        access_token=access_token,
        refresh_token="refresh-one",
        db=db_session,
    )

    try:
        save_bling_tokens(
            tenant_id=uuid4(),
            access_token=access_token,
            refresh_token="refresh-two",
            db=db_session,
        )
    except ValueError as exc:
        assert "outro tenant" in str(exc)
    else:  # pragma: no cover - assertion guard
        raise AssertionError("A mesma empresa Bling foi vinculada a dois tenants")


def test_stock_deposit_is_persisted_per_tenant(db_session, monkeypatch):
    monkeypatch.setenv("PAYMENT_CONFIG_ENCRYPTION_KEY", "bling-test-master-key")
    monkeypatch.setattr(
        "app.services.bling_connection_service.SessionLocal", lambda: db_session
    )
    tenant_id = uuid4()
    save_bling_tokens(
        tenant_id=tenant_id,
        access_token=_jwt_with_company("company-deposit"),
        refresh_token="refresh-deposit",
        db=db_session,
    )

    connection = save_bling_stock_deposit_id(
        tenant_id=tenant_id,
        stock_deposit_id=14_888_055_408,
        db=db_session,
    )

    assert connection.stock_deposit_id == 14_888_055_408
    assert load_bling_credentials(tenant_id)["stock_deposit_id"] == 14_888_055_408
