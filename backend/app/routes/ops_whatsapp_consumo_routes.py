"""OPS: consumo de WhatsApp por loja, tarifas da Meta e fechamento mensal."""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_session
from app.platform_auth import require_platform_admin
from app.platform_auth_models import PlatformAdmin
from app.services.ops_whatsapp_consumo_service import (
    ConsumoError,
    cadastrar_tarifa,
    consumo_do_mes,
    fechar_mes,
    informar_fatura,
    listar_tarifas,
)

router = APIRouter(
    prefix="/admin/whatsapp-consumo", tags=["Admin - Consumo de WhatsApp"]
)


class TarifaNova(BaseModel):
    categoria: str
    valor: float = Field(ge=0, le=100, description="Reais por mensagem")
    vigente_desde: date


class FechamentoPedido(BaseModel):
    mes: str = Field(pattern=r"^\d{4}-\d{2}$")
    margem_percentual: float = Field(default=0, ge=0, le=1000)


class FaturaInformada(BaseModel):
    fatura_meta: float = Field(ge=0)
    observacao: str | None = Field(default=None, max_length=1000)


def _executar(db: Session, acao):
    try:
        resultado = acao()
        db.commit()
        return resultado
    except ConsumoError as erro:
        db.rollback()
        raise HTTPException(status_code=erro.status_code, detail=str(erro)) from erro
    except ValueError as erro:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(erro)) from erro


@router.get("")
def consumo(
    mes: str | None = Query(None, description="AAAA-MM; vazio = mês atual"),
    _admin: PlatformAdmin = Depends(require_platform_admin),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    """Consumo de todas as lojas no mês (ao vivo), com o fechamento quando já existir."""
    try:
        return consumo_do_mes(db, mes)
    except ValueError as erro:
        raise HTTPException(status_code=422, detail=str(erro)) from erro


@router.get("/tarifas")
def tarifas(
    _admin: PlatformAdmin = Depends(require_platform_admin),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    return {"items": listar_tarifas(db)}


@router.post("/tarifas", status_code=201)
def nova_tarifa(
    dados: TarifaNova,
    admin: PlatformAdmin = Depends(require_platform_admin),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    def _cadastrar():
        cadastrar_tarifa(
            db,
            categoria=dados.categoria,
            valor=dados.valor,
            vigente_desde=dados.vigente_desde,
            admin_email=admin.email,
        )
        return {"items": listar_tarifas(db)}

    return _executar(db, _cadastrar)


@router.post("/fechar")
def fechar(
    dados: FechamentoPedido,
    admin: PlatformAdmin = Depends(require_platform_admin),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    """Fotografa o consumo do mês de cada loja (mês já fechado não muda)."""
    return _executar(
        db,
        lambda: fechar_mes(
            db, mes=dados.mes, margem_percentual=dados.margem_percentual, admin=admin
        ),
    )


@router.patch("/fechamentos/{fechamento_id}/fatura")
def fatura(
    fechamento_id: int,
    dados: FaturaInformada,
    admin: PlatformAdmin = Depends(require_platform_admin),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    """Registra a fatura real da Meta da loja e mostra a divergência com o estimado."""
    return _executar(
        db,
        lambda: informar_fatura(
            db,
            fechamento_id=fechamento_id,
            fatura_meta=dados.fatura_meta,
            observacao=dados.observacao,
            admin=admin,
        ),
    )
