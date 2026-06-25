"""Rotas de listagem e gestao das campanhas base."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.campaigns.models import Campaign, CampaignStatusEnum
from app.campaigns.routes_common import get_db


router = APIRouter()


@router.get("/health")
def campaigns_health():
    """Healthcheck do módulo de campanhas."""
    return {"status": "ok", "module": "campaigns"}


def listar_campanhas(
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista todas as campanhas ativas e pausadas do tenant."""
    _, tenant_id = user_and_tenant
    campanhas = (
        db.query(Campaign)
        .filter(
            Campaign.tenant_id == tenant_id,
            Campaign.status.in_([CampaignStatusEnum.active, CampaignStatusEnum.paused]),
        )
        .order_by(Campaign.priority)
        .all()
    )
    return [
        {
            "id": c.id,
            "name": c.name,
            "campaign_type": c.campaign_type.value,
            "status": c.status.value,
            "priority": c.priority,
            "params": c.params,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in campanhas
    ]


@router.post("/{campanha_id}/pausar")
def pausar_campanha(
    campanha_id: int,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Alterna o status da campanha entre active ↔ paused."""
    _, tenant_id = user_and_tenant
    campanha = (
        db.query(Campaign)
        .filter(Campaign.id == campanha_id, Campaign.tenant_id == tenant_id)
        .first()
    )
    if not campanha:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")

    if campanha.status == CampaignStatusEnum.active:
        campanha.status = CampaignStatusEnum.paused
        novo_status = "paused"
    else:
        campanha.status = CampaignStatusEnum.active
        novo_status = "active"

    db.commit()
    return {"id": campanha_id, "status": novo_status}


# ---------------------------------------------------------------------------
# Campanhas — atualizar parâmetros
# ---------------------------------------------------------------------------


class AtualizarParametrosBody(BaseModel):
    params: dict
    name: Optional[str] = None


@router.put("/{campanha_id}/parametros")
def atualizar_parametros(
    campanha_id: int,
    body: AtualizarParametrosBody,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Atualiza os parâmetros e/ou nome de uma campanha."""
    _, tenant_id = user_and_tenant
    campanha = (
        db.query(Campaign)
        .filter(Campaign.id == campanha_id, Campaign.tenant_id == tenant_id)
        .first()
    )
    if not campanha:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")

    campanha.params = {**(campanha.params or {}), **body.params}
    if body.name:
        campanha.name = body.name
    db.commit()
    return {
        "id": campanha.id,
        "name": campanha.name,
        "params": campanha.params,
    }


# ---------------------------------------------------------------------------
# Cupons — listagem
# ---------------------------------------------------------------------------
