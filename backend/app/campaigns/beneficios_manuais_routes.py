"""Rotas de ajustes manuais de cashback e carimbos."""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func as sqlfunc
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.campaigns.audit import build_loyalty_stamp_audit_metadata, log_campaign_event
from app.campaigns.loyalty_service import (
    build_consumed_loyalty_stamp_ids,
    get_loyalty_balance_for_campaign,
    summarize_loyalty_balances_for_customer,
)
from app.campaigns.models import (
    Campaign,
    CampaignStatusEnum,
    CashbackSourceTypeEnum,
    CashbackTransaction,
    LoyaltyStamp,
)
from app.campaigns.routes_common import (
    _current_user_id,
    _resolver_customer_id_campanhas,
    get_db,
)


logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/clientes/{customer_id}/carimbos")
def listar_carimbos_cliente(
    customer_id: int,
    incluir_estornados: bool = Query(
        False, description="Inclui carimbos já estornados"
    ),
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista todos os carimbos de um cliente (ativos e opcionalmente estornados)."""
    _, tenant_id = user_and_tenant

    q = db.query(LoyaltyStamp).filter(
        LoyaltyStamp.tenant_id == tenant_id,
        LoyaltyStamp.customer_id == customer_id,
    )
    if not incluir_estornados:
        q = q.filter(LoyaltyStamp.voided_at.is_(None))
    stamps = q.order_by(LoyaltyStamp.created_at.desc()).all()
    stamps_by_campaign: dict[int, list[LoyaltyStamp]] = {}
    for stamp in stamps:
        stamps_by_campaign.setdefault(int(stamp.campaign_id), []).append(stamp)

    converted_stamp_ids: set[int] = set()
    if stamps_by_campaign:
        campaigns = (
            db.query(Campaign)
            .filter(
                Campaign.tenant_id == tenant_id,
                Campaign.id.in_(list(stamps_by_campaign.keys())),
            )
            .all()
        )
        campaign_map = {int(c.id): c for c in campaigns}
        for campaign_id, campaign_stamps in stamps_by_campaign.items():
            campaign = campaign_map.get(campaign_id)
            if campaign is None:
                continue
            loyalty_balance = get_loyalty_balance_for_campaign(
                db,
                campaign=campaign,
                customer_id=customer_id,
            )
            converted_stamp_ids.update(
                build_consumed_loyalty_stamp_ids(
                    campaign_stamps,
                    consumed_count=loyalty_balance["converted_stamps"],
                )
            )

    return [
        {
            "id": s.id,
            "customer_id": s.customer_id,
            "venda_id": s.venda_id,
            "campaign_id": s.campaign_id,
            "is_manual": s.is_manual,
            "notes": s.notes,
            "created_at": s.created_at.isoformat(),
            "voided_at": s.voided_at.isoformat() if s.voided_at else None,
            "is_converted": s.id in converted_stamp_ids and s.voided_at is None,
            "status": (
                "estornado"
                if s.voided_at
                else "convertido"
                if s.id in converted_stamp_ids
                else "ativo"
            ),
        }
        for s in stamps
    ]


# ---------------------------------------------------------------------------
# Cashback — ajuste manual (Gestor de Benefícios)
# ---------------------------------------------------------------------------


class CashbackManualBody(BaseModel):
    customer_id: int
    amount: float  # positivo = crédito, negativo = débito
    description: str = "Ajuste manual"


@router.post("/cashback/manual")
def cashback_manual(
    body: CashbackManualBody,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Lança um ajuste manual de cashback para um cliente.
    Positivo = crédito, negativo = débito.
    Usado no Gestor de Benefícios para corригir ou ajustar saldo.
    """
    _, tenant_id = user_and_tenant
    if body.amount == 0:
        raise HTTPException(
            status_code=400, detail="O valor do ajuste não pode ser zero."
        )

    transacao = CashbackTransaction(
        tenant_id=tenant_id,
        customer_id=body.customer_id,
        amount=round(body.amount, 2),
        source_type=CashbackSourceTypeEnum.manual,
        description=body.description,
        tx_type="debit" if body.amount < 0 else "credit",
    )
    db.add(transacao)
    db.commit()
    db.refresh(transacao)

    novo_saldo = float(
        db.query(sqlfunc.sum(CashbackTransaction.amount))
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.customer_id == body.customer_id,
        )
        .scalar()
        or 0
    )

    logger.info(
        "[Campanhas] Cashback manual: customer_id=%d amount=%.2f tenant=%s novo_saldo=%.2f",
        body.customer_id,
        body.amount,
        tenant_id,
        novo_saldo,
    )
    return {
        "ok": True,
        "transaction_id": transacao.id,
        "amount": float(body.amount),
        "description": body.description,
        "novo_saldo": round(novo_saldo, 2),
    }


