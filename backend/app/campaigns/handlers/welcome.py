"""
Handler: Boas-vindas (app e ecommerce)
=======================================

Disparo:  customer_registered (evento em tempo real)
Campanha: welcome_app | welcome_ecommerce

Lógica:
  1. Extrai customer_id do payload do evento
  2. Verifica reference_period = "once" em campaign_executions
     (um cliente só recebe boas-vindas uma vez por campanha)
  3. Se não recebeu: gera cupom + registra execution + enfileira notificação

Parâmetros esperados em campaign.params:
  {
    "coupon_type": "fixed",
    "coupon_value": 15.00,
    "coupon_valid_days": 30,
    "coupon_channel": "app",         # ou "ecommerce"
    "notification_message": "Bem-vindo! Use o cupom {code} na sua primeira compra."
  }
"""

import logging

from sqlalchemy.orm import Session

from app.campaigns.coupon_service import create_coupon
from app.campaigns.models import (
    Campaign,
    CampaignEventQueue,
    CampaignExecution,
    CampaignTypeEnum,
)
from app.campaigns.notification_service import enqueue_email, enqueue_push

logger = logging.getLogger(__name__)

# Este handler só responde a este event_type
_SUPPORTED_EVENTS = frozenset({"customer_registered"})

# Período único: cliente nunca recebe boas-vindas duas vezes
_REFERENCE_PERIOD = "once"


class WelcomeHandler:
    """Handler para campanhas de boas-vindas no app e no ecommerce."""

    def run(
        self,
        db: Session,
        campaign: Campaign,
        event: CampaignEventQueue,
    ) -> dict:
        """
        Processa campanha de boas-vindas para um novo cliente.

        O payload do evento deve conter {"customer_id": <int>}.
        Retorna dict com {"evaluated", "rewarded", "errors"}.
        Não commita — o commit fica no CampaignEngine.
        """
        # Guarda: só processa eventos do tipo correto
        if event.event_type not in _SUPPORTED_EVENTS:
            return {"evaluated": 0, "rewarded": 0, "errors": 0}

        # Guarda: só processa campaigns do tipo correto
        if campaign.campaign_type not in (
            CampaignTypeEnum.welcome_app,
            CampaignTypeEnum.welcome_ecommerce,
        ):
            return {"evaluated": 0, "rewarded": 0, "errors": 0}

        payload = event.payload or {}
        customer_id = payload.get("customer_id")

        if not customer_id:
            logger.warning(
                "[WelcomeHandler] Evento sem customer_id — event_id=%d payload=%s",
                event.id,
                payload,
            )
            return {"evaluated": 0, "rewarded": 0, "errors": 1}

        try:
            rewarded = self._reward_customer(
                db=db,
                campaign=campaign,
                customer_id=int(customer_id),
                source_event_id=event.id,
            )
        except Exception as exc:
            logger.warning(
                "[WelcomeHandler] Erro ao recompensar customer_id=%s: %s",
                customer_id,
                exc,
            )
            return {"evaluated": 1, "rewarded": 0, "errors": 1}

        logger.info(
            "[WelcomeHandler] campaign_type=%s tenant=%s customer=%s rewarded=%d",
            campaign.campaign_type.value,
            campaign.tenant_id,
            customer_id,
            rewarded,
        )
        return {"evaluated": 1, "rewarded": rewarded, "errors": 0}

    # ------------------------------------------------------------------
    # Método interno: conceder recompensa (idempotente)
    # ------------------------------------------------------------------

    def _reward_customer(
        self,
        db: Session,
        campaign: Campaign,
        customer_id: int,
        source_event_id: int,
    ) -> int:
        """
        Concede recompensa de boas-vindas de forma idempotente.

        reference_period = "once" → o UNIQUE constraint no banco impede
        que o mesmo cliente receba boas-vindas duas vezes pela mesma campanha.

        Retorna 1 se recompensou, 0 se já havia sido recompensado antes.
        """
        from app.models import Cliente  # Import aqui evita circulares

        # Idempotência
        existing = (
            db.query(CampaignExecution.id)
            .filter(
                CampaignExecution.tenant_id == campaign.tenant_id,
                CampaignExecution.campaign_id == campaign.id,
                CampaignExecution.customer_id == customer_id,
                CampaignExecution.reference_period == _REFERENCE_PERIOD,
            )
            .first()
        )
        if existing:
            return 0  # Já recompensado

        # Busca dados do cliente para personalizar a notificação
        cliente = db.query(Cliente).filter(Cliente.id == customer_id).first()
        if cliente is None:
            logger.warning(
                "[WelcomeHandler] customer_id=%d não encontrado na tabela clientes",
                customer_id,
            )
            return 0

        # Parâmetros da campanha
        params = campaign.params or {}
        coupon_type = params.get("coupon_type", "fixed")
        coupon_value = params.get("coupon_value", 15.0)
        coupon_valid_days = params.get("coupon_valid_days", 30) or None
        coupon_channel = params.get("coupon_channel", "all")
        notification_msg = params.get(
            "notification_message",
            "Bem-vindo, {nome}! Use o cupom {code} na sua primeira compra.",
        )

        # Prefixo do código depende do canal
        prefix = (
            "BOAAPP"
            if campaign.campaign_type == CampaignTypeEnum.welcome_app
            else "BOAEC"
        )

        # Gera cupom
        discount_value = float(coupon_value) if coupon_type == "fixed" else None
        discount_percent = float(coupon_value) if coupon_type == "percent" else None

        coupon = create_coupon(
            db,
            tenant_id=campaign.tenant_id,
            campaign=campaign,
            customer_id=customer_id,
            coupon_type=coupon_type,
            discount_value=discount_value,
            discount_percent=discount_percent,
            channel=coupon_channel,
            valid_days=coupon_valid_days,
            prefix=prefix,
            meta={"reference_period": _REFERENCE_PERIOD},
        )

        # Registra execução
        execution = CampaignExecution(
            tenant_id=campaign.tenant_id,
            campaign_id=campaign.id,
            customer_id=customer_id,
            reference_period=_REFERENCE_PERIOD,
            reward_type=f"coupon:{coupon_type}",
            reward_value=coupon_value,
            reward_meta={"coupon_id": coupon.id, "coupon_code": coupon.code},
            source_event_id=source_event_id,
        )
        db.add(execution)

        # Notificação — body personalizado
        body = notification_msg.format(
            code=coupon.code,
            nome=cliente.nome,
        )
        notif_key = f"welcome:{campaign.id}:{customer_id}:{_REFERENCE_PERIOD}"

        if cliente.email:
            enqueue_email(
                db,
                tenant_id=campaign.tenant_id,
                customer_id=customer_id,
                subject=f"Bem-vindo, {cliente.nome}! Aqui está seu cupom de boas-vindas 🎁",
                body=body,
                email_address=cliente.email,
                idempotency_key=f"{notif_key}:email",
            )

        # Push token: clientes não têm push_token diretamente,
        # integração com app mobile será implementada no Sprint 3
        # enqueue_push(...)

        return 1
