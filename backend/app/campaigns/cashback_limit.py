"""Limite opcional de resgate de cashback por venda."""

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_DOWN

from app.campaigns.models import Campaign, CampaignStatusEnum, CampaignTypeEnum


def cashback_use_limit_percent(db, tenant_id):
    """Menor limite configurado entre campanhas de cashback ativas e vigentes."""
    now = datetime.now(timezone.utc)
    campaigns = (
        db.query(Campaign)
        .filter(
            Campaign.tenant_id == tenant_id,
            Campaign.campaign_type == CampaignTypeEnum.cashback,
            Campaign.status == CampaignStatusEnum.active,
            (Campaign.valid_from.is_(None) | (Campaign.valid_from <= now)),
            (Campaign.valid_until.is_(None) | (Campaign.valid_until >= now)),
        )
        .all()
    )
    limits = []
    for campaign in campaigns:
        value = (campaign.params or {}).get("cashback_use_limit_percent")
        if value is None or value == "":
            continue
        try:
            percent = Decimal(str(value))
        except (InvalidOperation, ValueError):
            continue
        if percent.is_finite() and 0 <= percent <= 100:
            limits.append(percent)
    return min(limits) if limits else None


def cashback_sale_limit(total, percent):
    """Arredonda para baixo para nunca ultrapassar o percentual configurado."""
    return (Decimal(str(total or 0)) * percent / 100).quantize(
        Decimal("0.01"), rounding=ROUND_DOWN
    )


def cashback_available_in_sale(total, percent, already_used):
    return max(Decimal("0"), cashback_sale_limit(total, percent) - Decimal(str(already_used)))


def cashback_amount_brl(value):
    formatted = f"{Decimal(str(value)):,.2f}"
    return "R$ " + formatted.replace(",", "_").replace(".", ",").replace("_", ".")
