"""
Serviço de Cupons — Campaign Engine
======================================

Responsabilidades:
- Gerar código único por tenant (prefixo + 6 chars aleatórios)
- Criar registro na tabela `coupons`
- Não commita — o commit fica no caller (engine ou handler)

Uso:
    from app.campaigns.coupon_service import create_coupon

    coupon = create_coupon(
        db,
        tenant_id=campaign.tenant_id,
        campaign=campaign,
        customer_id=cliente.id,
        coupon_type="fixed",
        discount_value=20.00,
        valid_days=7,
        prefix="ANIV",
    )
    print(coupon.code)  # ex: ANIV-XK92P3
"""

import logging
import secrets
import string
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.campaigns.models import (
    Campaign,
    Coupon,
    CouponChannelEnum,
    CouponTypeEnum,
)

logger = logging.getLogger(__name__)

_CODE_CHARS = string.ascii_uppercase + string.digits


def _generate_code(prefix: str, length: int = 6) -> str:
    """Gera código alfanumérico maiúsculo: PREFIX-XXXXXX."""
    suffix = "".join(secrets.choice(_CODE_CHARS) for _ in range(length))
    return f"{prefix}-{suffix}"


def create_coupon(
    db: Session,
    *,
    tenant_id,
    campaign: Campaign | None = None,
    customer_id: int,
    coupon_type: str = "fixed",
    discount_value=None,
    discount_percent=None,
    channel: str = "all",
    valid_days: int | None = None,
    min_purchase_value=None,
    prefix: str = "CAMP",
    meta: dict | None = None,
) -> Coupon:
    """
    Cria um cupom com código único para o tenant.

    Tenta até 5 vezes em caso de colisão de código (improvável) e
    usa db.flush() para obter o ID sem commitar.

    Parâmetros
    ----------
    tenant_id         : UUID do tenant da campanha
    campaign          : objeto Campaign (para FK)
    customer_id       : ID do cliente (nullable no modelo, mas obrigatório aqui)
    coupon_type       : "fixed" | "percent" | "gift" | "free_shipping"
    discount_value    : valor absoluto (R$) — para type="fixed"
    discount_percent  : percentual (0–100) — para type="percent"
    channel           : "pdv" | "app" | "ecommerce" | "all"
    valid_days        : dias de validade a partir de agora (None = sem validade)
    min_purchase_value: valor mínimo de compra para usar o cupom
    prefix            : prefixo do código (ex: "ANIV", "BOAS", "PETANIV")
    meta              : JSON livre para dados extras

    Retorna
    -------
    Coupon com ID já gerado via flush()
    """
    valid_until: datetime | None = None
    if valid_days:
        valid_until = datetime.now(timezone.utc) + timedelta(days=valid_days)

    coupon: Coupon | None = None
    for attempt in range(5):
        code = _generate_code(prefix)
        existing = (
            db.query(Coupon)
            .filter(Coupon.tenant_id == tenant_id, Coupon.code == code)
            .first()
        )
        if not existing:
            coupon = Coupon(
                tenant_id=tenant_id,
                code=code,
                campaign_id=campaign.id if campaign is not None else None,
                customer_id=customer_id,
                coupon_type=CouponTypeEnum(coupon_type),
                discount_value=discount_value,
                discount_percent=discount_percent,
                channel=CouponChannelEnum(channel),
                valid_until=valid_until,
                min_purchase_value=min_purchase_value,
                meta=meta,
            )
            db.add(coupon)
            db.flush()  # Gera o ID sem commitar
            logger.debug(
                "[coupon_service] Cupom criado: code=%s tenant=%s attempt=%d",
                code,
                tenant_id,
                attempt + 1,
            )
            return coupon

    # Se chegou aqui, todas as tentativas colidiram (altamente improvável)
    raise RuntimeError(
        f"Não foi possível gerar código de cupom único para tenant {tenant_id} "
        f"após 5 tentativas com prefix='{prefix}'"
    )