# ---------------------------------------------------------------------------
# Anular cupom (Sprint 9)
# ---------------------------------------------------------------------------


class LancarCarimboManualBody(BaseModel):
    customer_id: int
    venda_id: Optional[int] = None
    nota: Optional[str] = None


@router.post("/carimbos/manual")
def lancar_carimbo_manual(
    body: LancarCarimboManualBody,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Lança um carimbo manual para um cliente.

    Usado para converter cartões físicos antigos ou como ajuste operacional.
    Idempotente: se já existe um carimbo manual sem venda_id para este cliente
    na mesma hora, retorna o existente.
    """
    user, tenant_id = user_and_tenant
    customer_id = _resolver_customer_id_campanhas(
        db,
        tenant_id=tenant_id,
        customer_ref=body.customer_id,
    )

    # Buscar campanha de fidelidade ativa do tenant
    campanha = (
        db.query(Campaign)
        .filter(
            Campaign.tenant_id == tenant_id,
            Campaign.campaign_type == "loyalty_stamp",
            Campaign.status.in_([CampaignStatusEnum.active, CampaignStatusEnum.paused]),
        )
        .first()
    )
    if not campanha:
        raise HTTPException(
            status_code=404,
            detail="Nenhuma campanha de cartão fidelidade encontrada. Ative a campanha primeiro.",
        )

    stamp = LoyaltyStamp(
        tenant_id=tenant_id,
        customer_id=customer_id,
        venda_id=body.venda_id,
        campaign_id=campanha.id,
        stamp_index=1,
        is_manual=True,
        notes=body.nota or "Carimbo lançado manualmente",
    )
    db.add(stamp)
    try:
        db.flush()
    except Exception:
        db.rollback()
        # Já existe (UNIQUE constraint) — buscar o existente
        existing = (
            db.query(LoyaltyStamp)
            .filter(
                LoyaltyStamp.tenant_id == tenant_id,
                LoyaltyStamp.campaign_id == campanha.id,
                LoyaltyStamp.customer_id == customer_id,
                LoyaltyStamp.venda_id == body.venda_id,
            )
            .first()
        )
        if existing:
            saldo = summarize_loyalty_balances_for_customer(
                db,
                tenant_id=tenant_id,
                customer_id=customer_id,
            )
            return {
                "ok": True,
                "novo": False,
                "total_carimbos": saldo["total_carimbos"],
                "total_carimbos_brutos": saldo["total_carimbos_brutos"],
                "carimbos_comprometidos_total": saldo["carimbos_comprometidos_total"],
                "carimbos_em_debito": saldo["carimbos_em_debito"],
                "carimbos_convertidos": saldo["carimbos_convertidos"],
                "stamp_id": existing.id,
            }
        raise HTTPException(status_code=500, detail="Erro ao lançar carimbo")

    from app.campaigns.loyalty_service import sync_loyalty_rewards_for_customer

    sync_loyalty_rewards_for_customer(
        db,
        campaign=campanha,
        customer_id=customer_id,
        source_event_id=None,
    )

    saldo = summarize_loyalty_balances_for_customer(
        db,
        tenant_id=tenant_id,
        customer_id=customer_id,
    )
    log_campaign_event(
        db=db,
        tenant_id=tenant_id,
        user_id=_current_user_id(user),
        event="campaign.loyalty.manual_stamp_added",
        entity_type="campaign_loyalty_stamps",
        entity_id=stamp.id,
        metadata=build_loyalty_stamp_audit_metadata(
            stamp=stamp,
            campaign=campanha,
            operation="manual_added",
            balance=saldo,
        ),
        details=f"Carimbo manual #{stamp.id} lancado",
    )

    db.commit()
    db.refresh(stamp)

    logger.info(
        "[Campanhas] Carimbo manual lançado customer_id=%d tenant=%s total=%d",
        customer_id,
        tenant_id,
        saldo["total_carimbos"],
    )

    return {
        "ok": True,
        "novo": True,
        "stamp_id": stamp.id,
        "total_carimbos": saldo["total_carimbos"],
        "total_carimbos_brutos": saldo["total_carimbos_brutos"],
        "carimbos_comprometidos_total": saldo["carimbos_comprometidos_total"],
        "carimbos_em_debito": saldo["carimbos_em_debito"],
        "carimbos_convertidos": saldo["carimbos_convertidos"],
        "params": campanha.params,
        "stamps_to_complete": campanha.params.get("stamps_to_complete", 10),
    }


# ---------------------------------------------------------------------------
# Carimbos — estorno (remoção) de carimbo individual
# ---------------------------------------------------------------------------


@router.delete("/carimbos/{stamp_id}", status_code=200)
def estornar_carimbo(
    stamp_id: int,
    motivo: Optional[str] = Query(None, description="Motivo do estorno"),
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Estorna (remove) um carimbo de fidelidade lançado por engano.
    Registra voided_at — não deleta o registro para manter rastreabilidade.
    """
    user, tenant_id = user_and_tenant

    stamp = (
        db.query(LoyaltyStamp)
        .filter(LoyaltyStamp.id == stamp_id, LoyaltyStamp.tenant_id == tenant_id)
        .first()
    )
    if not stamp:
        raise HTTPException(status_code=404, detail="Carimbo não encontrado")
    if stamp.voided_at is not None:
        raise HTTPException(status_code=409, detail="Carimbo já foi estornado")

    stamp.voided_at = datetime.now(timezone.utc)
    if motivo:
        stamp.notes = f"{stamp.notes or ''} [ESTORNO: {motivo}]".strip()

    campanha = (
        db.query(Campaign)
        .filter(
            Campaign.id == stamp.campaign_id,
            Campaign.tenant_id == tenant_id,
        )
        .first()
    )
    if campanha is not None:
        from app.campaigns.loyalty_service import sync_loyalty_rewards_for_customer

        sync_loyalty_rewards_for_customer(
            db,
            campaign=campanha,
            customer_id=stamp.customer_id,
            source_event_id=None,
        )

    saldo = summarize_loyalty_balances_for_customer(
        db,
        tenant_id=tenant_id,
        customer_id=stamp.customer_id,
    )
    log_campaign_event(
        db=db,
        tenant_id=tenant_id,
        user_id=_current_user_id(user),
        event="campaign.loyalty.stamp_voided",
        entity_type="campaign_loyalty_stamps",
        entity_id=stamp.id,
        metadata=build_loyalty_stamp_audit_metadata(
            stamp=stamp,
            campaign=campanha,
            operation="voided",
            balance=saldo,
            extra={"reason": motivo},
        ),
        details=f"Carimbo #{stamp.id} estornado",
    )

    db.commit()

    logger.info(
        "[Campanhas] Carimbo #%d estornado customer_id=%d tenant=%s restantes=%d",
        stamp_id,
        stamp.customer_id,
        tenant_id,
        saldo["total_carimbos"],
    )
    return {
        "ok": True,
        "stamp_id": stamp_id,
        "total_carimbos_ativos": saldo["total_carimbos"],
        "total_carimbos_brutos": saldo["total_carimbos_brutos"],
        "carimbos_comprometidos_total": saldo["carimbos_comprometidos_total"],
        "carimbos_em_debito": saldo["carimbos_em_debito"],
        "carimbos_convertidos": saldo["carimbos_convertidos"],
    }


# ---------------------------------------------------------------------------
# Retenção Dinâmica — CRUD dedicado (filtra por campaign_type = inactivity)
# ---------------------------------------------------------------------------
