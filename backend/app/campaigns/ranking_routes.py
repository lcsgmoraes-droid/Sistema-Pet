"""Rotas de ranking, horarios e CRUD customizado de campanhas."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func as sqlfunc
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.campaigns.models import (
    Campaign,
    CampaignStatusEnum,
    CampaignTypeEnum,
    CustomerRankHistory,
    RankLevelEnum,
)
from app.db import SessionLocal
from app.models import Cliente


router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class RankingConfigBody(BaseModel):
    silver_min_spent: float = 300
    silver_min_purchases: int = 4
    silver_min_months: int = 2
    gold_min_spent: float = 1000
    gold_min_purchases: int = 10
    gold_min_months: int = 4
    diamond_min_spent: float = 3000
    diamond_min_purchases: int = 20
    diamond_min_months: int = 6
    platinum_min_spent: float = 8000
    platinum_min_purchases: int = 40
    platinum_min_months: int = 10


class SchedulerConfigBody(BaseModel):
    birthday_send_hour: int = 8
    inactivity_send_hour: int = 9
    inactivity_day_of_week: str = "mon"
    ranking_send_day: int = 1
    ranking_send_hour: int = 6
    auto_destaque_mensal: bool = False
    auto_destaque_coupon_value: float = 50.0
    auto_destaque_coupon_days: int = 10


class CriarCampanhaBody(BaseModel):
    name: str
    campaign_type: str
    params: Optional[dict] = None
    priority: Optional[int] = 50


@router.get("/ranking")
def listar_ranking(
    nivel: Optional[str] = Query(
        None, description="bronze | silver | gold | diamond | platinum"
    ),
    periodo: Optional[str] = Query(
        None, description="Periodo YYYY-MM (padrao: mais recente)"
    ),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista clientes com seu nivel de ranking atual."""
    _, tenant_id = user_and_tenant

    if not periodo:
        ultimo = (
            db.query(CustomerRankHistory.period)
            .filter(CustomerRankHistory.tenant_id == tenant_id)
            .order_by(CustomerRankHistory.period.desc())
            .first()
        )
        if not ultimo:
            return {"periodo": None, "distribuicao": {}, "clientes": []}
        periodo = ultimo[0]

    query = db.query(CustomerRankHistory).filter(
        CustomerRankHistory.tenant_id == tenant_id,
        CustomerRankHistory.period == periodo,
    )
    if nivel:
        try:
            query = query.filter(CustomerRankHistory.rank_level == RankLevelEnum(nivel))
        except ValueError as exc:
            raise HTTPException(
                status_code=400, detail=f"Nivel invalido: {nivel}"
            ) from exc

    registros = (
        query.order_by(CustomerRankHistory.total_spent.desc()).limit(limit).all()
    )

    customer_ids = [registro.customer_id for registro in registros]
    clientes_map = {}
    if customer_ids:
        clientes = (
            db.query(Cliente)
            .filter(
                Cliente.id.in_(customer_ids),
                Cliente.tenant_id == tenant_id,
            )
            .all()
        )
        clientes_map = {
            cliente.id: {
                "nome": cliente.nome,
                "telefone": getattr(cliente, "telefone", None),
            }
            for cliente in clientes
        }

    distribuicao_query = (
        db.query(CustomerRankHistory.rank_level, sqlfunc.count())
        .filter(
            CustomerRankHistory.tenant_id == tenant_id,
            CustomerRankHistory.period == periodo,
        )
        .group_by(CustomerRankHistory.rank_level)
        .all()
    )
    distribuicao = {rank.value: total for rank, total in distribuicao_query}

    return {
        "periodo": periodo,
        "distribuicao": distribuicao,
        "clientes": [
            {
                "customer_id": registro.customer_id,
                "nome": clientes_map.get(registro.customer_id, {}).get(
                    "nome", f"Cliente #{registro.customer_id}"
                ),
                "telefone": clientes_map.get(registro.customer_id, {}).get("telefone"),
                "rank_level": registro.rank_level.value,
                "total_spent": float(registro.total_spent),
                "total_purchases": registro.total_purchases,
                "active_months": registro.active_months,
                "period": registro.period,
            }
            for registro in registros
        ],
    }


