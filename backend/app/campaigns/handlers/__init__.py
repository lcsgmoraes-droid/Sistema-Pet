"""
Handlers de Campanhas
======================

Cada handler é responsável por um tipo de campanha.
O CampaignEngine chama handler.run() — a lógica específica fica aqui.

Regras:
- Handler recebe (db, campaign, event) e retorna {"evaluated": N, "rewarded": M, "errors": E}
- Handler NUNCA chama outro handler
- Handler opera apenas sobre o campaign_type que conhece
- Eventos gerados pelo handler têm event_origin='campaign_action' e event_depth = parent + 1

Handlers disponíveis:
  birthday    → birthday_customer, birthday_pet
  welcome     → welcome_app, welcome_ecommerce
  inactivity  → inactivity
  loyalty     → loyalty_stamp
  cashback    → cashback
  ranking     → ranking_monthly
"""

from typing import Optional

from app.campaigns.models import CampaignTypeEnum


def get_handler(campaign_type: CampaignTypeEnum):
    """
    Retorna a instância do handler para o campaign_type dado.
    Retorna None se o handler ainda não foi implementado.
    """
    from app.campaigns.handlers.birthday import BirthdayHandler
    from app.campaigns.handlers.welcome import WelcomeHandler
    from app.campaigns.handlers.inactivity import InactivityHandler
    from app.campaigns.handlers.loyalty import LoyaltyHandler
    from app.campaigns.handlers.cashback import CashbackHandler
    from app.campaigns.handlers.ranking import RankingHandler
    from app.campaigns.handlers.quick_repurchase import QuickRepurchaseHandler

    _registry = {
        CampaignTypeEnum.birthday_customer: BirthdayHandler(),
        CampaignTypeEnum.birthday_pet: BirthdayHandler(),
        CampaignTypeEnum.welcome_app: WelcomeHandler(),
        CampaignTypeEnum.welcome_ecommerce: WelcomeHandler(),
        CampaignTypeEnum.inactivity: InactivityHandler(),
        CampaignTypeEnum.loyalty_stamp: LoyaltyHandler(),
        CampaignTypeEnum.cashback: CashbackHandler(),
        CampaignTypeEnum.ranking_monthly: RankingHandler(),
        CampaignTypeEnum.quick_repurchase: QuickRepurchaseHandler(),
    }

    return _registry.get(campaign_type)
