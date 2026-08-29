"""Persistencia criptografada e resolucao de tenant para o Bling."""

from __future__ import annotations

import base64
import json
from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.bling_connection_models import BlingCompanyTenantLink, BlingConnection
from app.db import SessionLocal
from app.tenancy.context import get_current_tenant, tenant_context


def _tenant_uuid(value: Any) -> UUID | None:
    try:
        return UUID(str(value)) if value else None
    except (TypeError, ValueError):
        return None


def extract_bling_company_id(access_token: str | None) -> str | None:
    """Le o companyId do JWT emitido pelo Bling sem expor o token."""
    raw = str(access_token or "").strip()
    parts = raw.split(".")
    if len(parts) != 3:
        return None
    try:
        payload_part = parts[1] + "=" * (-len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_part).decode("utf-8"))
    except (ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError):
        return None

    def find_company_id(value: Any) -> str | None:
        if isinstance(value, dict):
            for key, candidate in value.items():
                normalized_key = str(key).replace("_", "").lower()
                if normalized_key in {"companyid", "empresaid"}:
                    company_id = str(candidate or "").strip()
                    if company_id:
                        return company_id[:100]
                if normalized_key in {"company", "empresa"} and isinstance(
                    candidate, dict
                ):
                    company_id = str(candidate.get("id") or "").strip()
                    if company_id:
                        return company_id[:100]
            for candidate in value.values():
                company_id = find_company_id(candidate)
                if company_id:
                    return company_id
        elif isinstance(value, list):
            for candidate in value:
                company_id = find_company_id(candidate)
                if company_id:
                    return company_id
        return None

    return find_company_id(payload)


def get_bling_connection(
    tenant_id: UUID | str | None = None,
    *,
    db: Session | None = None,
) -> BlingConnection | None:
    resolved_tenant = _tenant_uuid(tenant_id) or get_current_tenant()
    if not resolved_tenant:
        return None

    owns_session = db is None
    session = db or SessionLocal()
    context = (
        nullcontext(resolved_tenant)
        if get_current_tenant() == resolved_tenant
        else tenant_context(resolved_tenant)
    )
    try:
        with context:
            return (
                session.query(BlingConnection)
                .filter(
                    BlingConnection.tenant_id == resolved_tenant,
                    BlingConnection.status == "active",
                )
                .first()
            )
    finally:
        if owns_session:
            session.close()


def load_bling_credentials(
    tenant_id: UUID | str | None = None,
) -> dict[str, Any] | None:
    connection = get_bling_connection(tenant_id)
    if not connection:
        return None
    access_token = connection.access_token
    refresh_token = connection.refresh_token
    if not access_token or not refresh_token:
        return None
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "company_id": connection.company_id,
        "expires_at": connection.expires_at,
        "last_refresh_at": connection.last_refresh_at,
        "renewal_count": int(connection.renewal_count or 0),
        "source": "tenant",
    }


def save_bling_tokens(
    *,
    tenant_id: UUID | str,
    access_token: str,
    refresh_token: str,
    expires_in: int = 21600,
    increment_renewal: bool = False,
    db: Session | None = None,
) -> BlingConnection:
    resolved_tenant = _tenant_uuid(tenant_id)
    if not resolved_tenant:
        raise ValueError("Tenant invalido para salvar a conexao Bling")
    if not str(access_token or "").strip() or not str(refresh_token or "").strip():
        raise ValueError("Tokens do Bling ausentes")

    owns_session = db is None
    session = db or SessionLocal()
    context = (
        nullcontext(resolved_tenant)
        if get_current_tenant() == resolved_tenant
        else tenant_context(resolved_tenant)
    )
    try:
        with context:
            connection = (
                session.query(BlingConnection)
                .filter(BlingConnection.tenant_id == resolved_tenant)
                .first()
            )
            now = datetime.now(timezone.utc)
            if not connection:
                connection = BlingConnection(tenant_id=resolved_tenant)
                session.add(connection)

            previous_company_id = str(connection.company_id or "").strip() or None
            company_id = extract_bling_company_id(access_token) or previous_company_id
            connection.access_token = access_token
            connection.refresh_token = refresh_token
            connection.company_id = company_id
            connection.status = "active"
            connection.expires_at = now + timedelta(seconds=max(int(expires_in), 60))
            connection.last_error = None
            if increment_renewal:
                connection.last_refresh_at = now
                connection.renewal_count = int(connection.renewal_count or 0) + 1
            elif not connection.connected_at:
                connection.connected_at = now

            if previous_company_id and previous_company_id != company_id:
                session.query(BlingCompanyTenantLink).filter(
                    BlingCompanyTenantLink.company_id == previous_company_id,
                    BlingCompanyTenantLink.tenant_id == resolved_tenant,
                ).delete(synchronize_session=False)

            if company_id:
                conflicting_link = (
                    session.query(BlingCompanyTenantLink)
                    .filter(BlingCompanyTenantLink.company_id == company_id)
                    .first()
                )
                if conflicting_link and conflicting_link.tenant_id != resolved_tenant:
                    raise ValueError(
                        "Esta empresa do Bling ja esta vinculada a outro tenant"
                    )
                tenant_link = (
                    session.query(BlingCompanyTenantLink)
                    .filter(BlingCompanyTenantLink.tenant_id == resolved_tenant)
                    .first()
                )
                if tenant_link:
                    tenant_link.company_id = company_id
                elif not conflicting_link:
                    session.add(
                        BlingCompanyTenantLink(
                            company_id=company_id,
                            tenant_id=resolved_tenant,
                        )
                    )

            session.commit()
            session.refresh(connection)
            return connection
    except Exception:
        session.rollback()
        raise
    finally:
        if owns_session:
            session.close()


def webhook_company_id(payload: dict | None) -> str | None:
    envelope = payload if isinstance(payload, dict) else {}
    for key in ("companyId", "company_id", "empresaId"):
        value = str(envelope.get(key) or "").strip()
        if value:
            return value[:100]
    return None


def resolve_bling_webhook_tenant(
    payload: dict | None,
    *,
    db: Session | None = None,
) -> UUID | None:
    company_id = webhook_company_id(payload)
    if not company_id:
        return None
    owns_session = db is None
    session = db or SessionLocal()
    try:
        link = (
            session.query(BlingCompanyTenantLink)
            .filter(BlingCompanyTenantLink.company_id == company_id)
            .first()
        )
        return _tenant_uuid(link.tenant_id) if link else None
    finally:
        if owns_session:
            session.close()


def connected_bling_tenant_ids() -> list[UUID]:
    session = SessionLocal()
    try:
        rows = session.query(BlingCompanyTenantLink.tenant_id).all()
        return [tenant for tenant in (_tenant_uuid(row[0]) for row in rows) if tenant]
    finally:
        session.close()
