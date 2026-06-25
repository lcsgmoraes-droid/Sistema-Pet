"""Rotas de cupons de campanhas."""

import logging
import uuid as _uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.campaigns.audit import build_coupon_audit_metadata, log_campaign_event
from app.campaigns.coupon_service import preview_coupon_redemption
from app.campaigns.loyalty_service import revoke_loyalty_reward_by_coupon
from app.campaigns.models import (
    Coupon,
    CouponChannelEnum,
    CouponRedemption,
    CouponStatusEnum,
    CouponTypeEnum,
)
from app.campaigns.routes_common import (
    _current_user_id,
    _resolver_customer_id_campanhas,
    get_db,
)


logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/cupons")
def listar_cupons(
    status: Optional[str] = Query(
        None, description="Filtrar por status: active, used, expired"
    ),
    customer_id: Optional[int] = Query(None),
    campaign_id: Optional[int] = Query(None),
    busca: Optional[str] = Query(
        None, description="Busca por código ou nome do cliente"
    ),
    data_inicio: Optional[str] = Query(
        None, description="Data de criação inicial YYYY-MM-DD"
    ),
    data_fim: Optional[str] = Query(
        None, description="Data de criação final YYYY-MM-DD"
    ),
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista cupons do tenant com filtros opcionais."""
    from app.models import Cliente
    from app.campaigns.models import Campaign as CampaignModel

    _, tenant_id = user_and_tenant
    q = db.query(Coupon).filter(Coupon.tenant_id == tenant_id)
    if status:
        try:
            q = q.filter(Coupon.status == CouponStatusEnum(status))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Status inválido: {status}")
    if customer_id:
        q = q.filter(Coupon.customer_id == customer_id)
    if campaign_id:
        q = q.filter(Coupon.campaign_id == campaign_id)
    if data_inicio:
        try:
            q = q.filter(Coupon.created_at >= datetime.fromisoformat(data_inicio))
        except ValueError:
            pass
    if data_fim:
        try:
            from datetime import timedelta as _td

            q = q.filter(
                Coupon.created_at < datetime.fromisoformat(data_fim) + _td(days=1)
            )
        except ValueError:
            pass
    if busca:
        busca_like = f"%{busca}%"
        matching_ids = [
            c.id
            for c in db.query(Cliente.id)
            .filter(
                Cliente.tenant_id == tenant_id,
                Cliente.nome.ilike(busca_like),
            )
            .all()
        ]
        if matching_ids:
            q = q.filter(
                (Coupon.code.ilike(busca_like)) | (Coupon.customer_id.in_(matching_ids))
            )
        else:
            q = q.filter(Coupon.code.ilike(busca_like))

    cupons = q.order_by(Coupon.id.desc()).limit(300).all()

    # Enriquecer com nome do cliente
    cids = [c.customer_id for c in cupons if c.customer_id]
    clientes_map: dict = {}
    if cids:
        for cl in db.query(Cliente).filter(Cliente.id.in_(cids)).all():
            clientes_map[cl.id] = cl.nome

    # Enriquecer com nome da campanha
    camp_ids = [c.campaign_id for c in cupons if c.campaign_id]
    campanhas_map: dict = {}
    if camp_ids:
        for camp in (
            db.query(CampaignModel).filter(CampaignModel.id.in_(camp_ids)).all()
        ):
            campanhas_map[camp.id] = camp.name

    # Enriquecer com data de uso (redeemed_at) de cada cupom
    coupon_ids = [c.id for c in cupons]
    redeemed_at_map: dict = {}
    if coupon_ids:
        redemptions = (
            db.query(CouponRedemption.coupon_id, CouponRedemption.redeemed_at)
            .filter(CouponRedemption.coupon_id.in_(coupon_ids))
            .all()
        )
        for r in redemptions:
            redeemed_at_map[r.coupon_id] = r.redeemed_at

    return [
        {
            "id": c.id,
            "code": c.code,
            "coupon_type": c.coupon_type.value,
            "discount_value": float(c.discount_value) if c.discount_value else None,
            "discount_percent": float(c.discount_percent)
            if c.discount_percent
            else None,
            "channel": c.channel.value,
            "status": c.status.value,
            "valid_until": c.valid_until.isoformat() if c.valid_until else None,
            "min_purchase_value": float(c.min_purchase_value)
            if c.min_purchase_value
            else None,
            "customer_id": c.customer_id,
            "nome_cliente": clientes_map.get(c.customer_id),
            "campaign_id": c.campaign_id,
            "nome_campanha": campanhas_map.get(c.campaign_id),
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "used_at": redeemed_at_map[c.id].isoformat()
            if c.id in redeemed_at_map
            else None,
            "meta": c.meta,
        }
        for c in cupons
    ]


# ---------------------------------------------------------------------------
# Cupons — criar cupom manual
# ---------------------------------------------------------------------------


def _build_manual_coupon_meta(
    *,
    motivo: Optional[str] = None,
    descricao: Optional[str] = None,
    regras_resumo: Optional[str] = None,
) -> dict:
    motivo_final = (motivo or descricao or "Cupom manual").strip() or "Cupom manual"
    descricao_final = (descricao or motivo_final).strip() or motivo_final
    regras_final = (
        (regras_resumo or "").strip()
        or "Cupom gerado manualmente no gestor para uso conforme valor, canal e validade configurados."
    )
    return {
        "descricao": descricao_final,
        "motivo": motivo_final,
        "campaign_name": motivo_final,
        "regras_resumo": regras_final,
        "criado_por": "manual",
    }


class CriarCupomManualBody(BaseModel):
    coupon_type: str  # "percent" | "fixed" | "gift"
    discount_value: Optional[float] = None
    discount_percent: Optional[float] = None
    channel: str = "all"  # "pdv" | "app" | "ecommerce" | "all"
    valid_until: Optional[str] = None  # ISO date string "YYYY-MM-DD"
    min_purchase_value: Optional[float] = None
    customer_id: Optional[int] = None
    motivo: Optional[str] = None
    descricao: Optional[str] = None
    regras_resumo: Optional[str] = None


@router.post("/cupons/manual")
def criar_cupom_manual(
    body: CriarCupomManualBody,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Cria um cupom manualmente para casos especiais."""
    user, tenant_id = user_and_tenant

    try:
        tipo = CouponTypeEnum(body.coupon_type)
    except ValueError:
        raise HTTPException(
            status_code=400, detail=f"coupon_type inválido: {body.coupon_type}"
        )

    try:
        canal = CouponChannelEnum(body.channel)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"channel inválido: {body.channel}")

    if tipo == CouponTypeEnum.percent and not body.discount_percent:
        raise HTTPException(
            status_code=400, detail="discount_percent é obrigatório para cupom de %"
        )
    if tipo == CouponTypeEnum.fixed and not body.discount_value:
        raise HTTPException(
            status_code=400,
            detail="discount_value é obrigatório para cupom de valor fixo",
        )

    # Gerar código único
    code = f"MAN-{_uuid.uuid4().hex[:8].upper()}"

    valid_until = None
    if body.valid_until:
        try:
            valid_until = datetime.fromisoformat(body.valid_until).replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            raise HTTPException(
                status_code=400, detail="valid_until deve ser YYYY-MM-DD"
            )

    customer_id_resolvido = (
        _resolver_customer_id_campanhas(
            db,
            tenant_id=tenant_id,
            customer_ref=body.customer_id,
        )
        if body.customer_id
        else None
    )

    cupom = Coupon(
        tenant_id=tenant_id,
        code=code,
        coupon_type=tipo,
        discount_value=body.discount_value,
        discount_percent=body.discount_percent,
        channel=canal,
        valid_until=valid_until,
        min_purchase_value=body.min_purchase_value,
        customer_id=customer_id_resolvido,
        campaign_id=None,
        meta=_build_manual_coupon_meta(
            motivo=body.motivo,
            descricao=body.descricao,
            regras_resumo=body.regras_resumo,
        ),
    )
    db.add(cupom)
    db.flush()
    log_campaign_event(
        db=db,
        tenant_id=tenant_id,
        user_id=_current_user_id(user),
        event="campaign.coupon.manual_created",
        entity_type="campaign_coupons",
        entity_id=cupom.id,
        metadata=build_coupon_audit_metadata(
            cupom,
            source="manual",
            extra={"description": body.descricao or body.motivo or "Cupom manual"},
        ),
        details=f"Cupom manual {cupom.code} criado",
    )
    db.commit()
    db.refresh(cupom)

    return {
        "id": cupom.id,
        "code": cupom.code,
        "coupon_type": cupom.coupon_type.value,
        "discount_value": float(cupom.discount_value) if cupom.discount_value else None,
        "discount_percent": float(cupom.discount_percent)
        if cupom.discount_percent
        else None,
        "channel": cupom.channel.value,
        "status": cupom.status.value,
        "valid_until": cupom.valid_until.isoformat() if cupom.valid_until else None,
        "min_purchase_value": float(cupom.min_purchase_value)
        if cupom.min_purchase_value
        else None,
        "customer_id": cupom.customer_id,
        "meta": cupom.meta,
    }


