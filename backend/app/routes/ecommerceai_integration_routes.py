"""API da integracao bidirecional entre CorePet e EcommerceAI."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse
from uuid import UUID, uuid4

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.config import settings
from app.db import get_session
from app.ecommerceai_integration_models import (
    EcommerceAIConnection,
    EcommerceAIConnectionRequest,
    EcommerceAIInboundEvent,
)
from app.models import Tenant, User
from app.produtos_catalogo_models import Produto
from app.tenancy.context import set_current_tenant


router = APIRouter(prefix="/integracoes/ecommerceai", tags=["EcommerceAI"])
SUPPORTED_SCOPES = {"catalog:read", "events:write"}
SUPPORTED_EVENTS = {"integration.test", "company.overview.snapshot"}
SIGNATURE_TOLERANCE_SECONDS = 300


class ConnectionRequestPayload(BaseModel):
    client_id: str = Field(min_length=1, max_length=80)
    ecommerceai_user_id: str = Field(min_length=1, max_length=80)
    account_name: str | None = Field(default=None, max_length=255)
    account_email: str | None = Field(default=None, max_length=255)
    callback_url: str = Field(min_length=8, max_length=1000)
    state: str = Field(min_length=32, max_length=255)
    requested_scopes: list[str] = Field(
        default_factory=lambda: sorted(SUPPORTED_SCOPES)
    )


class InboundEventPayload(BaseModel):
    event_id: str = Field(min_length=8, max_length=80)
    event_type: str = Field(min_length=3, max_length=120)
    schema_version: str = Field(default="1.0", min_length=1, max_length=20)
    occurred_at: datetime
    payload: dict[str, Any]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _bootstrap_secret() -> str:
    secret = str(settings.ECOMMERCEAI_INTEGRATION_BOOTSTRAP_SECRET or "").strip()
    if len(secret) < 32:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Integracao EcommerceAI ainda nao foi configurada no servidor CorePet.",
        )
    return secret


def _signature(secret: str, timestamp: str, nonce: str, body: bytes) -> str:
    body_hash = hashlib.sha256(body).hexdigest()
    message = f"{timestamp}.{nonce}.{body_hash}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def _verify_signature(
    body: bytes,
    *,
    timestamp_value: str | None,
    nonce: str | None,
    provided_signature: str | None,
) -> str:
    if not timestamp_value or not nonce or not provided_signature:
        raise HTTPException(status_code=401, detail="Assinatura da integracao ausente.")
    try:
        signed_at = int(timestamp_value)
    except ValueError as exc:
        raise HTTPException(
            status_code=401, detail="Timestamp da assinatura invalido."
        ) from exc
    if abs(int(time.time()) - signed_at) > SIGNATURE_TOLERANCE_SECONDS:
        raise HTTPException(
            status_code=401, detail="Assinatura da integracao expirada."
        )
    expected = _signature(_bootstrap_secret(), timestamp_value, nonce, body)
    if not hmac.compare_digest(expected, provided_signature.strip().lower()):
        raise HTTPException(
            status_code=401, detail="Assinatura da integracao invalida."
        )
    return nonce


def _allowed_callback_url(callback_url: str) -> bool:
    parsed = urlparse(callback_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    origin = f"{parsed.scheme}://{parsed.netloc}".lower().rstrip("/")
    allowed = {
        item.strip().lower().rstrip("/")
        for item in str(settings.ECOMMERCEAI_CALLBACK_ALLOWED_ORIGINS or "").split(",")
        if item.strip()
    }
    strict_environment = str(settings.ENVIRONMENT or "").lower() in {
        "production",
        "prod",
        "staging",
    }
    if strict_environment and parsed.scheme != "https":
        return False
    return origin in allowed


def _signed_headers(body: bytes) -> dict[str, str]:
    timestamp_value = str(int(time.time()))
    nonce = secrets.token_urlsafe(24)
    return {
        "Content-Type": "application/json",
        "X-Integration-Timestamp": timestamp_value,
        "X-Integration-Nonce": nonce,
        "X-Integration-Signature": _signature(
            _bootstrap_secret(), timestamp_value, nonce, body
        ),
    }


def _connection_for_token(
    db: Session, authorization: str | None
) -> EcommerceAIConnection:
    scheme, _, raw_token = str(authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not raw_token.startswith("cp_eai_"):
        raise HTTPException(
            status_code=401, detail="Token da integracao ausente ou invalido."
        )
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    connection = (
        db.query(EcommerceAIConnection)
        .filter(
            EcommerceAIConnection.token_hash == token_hash,
            EcommerceAIConnection.status == "connected",
            EcommerceAIConnection.revoked_at.is_(None),
        )
        .first()
    )
    if not connection:
        raise HTTPException(
            status_code=401, detail="Conexao EcommerceAI invalida ou revogada."
        )
    set_current_tenant(UUID(str(connection.tenant_id)))
    return connection


def _require_scope(connection: EcommerceAIConnection, scope: str) -> None:
    if scope not in set(connection.scopes or []):
        raise HTTPException(status_code=403, detail=f"Conexao sem o escopo {scope}.")


def _serialize_columns(instance: Any) -> dict[str, Any]:
    if instance is None:
        return {}
    excluded = {"tenant_id", "user_id", "deleted_at"}
    result = {
        column.name: getattr(instance, column.name)
        for column in instance.__table__.columns
        if column.name not in excluded
    }
    return jsonable_encoder(result)


def _serialize_product(product: Produto, *, include_related: bool) -> dict[str, Any]:
    data = _serialize_columns(product)
    data["corepet_id"] = product.id
    data["sku"] = product.codigo
    data["categoria_nome"] = getattr(product.categoria, "nome", None)
    data["marca_nome"] = getattr(product.marca, "nome", None)
    data["departamento_nome"] = getattr(product.departamento, "nome", None)
    data["fornecedor_nome"] = getattr(product.fornecedor, "nome", None)
    if include_related:
        data["imagens"] = [_serialize_columns(item) for item in product.imagens]
        data["lotes"] = [_serialize_columns(item) for item in product.lotes]
        data["componentes_kit"] = [
            _serialize_columns(item) for item in getattr(product, "componentes_kit", [])
        ]
        data["fornecedores_alternativos"] = [
            {
                **_serialize_columns(item),
                "fornecedor_nome": getattr(
                    getattr(item, "fornecedor", None), "nome", None
                ),
            }
            for item in product.fornecedores_alternativos
        ]
        data["listas_preco"] = [
            _serialize_columns(item) for item in product.listas_preco
        ]
    return data


def _request_view(item: EcommerceAIConnectionRequest | None) -> dict[str, Any] | None:
    if not item:
        return None
    return {
        "request_id": item.request_id,
        "ecommerceai_user_id": item.ecommerceai_user_id,
        "account_name": item.account_name,
        "account_email": item.account_email,
        "requested_scopes": item.requested_scopes or [],
        "status": item.status,
        "expires_at": item.expires_at,
        "created_at": item.created_at,
        "callback_error": item.callback_error,
    }


def _connection_view(item: EcommerceAIConnection | None) -> dict[str, Any] | None:
    if not item:
        return None
    return {
        "connection_id": item.public_id,
        "ecommerceai_user_id": item.ecommerceai_user_id,
        "account_name": item.account_name,
        "account_email": item.account_email,
        "status": item.status,
        "scopes": item.scopes or [],
        "connected_at": item.connected_at,
        "last_event_at": item.last_event_at,
        "last_catalog_read_at": item.last_catalog_read_at,
        "last_error": item.last_error,
    }


@router.post("/requests", status_code=status.HTTP_201_CREATED)
async def create_connection_request(
    request: Request,
    db: Session = Depends(get_session),
    x_integration_timestamp: str | None = Header(
        default=None, alias="X-Integration-Timestamp"
    ),
    x_integration_nonce: str | None = Header(default=None, alias="X-Integration-Nonce"),
    x_integration_signature: str | None = Header(
        default=None, alias="X-Integration-Signature"
    ),
):
    body = await request.body()
    nonce = _verify_signature(
        body,
        timestamp_value=x_integration_timestamp,
        nonce=x_integration_nonce,
        provided_signature=x_integration_signature,
    )
    try:
        payload = ConnectionRequestPayload.model_validate_json(body)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
    if payload.client_id != settings.ECOMMERCEAI_INTEGRATION_CLIENT_ID:
        raise HTTPException(
            status_code=403, detail="Cliente da integracao nao autorizado."
        )
    if not _allowed_callback_url(payload.callback_url):
        raise HTTPException(
            status_code=400, detail="Callback do EcommerceAI nao autorizado."
        )
    invalid_scopes = set(payload.requested_scopes) - SUPPORTED_SCOPES
    if invalid_scopes:
        raise HTTPException(
            status_code=400,
            detail=f"Escopos nao suportados: {', '.join(sorted(invalid_scopes))}",
        )
    if (
        db.query(EcommerceAIConnectionRequest)
        .filter(EcommerceAIConnectionRequest.request_nonce == nonce)
        .first()
    ):
        raise HTTPException(status_code=409, detail="Requisicao de conexao repetida.")

    request_id = str(uuid4())
    ttl_minutes = max(5, int(settings.ECOMMERCEAI_CONNECTION_REQUEST_TTL_MINUTES))
    item = EcommerceAIConnectionRequest(
        request_id=request_id,
        request_nonce=nonce,
        client_id=payload.client_id,
        ecommerceai_user_id=payload.ecommerceai_user_id,
        account_name=payload.account_name,
        account_email=payload.account_email,
        callback_url=payload.callback_url,
        state=payload.state,
        requested_scopes=sorted(set(payload.requested_scopes)),
        status="pending",
        expires_at=_utcnow() + timedelta(minutes=ttl_minutes),
    )
    db.add(item)
    db.commit()
    approval_url = (
        f"{str(settings.COREPET_FRONTEND_URL).rstrip('/')}"
        f"/configuracoes/integracoes?ecommerceai_request={request_id}"
    )
    return {
        "request_id": request_id,
        "status": "pending",
        "approval_url": approval_url,
        "expires_at": item.expires_at,
    }


@router.get("/status")
def integration_status(
    request_id: str | None = Query(default=None, max_length=36),
    user_and_tenant: tuple[User, UUID] = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    _user, tenant_id = user_and_tenant
    connection = (
        db.query(EcommerceAIConnection)
        .filter(EcommerceAIConnection.tenant_id == tenant_id)
        .order_by(EcommerceAIConnection.created_at.desc())
        .first()
    )
    pending_request = None
    if request_id:
        candidate = (
            db.query(EcommerceAIConnectionRequest)
            .filter(EcommerceAIConnectionRequest.request_id == request_id)
            .first()
        )
        if candidate and candidate.tenant_id not in {None, tenant_id}:
            raise HTTPException(
                status_code=403, detail="Solicitacao pertence a outra empresa."
            )
        pending_request = candidate

    events = (
        db.query(EcommerceAIInboundEvent)
        .filter(EcommerceAIInboundEvent.tenant_id == tenant_id)
        .order_by(EcommerceAIInboundEvent.received_at.desc())
        .limit(20)
        .all()
    )
    latest_overview = next(
        (event for event in events if event.event_type == "company.overview.snapshot"),
        None,
    )
    return {
        "connected": bool(connection and connection.status == "connected"),
        "connection": _connection_view(connection),
        "request": _request_view(pending_request),
        "latest_overview": (
            latest_overview.processed_result if latest_overview else None
        ),
        "events": [
            {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "status": event.status,
                "occurred_at": event.occurred_at,
                "received_at": event.received_at,
                "processed_result": event.processed_result,
                "error_message": event.error_message,
            }
            for event in events
        ],
    }


@router.post("/requests/{request_id}/approve")
def approve_connection_request(
    request_id: str,
    user_and_tenant: tuple[User, UUID] = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    current_user, tenant_id = user_and_tenant
    item = (
        db.query(EcommerceAIConnectionRequest)
        .filter(EcommerceAIConnectionRequest.request_id == request_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Solicitacao nao encontrada.")
    if item.tenant_id not in {None, tenant_id}:
        raise HTTPException(
            status_code=403, detail="Solicitacao pertence a outra empresa."
        )
    if _aware(item.expires_at) < _utcnow():
        item.status = "expired"
        db.commit()
        raise HTTPException(
            status_code=410, detail="Solicitacao expirada. Inicie novamente."
        )
    if item.status not in {"pending", "callback_failed"}:
        raise HTTPException(
            status_code=409, detail=f"Solicitacao ja esta {item.status}."
        )

    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()
    raw_token = f"cp_eai_{secrets.token_urlsafe(36)}"
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    scopes = sorted(set(item.requested_scopes or []) & SUPPORTED_SCOPES)

    db.query(EcommerceAIConnection).filter(
        EcommerceAIConnection.tenant_id == tenant_id,
        EcommerceAIConnection.status == "connected",
    ).update(
        {
            EcommerceAIConnection.status: "revoked",
            EcommerceAIConnection.revoked_at: _utcnow(),
        },
        synchronize_session=False,
    )
    connection = (
        db.query(EcommerceAIConnection)
        .filter(EcommerceAIConnection.request_id == request_id)
        .first()
    )
    if connection:
        connection.token_hash = token_hash
        connection.token_prefix = raw_token[:16]
        connection.status = "callback_pending"
        connection.revoked_at = None
        connection.last_error = None
        connection.tenant_id = tenant_id
        connection.scopes = scopes
    else:
        connection = EcommerceAIConnection(
            public_id=str(uuid4()),
            request_id=request_id,
            tenant_id=tenant_id,
            ecommerceai_user_id=item.ecommerceai_user_id,
            account_name=item.account_name,
            account_email=item.account_email,
            status="callback_pending",
            token_hash=token_hash,
            token_prefix=raw_token[:16],
            scopes=scopes,
        )
        db.add(connection)
    item.tenant_id = tenant_id
    item.approved_by_user_id = current_user.id
    item.approved_at = _utcnow()
    item.status = "callback_pending"
    item.callback_error = None
    db.commit()

    callback_payload = {
        "request_id": item.request_id,
        "state": item.state,
        "connection_id": connection.public_id,
        "corepet_tenant_id": str(tenant_id),
        "corepet_tenant_name": tenant.name if tenant else None,
        "access_token": raw_token,
        "scopes": scopes,
        "events_url": f"{str(settings.COREPET_PUBLIC_API_URL).rstrip('/')}/integracoes/ecommerceai/events",
        "products_url": f"{str(settings.COREPET_PUBLIC_API_URL).rstrip('/')}/integracoes/ecommerceai/catalog/products",
    }
    body = json.dumps(
        callback_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    try:
        response = httpx.post(
            item.callback_url, content=body, headers=_signed_headers(body), timeout=15
        )
        response.raise_for_status()
    except (httpx.HTTPError, ValueError) as exc:
        error_message = str(exc)[:2000]
        item.status = "callback_failed"
        item.callback_error = error_message
        connection.status = "callback_failed"
        connection.last_error = error_message
        db.commit()
        raise HTTPException(
            status_code=502,
            detail="CorePet aprovou, mas o EcommerceAI nao confirmou o callback. Tente aprovar novamente.",
        ) from exc

    now = _utcnow()
    item.status = "approved"
    item.callback_error = None
    connection.status = "connected"
    connection.connected_at = now
    connection.last_error = None
    db.commit()
    return {
        "connected": True,
        "connection": _connection_view(connection),
        "message": "EcommerceAI conectado ao CorePet com sucesso.",
    }


@router.post("/requests/{request_id}/reject")
def reject_connection_request(
    request_id: str,
    user_and_tenant: tuple[User, UUID] = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    _user, tenant_id = user_and_tenant
    item = (
        db.query(EcommerceAIConnectionRequest)
        .filter(EcommerceAIConnectionRequest.request_id == request_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Solicitacao nao encontrada.")
    if item.tenant_id not in {None, tenant_id}:
        raise HTTPException(
            status_code=403, detail="Solicitacao pertence a outra empresa."
        )
    if item.status != "pending":
        raise HTTPException(status_code=409, detail="Solicitacao nao esta pendente.")
    item.status = "rejected"
    item.tenant_id = tenant_id
    item.rejected_at = _utcnow()
    db.commit()
    return {"rejected": True}


@router.post("/disconnect")
def disconnect(
    user_and_tenant: tuple[User, UUID] = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    _user, tenant_id = user_and_tenant
    connections = (
        db.query(EcommerceAIConnection)
        .filter(
            EcommerceAIConnection.tenant_id == tenant_id,
            EcommerceAIConnection.revoked_at.is_(None),
        )
        .all()
    )
    if not connections:
        raise HTTPException(
            status_code=404, detail="Integracao EcommerceAI nao encontrada."
        )
    now = _utcnow()
    for connection in connections:
        connection.status = "revoked"
        connection.revoked_at = now
    db.commit()
    return {"message": "EcommerceAI desconectado do CorePet."}


@router.post("/events", status_code=status.HTTP_202_ACCEPTED)
def receive_event(
    payload: InboundEventPayload,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_session),
):
    connection = _connection_for_token(db, authorization)
    _require_scope(connection, "events:write")
    canonical_payload = json.dumps(
        payload.payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    payload_hash = hashlib.sha256(canonical_payload).hexdigest()
    existing = (
        db.query(EcommerceAIInboundEvent)
        .filter(
            EcommerceAIInboundEvent.connection_id == connection.id,
            EcommerceAIInboundEvent.event_id == payload.event_id,
        )
        .first()
    )
    if existing:
        if existing.payload_hash != payload_hash:
            raise HTTPException(
                status_code=409,
                detail="event_id ja utilizado com outro conteudo.",
            )
        return {
            "accepted": True,
            "duplicate": True,
            "event_id": existing.event_id,
            "status": existing.status,
        }

    now = _utcnow()
    event = EcommerceAIInboundEvent(
        tenant_id=connection.tenant_id,
        connection_id=connection.id,
        event_id=payload.event_id,
        event_type=payload.event_type,
        schema_version=payload.schema_version,
        occurred_at=payload.occurred_at,
        payload=payload.payload,
        payload_hash=payload_hash,
        status="received",
    )
    if payload.event_type == "integration.test":
        event.status = "processed"
        event.processed_result = {
            "message": "Evento de teste recebido e processado pelo CorePet.",
            "echo": payload.payload.get("message"),
        }
        event.processed_at = now
    elif payload.event_type == "company.overview.snapshot":
        overview = payload.payload.get("overview") or {}
        consolidated = overview.get("consolidated") or {}
        period = overview.get("period") or {}
        channels = overview.get("channels") or {}
        event.status = "processed"
        event.processed_result = {
            "period": period,
            "sales_base": consolidated.get("sales_base", 0),
            "contribution_margin": consolidated.get("contribution_margin", 0),
            "contribution_margin_pct": consolidated.get("contribution_margin_pct", 0),
            "orders": consolidated.get("total_orders", 0),
            "coverage_pct": consolidated.get("coverage_pct", 0),
            "channels": channels,
            "last_updated": overview.get("last_updated"),
        }
        event.processed_at = now
    else:
        event.status = "unsupported"
        event.processed_result = {
            "message": "Evento armazenado para implementacao futura.",
            "supported_events": sorted(SUPPORTED_EVENTS),
        }
        event.processed_at = now

    db.add(event)
    connection.last_event_at = now
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(EcommerceAIInboundEvent)
            .filter(
                EcommerceAIInboundEvent.connection_id == connection.id,
                EcommerceAIInboundEvent.event_id == payload.event_id,
            )
            .first()
        )
        if not existing:
            raise
        if existing.payload_hash != payload_hash:
            raise HTTPException(
                status_code=409,
                detail="event_id ja utilizado com outro conteudo.",
            )
        return {
            "accepted": True,
            "duplicate": True,
            "event_id": existing.event_id,
            "status": existing.status,
        }
    return {
        "accepted": True,
        "duplicate": False,
        "event_id": event.event_id,
        "status": event.status,
        "processed_result": event.processed_result,
    }


@router.get("/catalog/products")
def read_catalog_products(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=200),
    updated_since: datetime | None = Query(default=None),
    include_inactive: bool = Query(default=True),
    include_related: bool = Query(default=True),
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_session),
):
    connection = _connection_for_token(db, authorization)
    _require_scope(connection, "catalog:read")
    query = db.query(Produto).filter(
        Produto.tenant_id == connection.tenant_id,
        Produto.deleted_at.is_(None),
    )
    if not include_inactive:
        query = query.filter(Produto.ativo.is_(True), Produto.situacao.is_(True))
    if updated_since:
        query = query.filter(Produto.updated_at >= updated_since)
    total = query.with_entities(func.count(Produto.id)).scalar() or 0
    products = (
        query.order_by(Produto.updated_at.asc(), Produto.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    connection.last_catalog_read_at = _utcnow()
    db.commit()
    return {
        "schema_version": "1.0",
        "page": page,
        "page_size": page_size,
        "total": int(total),
        "has_next": page * page_size < int(total),
        "products": [
            _serialize_product(product, include_related=include_related)
            for product in products
        ],
    }
