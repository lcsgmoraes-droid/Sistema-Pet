from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import User
from app.routes.ecommerce_auth_cliente import _get_or_create_cliente_for_user
from app.routes.ecommerce_auth_common import (
    _cashback_disponivel_clause,
    _get_current_ecommerce_user,
    _is_expired,
    _is_expired_or_equal,
    _remaining_days_until,
)


router = APIRouter()


@router.get("/meus-cupons")
def meus_cupons(
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    """
    Retorna os cupons ativos do cliente autenticado no app.
    """
    from app.campaigns.models import Coupon, CouponStatusEnum

    cliente = _get_or_create_cliente_for_user(db, current_user)

    cupons = (
        db.query(Coupon)
        .filter(
            Coupon.tenant_id == current_user.tenant_id,
            Coupon.customer_id == cliente.id,
            Coupon.status == CouponStatusEnum.active,
        )
        .order_by(Coupon.created_at.desc())
        .all()
    )

    now = datetime.now(timezone.utc)
    resultado = []
    for c in cupons:
        expirado = _is_expired(c.valid_until, now)
        resultado.append(
            {
                "id": c.id,
                "code": c.code,
                "coupon_type": c.coupon_type.value,
                "discount_value": float(c.discount_value) if c.discount_value else None,
                "discount_percent": float(c.discount_percent)
                if c.discount_percent
                else None,
                "valid_until": c.valid_until.isoformat() if c.valid_until else None,
                "expirado": expirado,
                "min_purchase_value": float(c.min_purchase_value)
                if c.min_purchase_value
                else None,
            }
        )

    return resultado


@router.get("/meus-beneficios")
def meus_beneficios(
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    """
    Retorna em uma única chamada tudo que o app precisa para montar
    a tela 'Meus Benefícios': ranking, carimbos, cashback e cupons ativos.
    """
    from sqlalchemy import func as sqlfunc
    from app.campaigns.models import (
        CashbackTransaction,
        Campaign,
        CampaignTypeEnum,
        Coupon,
        CouponStatusEnum,
        CustomerRankHistory,
    )
    from app.campaigns.loyalty_service import summarize_loyalty_balances_for_customer

    cliente = _get_or_create_cliente_for_user(db, current_user)
    tenant_id = current_user.tenant_id
    now = datetime.now(timezone.utc)

    # --- Cashback ---
    saldo_raw = (
        db.query(sqlfunc.sum(CashbackTransaction.amount))
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.customer_id == cliente.id,
            _cashback_disponivel_clause(CashbackTransaction, now),
        )
        .scalar()
    )
    saldo_cashback = float(saldo_raw or 0)

    # --- Carimbos ---
    loyalty_summary = summarize_loyalty_balances_for_customer(
        db,
        tenant_id=tenant_id,
        customer_id=cliente.id,
    )
    loyalty_campaign = (
        db.query(Campaign)
        .filter(
            Campaign.tenant_id == tenant_id,
            Campaign.campaign_type == CampaignTypeEnum.loyalty_stamp,
        )
        .first()
    )
    stamps_to_complete = (
        int((loyalty_campaign.params or {}).get("stamps_to_complete", 10))
        if loyalty_campaign
        else 10
    )
    min_purchase_value = (
        float((loyalty_campaign.params or {}).get("min_purchase_value", 0) or 0)
        if loyalty_campaign
        else 0.0
    )
    saldo_total_carimbos = int(loyalty_summary.get("total_carimbos") or 0)
    carimbos_no_cartao = max(saldo_total_carimbos, 0)

    # --- Ranking ---
    rank_atual = (
        db.query(CustomerRankHistory)
        .filter(
            CustomerRankHistory.tenant_id == tenant_id,
            CustomerRankHistory.customer_id == cliente.id,
        )
        .order_by(CustomerRankHistory.period.desc())
        .first()
    )
    rank_level = rank_atual.rank_level.value if rank_atual else "bronze"
    rank_total_spent = float(rank_atual.total_spent) if rank_atual else 0.0
    rank_total_purchases = rank_atual.total_purchases if rank_atual else 0

    ranking_campaign = (
        db.query(Campaign)
        .filter(
            Campaign.tenant_id == tenant_id,
            Campaign.campaign_type == CampaignTypeEnum.ranking_monthly,
        )
        .first()
    )
    rp = ranking_campaign.params if ranking_campaign else {}
    ranking_thresholds = {
        "silver_min_spent": float(rp.get("silver_min_spent", 300)),
        "silver_min_purchases": int(rp.get("silver_min_purchases", 4)),
        "silver_min_months": int(rp.get("silver_min_months", 2)),
        "gold_min_spent": float(rp.get("gold_min_spent", 1000)),
        "gold_min_purchases": int(rp.get("gold_min_purchases", 10)),
        "gold_min_months": int(rp.get("gold_min_months", 4)),
        "diamond_min_spent": float(rp.get("diamond_min_spent", 3000)),
        "diamond_min_purchases": int(rp.get("diamond_min_purchases", 20)),
        "diamond_min_months": int(rp.get("diamond_min_months", 6)),
        "platinum_min_spent": float(rp.get("platinum_min_spent", 8000)),
        "platinum_min_purchases": int(rp.get("platinum_min_purchases", 40)),
        "platinum_min_months": int(rp.get("platinum_min_months", 10)),
    }

    # --- Cupons ativos ---
    cupons = (
        db.query(Coupon)
        .filter(
            Coupon.tenant_id == tenant_id,
            Coupon.customer_id == cliente.id,
            Coupon.status == CouponStatusEnum.active,
        )
        .order_by(Coupon.created_at.desc())
        .all()
    )
    cupons_lista = []
    for c in cupons:
        expirado = _is_expired(c.valid_until, now)
        cupons_lista.append(
            {
                "id": c.id,
                "code": c.code,
                "coupon_type": c.coupon_type.value,
                "discount_value": float(c.discount_value) if c.discount_value else None,
                "discount_percent": float(c.discount_percent)
                if c.discount_percent
                else None,
                "valid_until": c.valid_until.isoformat() if c.valid_until else None,
                "expirado": expirado,
                "min_purchase_value": float(c.min_purchase_value)
                if c.min_purchase_value
                else None,
            }
        )

    return {
        "cashback": {
            "saldo": saldo_cashback,
        },
        "carimbos": {
            "total_geral": saldo_total_carimbos,
            "carimbos_no_cartao": carimbos_no_cartao,
            "carimbos_ativos_brutos": int(
                loyalty_summary.get("total_carimbos_brutos") or 0
            ),
            "carimbos_comprometidos_total": int(
                loyalty_summary.get("carimbos_comprometidos_total") or 0
            ),
            "carimbos_convertidos": int(
                loyalty_summary.get("carimbos_convertidos") or 0
            ),
            "carimbos_em_debito": int(loyalty_summary.get("carimbos_em_debito") or 0),
            "meta": stamps_to_complete,
            "min_purchase_value": min_purchase_value,
        },
        "ranking": {
            "nivel": rank_level,
            "total_spent": rank_total_spent,
            "total_purchases": rank_total_purchases,
            "thresholds": ranking_thresholds,
        },
        "cupons": cupons_lista,
    }


# ---------------------------------------------------------------------------
# Cashback — extrato (app mobile)
# ---------------------------------------------------------------------------


@router.get("/cashback/extrato")
def meu_extrato_cashback(
    limit: int = 50,
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    """
    Retorna o extrato de cashback do cliente autenticado no app.
    """
    from sqlalchemy import func as sqlfunc
    from app.campaigns.models import CashbackTransaction

    cliente = _get_or_create_cliente_for_user(db, current_user)
    tenant_id = current_user.tenant_id
    now = datetime.now(timezone.utc)

    txs = (
        db.query(CashbackTransaction)
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.customer_id == cliente.id,
        )
        .order_by(CashbackTransaction.created_at.desc())
        .limit(min(limit, 100))
        .all()
    )

    saldo_raw = (
        db.query(sqlfunc.sum(CashbackTransaction.amount))
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.customer_id == cliente.id,
            _cashback_disponivel_clause(CashbackTransaction, now),
        )
        .scalar()
    )
    saldo_atual = float(saldo_raw or 0)

    items = []
    for t in txs:
        is_expired_credit = (
            getattr(t, "tx_type", "credit") == "credit"
            and t.expires_at is not None
            and _is_expired_or_equal(t.expires_at, now)
        )
        items.append(
            {
                "id": t.id,
                "amount": float(t.amount),
                "tx_type": getattr(t, "tx_type", "credit"),
                "source_type": t.source_type.value,
                "description": t.description,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "expires_at": t.expires_at.isoformat() if t.expires_at else None,
                "expired": is_expired_credit,
            }
        )

    return {"saldo_atual": saldo_atual, "transacoes": items}


