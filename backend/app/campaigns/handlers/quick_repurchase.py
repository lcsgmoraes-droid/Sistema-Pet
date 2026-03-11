"""
Handler: Recompra Rápida
=========================

Disparo:  purchase_completed (ao finalizar venda no PDV)
Campanha: quick_repurchase

Lógica:
  1. Ao finalizar uma compra, verifica se o cliente já tem um cupom ativo
     gerado por esta campanha (evita reenvio enquanto o cupom não expirar)
  2. Verifica valor mínimo da compra (opcional)
  3. Gera um cupom de desconto com validade curta para estimular retorno
  4. Idempotência: 1 cupom ativo por cliente por campanha (via query em coupons)

Parâmetros esperados em campaign.params:
  {
    "min_purchase_value": 0.0,       # valor mínimo da compra para receber o cupom (0 = sem mínimo)
    "coupon_type": "percent",        # "percent" ou "fixed"
    "coupon_value": 10.0,            # 10% off ou R$ 10 off
    "coupon_valid_days": 15,         # cupom válido por X dias
    "coupon_channel": "pdv",         # canal onde o cupom pode ser usado
    "notification_message": ""       # mensagem opcional (futura integração de push/email)
  }
"""

import logging
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.campaigns.coupon_service import create_coupon
from app.campaigns.models import (
    Campaign,
    CampaignEventQueue,
    CampaignTypeEnum,
    Coupon,
    CouponStatusEnum,
)

logger = logging.getLogger(__name__)

_SUPPORTED_EVENTS = frozenset({"purchase_completed"})


class QuickRepurchaseHandler:
    """Handler para cupom de recompra rápida após finalização de venda."""

    def run(
        self,
        db: Session,
        campaign: Campaign,
        event: CampaignEventQueue,
    ) -> dict:
        """
        Gera um cupom de desconto imediatamente após uma compra.
        Só processa se o cliente ainda não tem um cupom ativo desta campanha.
        Não commita — o commit fica no CampaignEngine.
        """
        if event.event_type not in _SUPPORTED_EVENTS:
            return {"evaluated": 0, "rewarded": 0, "errors": 0}
        if campaign.campaign_type != CampaignTypeEnum.quick_repurchase:
            return {"evaluated": 0, "rewarded": 0, "errors": 0}

        payload = event.payload or {}
        customer_id = payload.get("customer_id")
        venda_total = float(payload.get("venda_total", 0))

        if not customer_id:
            return {"evaluated": 0, "rewarded": 0, "errors": 0}

        params = campaign.params or {}
        min_purchase = float(params.get("min_purchase_value", 0))

        # Verifica valor mínimo
        if min_purchase > 0 and venda_total < min_purchase:
            return {"evaluated": 1, "rewarded": 0, "errors": 0}

        # Idempotência: cliente já tem cupom ativo desta campanha?
        existing_coupon = (
            db.query(Coupon.id)
            .filter(
                Coupon.tenant_id == campaign.tenant_id,
                Coupon.customer_id == customer_id,
                Coupon.campaign_id == campaign.id,
                Coupon.status == CouponStatusEnum.active,
            )
            .first()
        )
        if existing_coupon:
            return {"evaluated": 1, "rewarded": 0, "errors": 0}

        # Cooldown: não reenviar cupom se já foi gerado nos últimos 60 dias
        sixty_days_ago = date.today() - timedelta(days=60)
        recent_coupon = (
            db.query(Coupon.id)
            .filter(
                Coupon.tenant_id == campaign.tenant_id,
                Coupon.customer_id == customer_id,
                Coupon.campaign_id == campaign.id,
                Coupon.created_at >= sixty_days_ago,
            )
            .first()
        )
        if recent_coupon:
            return {"evaluated": 1, "rewarded": 0, "errors": 0}

        coupon_type = params.get("coupon_type", "percent")
        coupon_value = float(params.get("coupon_value", 10.0))
        coupon_valid_days = int(params.get("coupon_valid_days", 15))

        discount_value = coupon_value if coupon_type == "fixed" else None
        discount_percent = coupon_value if coupon_type == "percent" else None

        try:
            coupon = create_coupon(
                db,
                tenant_id=campaign.tenant_id,
                campaign=campaign,
                customer_id=customer_id,
                coupon_type=coupon_type,
                discount_value=discount_value,
                discount_percent=discount_percent,
                valid_days=coupon_valid_days,
                channel=params.get("coupon_channel", "pdv"),
            )

            logger.info(
                "[QuickRepurchaseHandler] Cupom %s gerado para cliente_id=%s (campanha=%d)",
                coupon.code,
                customer_id,
                campaign.id,
            )
            return {"evaluated": 1, "rewarded": 1, "errors": 0}

        except Exception as exc:
            logger.warning(
                "[QuickRepurchaseHandler] Erro ao gerar cupom cliente_id=%s: %s",
                customer_id,
                exc,
            )
            return {"evaluated": 1, "rewarded": 0, "errors": 1}