@router.get("/ranking/config")
def get_ranking_config(
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Retorna os criterios de ranking configurados para o tenant."""
    _, tenant_id = user_and_tenant
    campanha = (
        db.query(Campaign)
        .filter(
            Campaign.tenant_id == tenant_id,
            Campaign.campaign_type == CampaignTypeEnum.ranking_monthly,
        )
        .first()
    )
    params = campanha.params if campanha else {}
    defaults = RankingConfigBody().model_dump()
    return {key: params.get(key, value) for key, value in defaults.items()}


@router.put("/ranking/config")
def salvar_ranking_config(
    body: RankingConfigBody,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Salva os criterios de ranking no tenant."""
    _, tenant_id = user_and_tenant
    campanha = (
        db.query(Campaign)
        .filter(
            Campaign.tenant_id == tenant_id,
            Campaign.campaign_type == CampaignTypeEnum.ranking_monthly,
        )
        .first()
    )
    if not campanha:
        raise HTTPException(
            status_code=404,
            detail="Campanha de ranking nao encontrada. Execute o seed primeiro.",
        )
    campanha.params = {**(campanha.params or {}), **body.model_dump()}
    db.commit()
    return {"ok": True, "params": campanha.params}


@router.get("/config/horarios")
def get_scheduler_config(
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Retorna as configuracoes de horario do scheduler para o tenant."""
    _, tenant_id = user_and_tenant
    campanha = (
        db.query(Campaign)
        .filter(
            Campaign.tenant_id == tenant_id,
            Campaign.campaign_type == CampaignTypeEnum.birthday_customer,
        )
        .first()
    )
    params = campanha.params if campanha else {}
    defaults = SchedulerConfigBody().model_dump()
    return {key: params.get(key, value) for key, value in defaults.items()}


@router.put("/config/horarios")
def salvar_scheduler_config(
    body: SchedulerConfigBody,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Salva as configuracoes de horario do scheduler para o tenant."""
    _, tenant_id = user_and_tenant
    campanha = (
        db.query(Campaign)
        .filter(
            Campaign.tenant_id == tenant_id,
            Campaign.campaign_type == CampaignTypeEnum.birthday_customer,
        )
        .first()
    )
    if not campanha:
        raise HTTPException(
            status_code=404,
            detail="Campanha de aniversario nao encontrada. Execute o seed primeiro.",
        )
    campanha.params = {**(campanha.params or {}), **body.model_dump()}

    ranking_camp = (
        db.query(Campaign)
        .filter(
            Campaign.tenant_id == tenant_id,
            Campaign.campaign_type == CampaignTypeEnum.ranking_monthly,
        )
        .first()
    )
    if ranking_camp:
        ranking_camp.params = {
            **(ranking_camp.params or {}),
            "auto_destaque_mensal": body.auto_destaque_mensal,
            "auto_destaque_coupon_value": body.auto_destaque_coupon_value,
            "auto_destaque_coupon_days": body.auto_destaque_coupon_days,
        }

    db.commit()
    return {"ok": True, "params": campanha.params}


@router.post("/ranking/recalcular")
def recalcular_ranking(
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Enfileira recalculo imediato do ranking de todos os clientes do tenant."""
    _, tenant_id = user_and_tenant

    from app.campaigns.models import CampaignEventQueue, EventOriginEnum

    evento = CampaignEventQueue(
        tenant_id=tenant_id,
        event_type="monthly_ranking_recalc",
        event_origin=EventOriginEnum.user_action,
        event_depth=0,
        payload={
            "triggered_by": "manual",
            "triggered_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    db.add(evento)
    db.commit()

    return {
        "ok": True,
        "message": "Recalculo de ranking enfileirado. O worker processara em ate 10 segundos.",
    }


_USER_CREATABLE_TYPES = {
    CampaignTypeEnum.inactivity,
    CampaignTypeEnum.quick_repurchase,
    CampaignTypeEnum.bulk_segment,
}


@router.post("/campanhas", status_code=201)
def criar_campanha(
    body: CriarCampanhaBody,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Cria uma nova campanha personalizada."""
    _, tenant_id = user_and_tenant

    try:
        tipo = CampaignTypeEnum(body.campaign_type)
    except ValueError as exc:
        raise HTTPException(
            400, detail=f"Tipo de campanha invalido: {body.campaign_type}"
        ) from exc

    if tipo not in _USER_CREATABLE_TYPES:
        raise HTTPException(
            400,
            detail=f"Tipo '{body.campaign_type}' e gerenciado automaticamente e nao pode ser criado manualmente.",
        )

    campaign = Campaign(
        tenant_id=tenant_id,
        name=body.name.strip(),
        campaign_type=tipo,
        status=CampaignStatusEnum.active,
        priority=max(0, min(999, body.priority or 50)),
        params=body.params or {},
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    return {
        "id": campaign.id,
        "name": campaign.name,
        "campaign_type": campaign.campaign_type,
        "status": campaign.status,
        "priority": campaign.priority,
        "params": campaign.params,
    }


@router.delete("/campanhas/{campaign_id}", status_code=204)
def deletar_campanha(
    campaign_id: int,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Arquiva uma campanha personalizada."""
    _, tenant_id = user_and_tenant

    campaign = (
        db.query(Campaign)
        .filter(Campaign.id == campaign_id, Campaign.tenant_id == tenant_id)
        .first()
    )
    if not campaign:
        raise HTTPException(404, detail="Campanha nao encontrada.")

    if campaign.campaign_type not in _USER_CREATABLE_TYPES:
        raise HTTPException(
            400,
            detail="Campanha do sistema nao pode ser removida manualmente.",
        )

    campaign.status = CampaignStatusEnum.archived
    db.commit()
    return
