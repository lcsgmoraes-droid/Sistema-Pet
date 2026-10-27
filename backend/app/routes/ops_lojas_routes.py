"""OPS: tela "Lojas e modulos" (quem e a loja, o grupo e os modulos ligados)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_session
from app.platform_auth import require_platform_admin
from app.platform_auth_models import PlatformAdmin
from app.services.ops_lojas_modulos_service import (
    OpsLojaError,
    alterar_modulo,
    listar_lojas,
)
from app.services.ops_tenant_log_service import listar_historico
from app.services.ops_whatsapp_consumo_service import consumo_do_mes

router = APIRouter(prefix="/admin/lojas", tags=["Admin - Lojas e módulos"])


@router.get("")
def listar(
    search: str | None = Query(None, max_length=100),
    _admin: PlatformAdmin = Depends(require_platform_admin),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    return listar_lojas(db, search=search)


@router.get("/consumo-whatsapp")
def consumo_whatsapp(
    mes: str | None = Query(None, description="AAAA-MM; vazio = mês atual"),
    _admin: PlatformAdmin = Depends(require_platform_admin),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    """Mensagens de WhatsApp por loja no mês, para conferir e repassar o custo da Meta."""
    try:
        return consumo_do_mes(db, mes)
    except ValueError as erro:
        raise HTTPException(status_code=422, detail=str(erro)) from erro


@router.get("/historico")
def historico_geral(
    limite: int = Query(100, ge=1, le=500),
    _admin: PlatformAdmin = Depends(require_platform_admin),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    """Ultimas alteracoes feitas pela plataforma em qualquer loja."""
    return {"items": listar_historico(db, limite=limite)}


@router.get("/{tenant_id}/historico")
def historico_da_loja(
    tenant_id: str,
    limite: int = Query(200, ge=1, le=500),
    _admin: PlatformAdmin = Depends(require_platform_admin),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    """Quem alterou o que nesta loja, quando e o valor anterior."""
    return {"items": listar_historico(db, tenant_id=tenant_id, limite=limite)}


def _alterar(
    db: Session, admin: PlatformAdmin, tenant_id: str, modulo: str, ativar: bool
) -> dict[str, Any]:
    try:
        resultado = alterar_modulo(
            db,
            tenant_id=tenant_id,
            modulo=modulo,
            ativar=ativar,
            admin=admin,
        )
        db.commit()
        return resultado
    except OpsLojaError as erro:
        db.rollback()
        raise HTTPException(status_code=erro.status_code, detail=str(erro)) from erro


@router.post("/{tenant_id}/modulos/{modulo}/ativar")
def ativar(
    tenant_id: str,
    modulo: str,
    admin: PlatformAdmin = Depends(require_platform_admin),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    return _alterar(db, admin, tenant_id, modulo, True)


@router.post("/{tenant_id}/modulos/{modulo}/desativar")
def desativar(
    tenant_id: str,
    modulo: str,
    admin: PlatformAdmin = Depends(require_platform_admin),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    return _alterar(db, admin, tenant_id, modulo, False)
