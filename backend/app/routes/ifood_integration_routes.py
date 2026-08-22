"""Configuracao, diagnostico e catalogo da integracao iFood."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user_and_tenant
from app.config import settings
from app.db import get_session
from app.ifood_integration_models import IfoodMerchantConfig
from app.integrations.ifood import (
    IfoodClient,
    IfoodClientError,
    build_catalog_preview,
)
from app.models import User
from app.produtos_catalogo_models import Produto

router = APIRouter(prefix="/integracoes/ifood", tags=["iFood"])


class IfoodConfigPayload(BaseModel):
    merchant_id: str | None = Field(default=None, max_length=36)
    active: bool = False
    catalog_source: Literal["ecommerce", "erp"] = "ecommerce"
    default_markup_percent: float = Field(default=0, ge=-50, le=300)
    stock_safety: float = Field(default=0, ge=0, le=1000000)

    @field_validator("merchant_id")
    @classmethod
    def validate_merchant_id(cls, value: str | None) -> str | None:
        normalized = str(value or "").strip()
        if not normalized:
            return None
        try:
            return str(UUID(normalized))
        except ValueError as exc:
            raise ValueError("Informe um Merchant ID valido do iFood.") from exc


class IfoodSyncPayload(BaseModel):
    operation: Literal["create", "update"] = "update"
    product_ids: list[int] | None = Field(default=None, max_length=500)
    dry_run: bool = True
    confirm_send: bool = False


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _require_admin(user: User) -> None:
    if not any(
        bool(getattr(user, flag, False))
        for flag in ("is_admin", "is_superadmin", "is_system_admin")
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Somente um administrador pode alterar a integracao do iFood.",
        )


def _credentials_configured() -> bool:
    return bool(
        str(settings.IFOOD_CLIENT_ID or "").strip()
        and str(settings.IFOOD_CLIENT_SECRET or "").strip()
    )


def _provider_http_status(exc: IfoodClientError) -> int:
    # Nunca devolver 401/403 do provedor: o frontend poderia interpretar isso
    # como expiracao da sessao do usuario CorePet. Apenas o 429 preserva sentido.
    if exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        return status.HTTP_429_TOO_MANY_REQUESTS
    return status.HTTP_502_BAD_GATEWAY


def _get_config(
    db: Session, tenant_id: UUID, *, create: bool = False
) -> IfoodMerchantConfig | None:
    config = (
        db.query(IfoodMerchantConfig)
        .filter(IfoodMerchantConfig.tenant_id == tenant_id)
        .first()
    )
    if config is None and create:
        config = IfoodMerchantConfig(
            tenant_id=tenant_id,
            active=False,
            catalog_source="ecommerce",
            default_markup_percent=0,
            stock_safety=0,
            status="draft",
        )
        db.add(config)
        db.flush()
    return config


def _config_view(config: IfoodMerchantConfig | None) -> dict[str, Any]:
    return {
        "merchant_id": config.merchant_id if config else None,
        "active": bool(config.active) if config else False,
        "catalog_source": config.catalog_source if config else "ecommerce",
        "default_markup_percent": config.default_markup_percent if config else 0,
        "stock_safety": config.stock_safety if config else 0,
        "status": config.status if config else "draft",
        "last_connection_check_at": (
            config.last_connection_check_at if config else None
        ),
        "last_catalog_sync_at": config.last_catalog_sync_at if config else None,
        "last_orders_poll_at": config.last_orders_poll_at if config else None,
        "last_orders_error": config.last_orders_error if config else None,
        "last_error": config.last_error if config else None,
    }


def _products(db: Session, product_ids: list[int] | None = None) -> list[Produto]:
    query = db.query(Produto).options(
        joinedload(Produto.categoria),
        joinedload(Produto.marca),
        joinedload(Produto.departamento),
    )
    if product_ids is not None:
        if not product_ids:
            return []
        query = query.filter(Produto.id.in_(product_ids))
    return query.order_by(Produto.id.asc()).all()


def _catalog(
    db: Session,
    config: IfoodMerchantConfig | None,
    product_ids: list[int] | None = None,
):
    return build_catalog_preview(
        _products(db, product_ids),
        source=config.catalog_source if config else "ecommerce",
        markup_percent=float(config.default_markup_percent or 0) if config else 0,
        stock_safety=float(config.stock_safety or 0) if config else 0,
        public_base_url=settings.COREPET_FRONTEND_URL,
    )


def _catalog_response(
    items: list[Any], *, limit: int, only_issues: bool = False
) -> dict[str, Any]:
    eligible = [item for item in items if item.eligible]
    rejected = [item for item in items if not item.eligible]
    selected = rejected if only_issues else items
    error_counts = Counter(error for item in rejected for error in item.errors)
    warning_counts = Counter(warning for item in items for warning in item.warnings)
    return {
        "summary": {
            "total_scanned": len(items),
            "eligible": len(eligible),
            "rejected": len(rejected),
        },
        "issues": [
            {"message": message, "count": count}
            for message, count in error_counts.most_common()
        ],
        "warnings": [
            {"message": message, "count": count}
            for message, count in warning_counts.most_common()
        ],
        "items": [item.as_dict() for item in selected[:limit]],
        "has_more": len(selected) > limit,
    }


def _client() -> IfoodClient:
    return IfoodClient(
        client_id=settings.IFOOD_CLIENT_ID,
        client_secret=settings.IFOOD_CLIENT_SECRET,
        base_url=settings.IFOOD_API_BASE_URL,
        timeout_seconds=settings.IFOOD_REQUEST_TIMEOUT_SECONDS,
    )


def _merchant_entries(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("merchants", "data"):
            if isinstance(payload.get(key), list):
                return [item for item in payload[key] if isinstance(item, dict)]
    return []


@router.get("/status")
def get_ifood_status(
    auth=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    _user, tenant_id = auth
    config = _get_config(db, tenant_id)
    items = _catalog(db, config)
    eligible = sum(1 for item in items if item.eligible)
    return {
        "configured": bool(config and config.merchant_id),
        "credentials_configured": _credentials_configured(),
        "catalog_write_enabled": bool(settings.IFOOD_CATALOG_WRITE_ENABLED),
        "order_operations_enabled": bool(settings.IFOOD_ORDER_OPERATIONS_ENABLED),
        "order_polling_enabled": bool(settings.IFOOD_ORDER_POLLING_ENABLED),
        "config": _config_view(config),
        "catalog": {
            "total_scanned": len(items),
            "eligible": eligible,
            "rejected": len(items) - eligible,
        },
    }


@router.put("/config")
def save_ifood_config(
    body: IfoodConfigPayload,
    auth=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    current_user, tenant_id = auth
    _require_admin(current_user)
    if body.active and not body.merchant_id:
        raise HTTPException(
            status_code=422,
            detail="Informe o Merchant ID antes de ativar a integracao.",
        )
    config = _get_config(db, tenant_id, create=True)
    assert config is not None
    config.merchant_id = body.merchant_id
    config.active = body.active
    config.catalog_source = body.catalog_source
    config.default_markup_percent = body.default_markup_percent
    config.stock_safety = body.stock_safety
    config.status = "ready" if body.merchant_id else "draft"
    config.last_error = None
    db.commit()
    db.refresh(config)
    return {"config": _config_view(config)}


@router.get("/catalogo/preview")
def preview_ifood_catalog(
    limit: int = Query(default=50, ge=1, le=200),
    only_issues: bool = Query(default=False),
    auth=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    _user, tenant_id = auth
    config = _get_config(db, tenant_id)
    return _catalog_response(_catalog(db, config), limit=limit, only_issues=only_issues)


@router.post("/testar-conexao")
def test_ifood_connection(
    auth=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    current_user, tenant_id = auth
    _require_admin(current_user)
    config = _get_config(db, tenant_id, create=True)
    assert config is not None
    if not config.merchant_id:
        raise HTTPException(status_code=422, detail="Informe primeiro o Merchant ID.")
    try:
        with _client() as client:
            response = client.list_merchants()
        merchants = _merchant_entries(response)
        allowed_ids = {
            str(item.get("id") or item.get("merchantId") or "").strip()
            for item in merchants
        }
        if config.merchant_id not in allowed_ids:
            raise IfoodClientError(
                "O Merchant ID informado nao esta vinculado ao aplicativo CorePet."
            )
        config.status = "connected"
        config.last_connection_check_at = _utcnow()
        config.last_error = None
        db.commit()
        return {
            "connected": True,
            "merchant_id": config.merchant_id,
            "accessible_merchants": len(merchants),
        }
    except IfoodClientError as exc:
        config.status = "error"
        config.last_connection_check_at = _utcnow()
        config.last_error = str(exc)
        db.commit()
        raise HTTPException(
            status_code=_provider_http_status(exc),
            detail=str(exc),
        ) from exc


@router.post("/catalogo/sincronizar")
def sync_ifood_catalog(
    body: IfoodSyncPayload,
    auth=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    current_user, tenant_id = auth
    _require_admin(current_user)
    config = _get_config(db, tenant_id)
    items = _catalog(db, config, body.product_ids)
    eligible = [item for item in items if item.eligible and item.payload]
    preview = _catalog_response(items, limit=200)
    if body.dry_run:
        return {"dry_run": True, "operation": body.operation, **preview}

    if not settings.IFOOD_CATALOG_WRITE_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Envios reais estao bloqueados ate concluir a homologacao do iFood.",
        )
    if not body.confirm_send:
        raise HTTPException(
            status_code=422,
            detail="Confirme explicitamente o envio real do catalogo.",
        )
    if not config or not config.active or not config.merchant_id:
        raise HTTPException(
            status_code=409,
            detail="Ative a integracao e informe o Merchant ID antes de enviar.",
        )
    if not _credentials_configured():
        raise HTTPException(
            status_code=503,
            detail="Credenciais do aplicativo iFood nao configuradas no servidor.",
        )
    if len(eligible) > 200:
        raise HTTPException(
            status_code=422,
            detail="Selecione no maximo 200 produtos por envio para respeitar a volumetria do iFood.",
        )
    payloads = [item.payload for item in eligible if item.payload]
    if not payloads:
        raise HTTPException(
            status_code=422,
            detail="Nenhum produto elegivel foi selecionado para o envio.",
        )
    if body.operation == "update":
        payloads = [
            {
                "barcode": payload["barcode"],
                "name": payload["name"],
                "inventory": payload["inventory"],
                "details": payload["details"],
                "prices": payload["prices"],
                "channels": payload["channels"],
            }
            for payload in payloads
        ]
    try:
        with _client() as client:
            result = client.ingest_items(
                config.merchant_id,
                payloads,
                method="POST" if body.operation == "create" else "PATCH",
            )
        config.status = "connected"
        config.last_catalog_sync_at = _utcnow()
        config.last_error = None
        db.commit()
        return {
            "dry_run": False,
            "operation": body.operation,
            "sent": len(payloads),
            "rejected": len(items) - len(eligible),
            **result,
        }
    except IfoodClientError as exc:
        config.status = "error"
        config.last_error = str(exc)
        db.commit()
        raise HTTPException(
            status_code=_provider_http_status(exc),
            detail=str(exc),
        ) from exc