# ---------------------------------------------------------------------------
# Cupons — resgate no PDV
# ---------------------------------------------------------------------------


class ResgateBody(BaseModel):
    venda_total: Optional[float] = None
    customer_id: Optional[int] = None


@router.post("/cupons/{code}/resgatar")
def resgatar_cupom(
    code: str,
    body: ResgateBody,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Valida um cupom no PDV e retorna a previa do desconto.

    O consumo efetivo acontece apenas no fechamento atomico da venda.
    """
    _, tenant_id = user_and_tenant
    preview = preview_coupon_redemption(
        db,
        tenant_id=tenant_id,
        code=code,
        venda_total=body.venda_total or 0.0,
        customer_id=body.customer_id,
    )
    logger.info(
        "[Campanhas] Cupom validado em previa: code=%s tenant=%s discount=R$%.2f",
        preview["code"],
        tenant_id,
        float(preview["discount_applied"] or 0),
    )
    return preview


# ---------------------------------------------------------------------------
# Clientes — saldo cashback, carimbos e ranking
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Busca de clientes (para o Gestor de Benefícios — sem exigir clientes.visualizar)
# ---------------------------------------------------------------------------


@router.delete("/cupons/{code}", status_code=200)
def anular_cupom(
    code: str,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Marca o cupao como void (cancelado).
    Se o cupao for de fidelidade (gerado por consumo de carimbos),
    devolve automaticamente os carimbos comprometidos para saldo disponivel.
    So e possivel anular cupoes com status `active`.
    """
    user, tenant_id = user_and_tenant
    cupom = (
        db.query(Coupon)
        .filter(Coupon.tenant_id == tenant_id, Coupon.code == code)
        .first()
    )
    if not cupom:
        raise HTTPException(404, detail="Cupão não encontrado.")
    if cupom.status != CouponStatusEnum.active:
        raise HTTPException(
            400,
            detail=f"Não é possível anular um cupão com status '{cupom.status.value}'.",
        )

    loyalty_reversal = revoke_loyalty_reward_by_coupon(
        db,
        tenant_id=tenant_id,
        coupon_id=cupom.id,
        reason="cupom_anulado_manualmente",
    )

    cupom.status = CouponStatusEnum.voided
    cupom.meta = {
        **(getattr(cupom, "meta", None) or {}),
        "voided_reason": "cupom_anulado_manualmente",
        "voided_at": datetime.now(timezone.utc).isoformat(),
    }
    log_campaign_event(
        db=db,
        tenant_id=tenant_id,
        user_id=_current_user_id(user),
        event="campaign.coupon.voided",
        entity_type="campaign_coupons",
        entity_id=cupom.id,
        metadata=build_coupon_audit_metadata(
            cupom,
            source="manual_void",
            extra={
                "reason": "cupom_anulado_manualmente",
                "loyalty_reversal": loyalty_reversal,
            },
        ),
        details=f"Cupom {cupom.code} anulado manualmente",
    )
    db.commit()
    return {
        "ok": True,
        "code": code,
        "status": "voided",
        "fidelidade": {
            "cupom_vinculado": bool(loyalty_reversal.get("matched")),
            "carimbos_restaurados": bool(loyalty_reversal.get("revoked")),
        },
    }


# ---------------------------------------------------------------------------
# Relátorio de campanhas — histórico de cashback (créditos e resgates)
# ---------------------------------------------------------------------------
