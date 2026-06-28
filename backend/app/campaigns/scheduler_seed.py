"""Seed de campanhas padrao usado pelo scheduler e rotas administrativas."""

_DEFAULT_CAMPAIGNS = [
    {
        "name": "Cartão Fidelidade",
        "campaign_type": "loyalty_stamp",
        "priority": 10,
        "params": {
            "min_purchase_value": 50.0,
            "stamps_to_complete": 10,
            "reward_type": "coupon",
            "reward_value": 20.0,
            "coupon_percent": None,
            "coupon_days_valid": 30,
            "intermediate_stamp": None,
            "intermediate_reward_type": "coupon",
            "intermediate_reward_value": 0.0,
            "benefit_channels": ["loja_fisica", "app", "ecommerce"],
            "notification_message": "Parabéns! Seu cartão está completo 🎉 Use o cupom: {code}",
        },
    },
    {
        "name": "Cashback por Nível",
        "campaign_type": "cashback",
        "priority": 20,
        "params": {
            "bronze_percent": 0.0,
            "silver_percent": 1.0,
            "gold_percent": 2.0,
            "diamond_percent": 3.0,
            "platinum_percent": 5.0,
            "benefit_channels": ["loja_fisica", "app", "ecommerce"],
        },
    },
    {
        "name": "Aniversário do Cliente",
        "campaign_type": "birthday_customer",
        "priority": 30,
        "params": {
            "coupon_type": "fixed",
            "coupon_value": 20.0,
            "coupon_valid_days": 3,
            "coupon_channel": "all",
            "notification_message": "Feliz aniversário! 🎂 Seu cupom de presente: {code}",
        },
    },
    {
        "name": "Aniversário do Pet",
        "campaign_type": "birthday_pet",
        "priority": 35,
        "params": {
            "coupon_type": "fixed",
            "coupon_value": 15.0,
            "coupon_valid_days": 3,
            "coupon_channel": "all",
            "notification_message": "Parabéns pelo aniversário do seu pet! 🐾 Cupom: {code}",
        },
    },
    {
        "name": "Boas-vindas App",
        "campaign_type": "welcome_app",
        "priority": 40,
        "params": {
            "coupon_type": "fixed",
            "coupon_value": 10.0,
            "coupon_valid_days": 30,
            "coupon_channel": "app",
            "notification_message": "Bem-vindo! 🎉 Use o cupom: {code} na sua primeira compra.",
        },
    },
    {
        "name": "Clientes Inativos (30 dias)",
        "campaign_type": "inactivity",
        "priority": 50,
        "params": {
            "inactivity_days": 30,
            "coupon_type": "percent",
            "coupon_value": None,
            "coupon_percent": 10.0,
            "coupon_valid_days": 7,
            "coupon_channel": "all",
            "notification_message": "Sentimos sua falta! 😊 Use o cupom: {code} e volte a nos visitar.",
        },
    },
    {
        "name": "Recompra Rápida (15 dias)",
        "campaign_type": "quick_repurchase",
        "priority": 55,
        "params": {
            "min_purchase_value": 0.0,
            "coupon_type": "percent",
            "coupon_value": 5.0,
            "coupon_valid_days": 15,
            "coupon_channel": "pdv",
            "benefit_channels": ["loja_fisica", "app", "ecommerce"],
            "notification_message": "Obrigado pela compra! Use o cupom {code} na próxima visita.",
        },
    },
    {
        "name": "Ranking Mensal",
        "campaign_type": "ranking_monthly",
        "priority": 60,
        "params": {
            "bronze_min_spent": 0.0,
            "bronze_min_purchases": 1,
            "silver_min_spent": 300.0,
            "silver_min_purchases": 4,
            "silver_min_active_months": 2,
            "gold_min_spent": 1000.0,
            "gold_min_purchases": 10,
            "gold_min_active_months": 4,
            "diamond_min_spent": 3000.0,
            "diamond_min_purchases": 20,
            "diamond_min_active_months": 6,
            "platinum_min_spent": 8000.0,
            "platinum_min_purchases": 40,
            "platinum_min_active_months": 10,
        },
    },
]


def seed_campaigns_for_tenant(db, tenant_id) -> int:
    """
    Cria campanhas padrão para o tenant se ele ainda não as tiver.
    Idempotente: não duplica campanhas já existentes (verifica por campaign_type).
    Retorna o número de campanhas criadas.
    """
    from app.campaigns.models import Campaign, CampaignStatusEnum, CampaignTypeEnum

    # Tipos já existentes para este tenant
    existing_types = {
        row[0].value
        for row in db.query(Campaign.campaign_type)
        .filter(Campaign.tenant_id == tenant_id)
        .all()
    }

    created = 0
    for spec in _DEFAULT_CAMPAIGNS:
        if spec["campaign_type"] in existing_types:
            continue
        campaign = Campaign(
            tenant_id=tenant_id,
            name=spec["name"],
            campaign_type=CampaignTypeEnum(spec["campaign_type"]),
            status=CampaignStatusEnum.active,
            priority=spec["priority"],
            params=spec["params"],
        )
        db.add(campaign)
        created += 1

    if created:
        db.commit()

    return created


__all__ = ["_DEFAULT_CAMPAIGNS", "seed_campaigns_for_tenant"]
