from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.db import get_session
from app.models import User
from app.services.ops_tenants_service import (
    OpsTenantActionError,
    apply_base_catalog_import,
    list_ops_tenants,
    preview_base_catalog_import,
)


router = APIRouter(prefix="/admin/tenants", tags=["Admin - Tenants"])


class CatalogImportApplyRequest(BaseModel):
    confirm: bool = False


@router.get("")
def listar_tenants_ops(
    search: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(100, ge=1, le=300),
    _current_user: User = Depends(require_admin),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    return list_ops_tenants(db, search=search, status=status, limit=limit)


@router.post("/{tenant_id}/catalog-import/preview")
def simular_importacao_catalogo_base(
    tenant_id: str,
    _current_user: User = Depends(require_admin),
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
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    try:
        result = apply_base_catalog_import(
            db,
            tenant_id=tenant_id,
            actor_user_id=int(current_user.id),
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
