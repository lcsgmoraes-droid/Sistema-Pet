"""Onboarding assistido de ops — cadastro negociado "1 -> N": a equipe
interna cria, de uma vez, todas as lojas de um cliente novo dentro de um
unico grupo comercial. Ferramenta administrativa; o cliente final nunca
acessa esta rota (ver `grupo_comercial_routes.py` para o "adicionar loja"
self-service, usado pelo proprio titular ja logado).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.db import get_session
from app.platform_auth import require_platform_admin
from app.platform_auth_models import PlatformAdmin
from app.services.ops_grupo_comercial_onboarding_service import (
    OpsGrupoComercialOnboardingError,
    OpsLojaOnboarding,
    adicionar_loja_a_grupo_existente,
    onboard_grupo_comercial,
)

router = APIRouter(prefix="/admin/grupos-comerciais", tags=["Admin - Grupos Comerciais"])


class OpsLojaOnboardingRequest(BaseModel):
    nome_loja: str = Field(min_length=2, max_length=150)
    nome_acesso: str | None = Field(default=None, max_length=150)
    plan: str | None = None
    organization_type: str | None = None


class OpsGrupoComercialOnboardingRequest(BaseModel):
    titular_email: EmailStr
    titular_nome: str | None = Field(default=None, max_length=160)
    lojas: list[OpsLojaOnboardingRequest] = Field(min_length=1, max_length=50)


@router.post("/onboarding")
def onboarding_assistido_grupo_comercial(
    payload: OpsGrupoComercialOnboardingRequest,
    request: Request,
    _current_admin: PlatformAdmin = Depends(require_platform_admin),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    lojas = [
        OpsLojaOnboarding(
            nome_loja=loja.nome_loja,
            nome_acesso=loja.nome_acesso,
            plan=loja.plan,
            organization_type=loja.organization_type,
        )
        for loja in payload.lojas
    ]
    try:
        resultado = onboard_grupo_comercial(
            db,
            request=request,
            titular_email=payload.titular_email,
            titular_nome=payload.titular_nome,
            lojas=lojas,
        )
    except OpsGrupoComercialOnboardingError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    return {
        "grupo_id": resultado.grupo_id,
        "titular_email": resultado.titular_email,
        "lojas": resultado.lojas,
    }


@router.post("/{grupo_id}/lojas")
def adicionar_loja_ops(
    grupo_id: int,
    payload: OpsLojaOnboardingRequest,
    _current_admin: PlatformAdmin = Depends(require_platform_admin),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    loja = OpsLojaOnboarding(
        nome_loja=payload.nome_loja,
        nome_acesso=payload.nome_acesso,
        plan=payload.plan,
        organization_type=payload.organization_type,
    )
    try:
        return adicionar_loja_a_grupo_existente(db, grupo_id=grupo_id, loja=loja)
    except OpsGrupoComercialOnboardingError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