# ---------------------------------------------------------------------------
# Cashback — sugestão inteligente de pedido (app mobile)
# ---------------------------------------------------------------------------


@router.get("/cashback/sugestao")
def minha_sugestao_cashback(
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    """
    Retorna sugestão de compra baseada no padrão do cliente + saldo de cashback.
    """
    from sqlalchemy import func as sqlfunc
    from app.campaigns.models import CashbackTransaction, CashbackSourceTypeEnum

    cliente = _get_or_create_cliente_for_user(db, current_user)
    tenant_id = current_user.tenant_id
    now = datetime.now(timezone.utc)

    saldo_raw = (
        db.query(sqlfunc.sum(CashbackTransaction.amount))
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.customer_id == cliente.id,
            _cashback_disponivel_clause(CashbackTransaction, now),
        )
        .scalar()
    )
    saldo = float(saldo_raw or 0)

    # Ticket médio estimado pelas últimas compras com cashback
    ultimas = (
        db.query(CashbackTransaction)
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.customer_id == cliente.id,
            CashbackTransaction.tx_type == "credit"
            if hasattr(CashbackTransaction, "tx_type")
            else True,
            CashbackTransaction.source_type == CashbackSourceTypeEnum.campaign,
        )
        .order_by(CashbackTransaction.created_at.desc())
        .limit(10)
        .all()
    )
    ticket_sugerido = (
        round(sum(float(t.amount) for t in ultimas) / len(ultimas) * 50, 2)
        if ultimas
        else 100.0
    )

    valor_com_cashback = max(0.0, round(ticket_sugerido - saldo, 2))

    proximo_expirando = (
        db.query(CashbackTransaction)
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.customer_id == cliente.id,
            CashbackTransaction.tx_type == "credit"
            if hasattr(CashbackTransaction, "tx_type")
            else True,
            CashbackTransaction.expires_at.isnot(None),
            CashbackTransaction.expires_at > now,
        )
        .order_by(CashbackTransaction.expires_at.asc())
        .first()
    )

    return {
        "saldo_disponivel": saldo,
        "ticket_sugerido": ticket_sugerido,
        "valor_com_cashback": valor_com_cashback,
        "economia": min(saldo, ticket_sugerido),
        "proximo_expirando": {
            "amount": float(proximo_expirando.amount),
            "expires_at": proximo_expirando.expires_at.isoformat(),
            "dias_restantes": _remaining_days_until(proximo_expirando.expires_at, now),
        }
        if proximo_expirando
        else None,
    }
