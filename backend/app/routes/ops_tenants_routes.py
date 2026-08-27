from __future__ import annotations

from datetime import date
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Tenant
from app.platform_auth import require_platform_admin
from app.platform_auth_models import PlatformAdmin
from app.services.billing_offer_service import (
    BillingOfferError,
    create_billing_offer,
    list_billing_offers,
    offer_to_admin,
)
from app.services.ops_tenants_service import (
    OpsTenantActionError,
    apply_base_catalog_import,
    list_ops_tenants,
    preview_base_catalog_import,
    update_ops_tenant_commercial_state,
    update_ops_tenant_onboarding_follow_up,
)


router = APIRouter(prefix="/admin/tenants", tags=["Admin - Tenants"])


class CatalogImportApplyRequest(BaseModel):
    confirm: bool = False


class CommercialStateRequest(BaseModel):
    status: str | None = None
    plan: str | None = None
    billing_status: str | None = None
    subscription_source: str | None = None


class OnboardingFollowUpRequest(BaseModel):
    owner_name: str | None = Field(default=None, max_length=160)
    unblocked_on: date | None = None
    satisfaction: (
        Literal[
            "not_collected",
            "satisfied",
            "neutral",
            "dissatisfied",
        ]
        | None
    ) = None


class BillingOfferCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    plan_code: str
    price_cents: int = Field(ge=100, le=10_000_000)
    first_due_date: date
    billing_type: Literal["UNDEFINED", "PIX", "BOLETO", "CREDIT_CARD"] = "UNDEFINED"
    extra_modules: list[str] = Field(default_factory=list, max_length=20)


@router.get("")
def listar_tenants_ops(
    search: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(100, ge=1, le=300),
    _current_admin: PlatformAdmin = Depends(require_platform_admin),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    return list_ops_tenants(db, search=search, status=status, limit=limit)


@router.patch("/{tenant_id}/commercial")
def atualizar_estado_comercial_tenant(
    tenant_id: str,
    payload: CommercialStateRequest,
    _current_admin: PlatformAdmin = Depends(require_platform_admin),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    try:
        result = update_ops_tenant_commercial_state(
            db,
            tenant_id=tenant_id,
            changes=payload.model_dump(exclude_unset=True),
        )
        db.commit()
        return result
    except OpsTenantActionError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise


@router.patch("/{tenant_id}/onboarding-follow-up")
def atualizar_acompanhamento_onboarding(
    tenant_id: str,
    payload: OnboardingFollowUpRequest,
    _current_admin: PlatformAdmin = Depends(require_platform_admin),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    changes = payload.model_dump(exclude_unset=True)
    mapped_changes = {f"onboarding_{field}": value for field, value in changes.items()}
    try:
        result = update_ops_tenant_onboarding_follow_up(
            db,
            tenant_id=tenant_id,
            changes=mapped_changes,
        )
        db.commit()
        return result
    except OpsTenantActionError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise


@router.get("/{tenant_id}/billing-offers")
def listar_propostas_cobranca(
    tenant_id: str,
    limit: int = Query(10, ge=1, le=50),
    _current_admin: PlatformAdmin = Depends(require_platform_admin),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    try:
        return {
            "items": list_billing_offers(db, tenant_reference=tenant_id, limit=limit)
        }
    except BillingOfferError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("/{tenant_id}/billing-offers")
def criar_proposta_cobranca(
    tenant_id: str,
    payload: BillingOfferCreateRequest,
    current_admin: PlatformAdmin = Depends(require_platform_admin),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    try:
        offer, token = create_billing_offer(
            db,
            tenant_reference=tenant_id,
            created_by=current_admin,
            title=payload.title,
            plan_code=payload.plan_code,
            price_cents=payload.price_cents,
            first_due_date=payload.first_due_date,
            billing_type=payload.billing_type,
            extra_modules=payload.extra_modules,
        )
        db.commit()
        result = offer_to_admin(
            offer,
            db.query(Tenant).filter(Tenant.id == offer.tenant_reference).first(),
        )
        result["public_path"] = f"/contratar/{token}"
        return result
    except BillingOfferError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise


@router.post("/{tenant_id}/catalog-import/preview")
def simular_importacao_catalogo_base(
    tenant_id: str,
    _current_admin: PlatformAdmin = Depends(require_platform_admin),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    try:
        result = preview_base_catalog_import(db, tenant_id=tenant_id)
        db.rollback()
        return result
    except OpsTenantActionError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{tenant_id}/catalog-import/apply")
def aplicar_importacao_catalogo_base(
    tenant_id: str,
    payload: CatalogImportApplyRequest,
    _current_admin: PlatformAdmin = Depends(require_platform_admin),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    try:
        result = apply_base_catalog_import(
            db,
            tenant_id=tenant_id,
            confirm=bool(payload.confirm),
        )
        db.commit()
        return result
    except OpsTenantActionError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise
