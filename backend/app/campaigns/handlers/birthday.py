"""
Handler: Aniversário (cliente e pet)
=====================================

Disparo:  daily_birthday_check (job diário às 08:00)
Campanha: birthday_customer | birthday_pet

Lógica:
  1. Busca clientes cujo aniversário é hoje (campo nascimento = hoje)
  2. Para birthday_pet: busca pets cujo aniversário é hoje
  3. Para cada cliente elegível, verifica em campaign_executions se
     já recebeu recompensa neste período (reference_period = "YYYY-MM-DD")
  4. Se não recebeu: gera cupom + registra execution + enfileira notificação

Parâmetros esperados em campaign.params:
  {
    "coupon_type": "fixed",          # ou "percent"
    "coupon_value": 20.00,           # R$ 20 ou 20%
    "coupon_valid_days": 1,          # validade em dias (1 = só no aniversário, 0 = sem expirar)
    "coupon_channel": "all",
    "notification_message": "Feliz aniversário! Seu cupom: {code}"
  }
"""

import logging
from datetime import date

from sqlalchemy import extract
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
_SUPPORTED_EVENTS = frozenset({"daily_birthday_check"})


class BirthdayHandler:
    """Handler para campanhas de aniversário de cliente e de pet."""

    def run(
        self,
        db: Session,
        campaign: Campaign,
        event: CampaignEventQueue,
    ) -> dict:
        """
        Processa campanhas de aniversário para cliente ou pet.

        Retorna dict com {"evaluated", "rewarded", "errors"}.
        Não commita — o commit fica no CampaignEngine.
        """
        # Guarda: só processa eventos do tipo correto
        if event.event_type not in _SUPPORTED_EVENTS:
            return {"evaluated": 0, "rewarded": 0, "errors": 0}

        if campaign.campaign_type == CampaignTypeEnum.birthday_customer:
            return self._run_birthday_customer(db, campaign, event)
        elif campaign.campaign_type == CampaignTypeEnum.birthday_pet:
            return self._run_birthday_pet(db, campaign, event)

        return {"evaluated": 0, "rewarded": 0, "errors": 0}

    # ------------------------------------------------------------------
    # Aniversário de cliente
    # ------------------------------------------------------------------

    def _run_birthday_customer(
        self,
        db: Session,
        campaign: Campaign,
        event: CampaignEventQueue,
    ) -> dict:
        """Busca clientes com aniversário hoje e concede recompensa."""
        from app.models import Cliente, User  # Import aqui evita circulares

        today = date.today()
        params = campaign.params or {}

        # Busca clientes do tenant com aniversário hoje
        clientes = (
            db.query(Cliente)
            .join(User, User.id == Cliente.user_id)
            .filter(
                User.tenant_id == campaign.tenant_id,
                extract("month", Cliente.data_nascimento) == today.month,
                extract("day", Cliente.data_nascimento) == today.day,
                Cliente.data_nascimento.isnot(None),
            )
            .all()
        )

        evaluated = len(clientes)
        rewarded = 0
        errors = 0

        for cliente in clientes:
            try:
                rewarded += self._reward_customer(
                    db=db,
                    campaign=campaign,
                    customer_id=cliente.id,
                    customer_name=cliente.nome,
                    customer_email=cliente.email,
                    customer_push_token=None,  # Clientes não têm push_token diretamente
                    reference_period=today.isoformat(),
                    params=params,
                    source_event_id=event.id,
                    prefix="ANIV",
                )
            except Exception as exc:
                errors += 1
                logger.warning(
                    "[BirthdayHandler] Erro ao recompensar cliente_id=%d: %s",
                    cliente.id,
                    exc,
                )

        logger.info(
            "[BirthdayHandler] birthday_customer tenant=%s avaliados=%d recompensados=%d erros=%d",
            campaign.tenant_id,
            evaluated,
            rewarded,
            errors,
        )
        return {"evaluated": evaluated, "rewarded": rewarded, "errors": errors}

    # ------------------------------------------------------------------
    # Aniversário de pet
    # ------------------------------------------------------------------

    def _run_birthday_pet(
        self,
        db: Session,
        campaign: Campaign,
        event: CampaignEventQueue,
    ) -> dict:
        """Busca pets com aniversário hoje e concede recompensa ao dono."""
        from app.models import Cliente, Pet, User  # Import aqui evita circulares

        today = date.today()
        params = campaign.params or {}

        # Busca pets do tenant com aniversário hoje
        pets = (
            db.query(Pet)
            .join(User, User.id == Pet.user_id)
            .filter(
                User.tenant_id == campaign.tenant_id,
                extract("month", Pet.data_nascimento) == today.month,
                extract("day", Pet.data_nascimento) == today.day,
                Pet.data_nascimento.isnot(None),
                Pet.ativo.is_(True),
            )
            .all()
        )

        evaluated = len(pets)
        rewarded = 0
        errors = 0

        for pet in pets:
            try:
                # Recompensa vai para o dono do pet
                dono = db.query(Cliente).filter(Cliente.id == pet.cliente_id).first()
                if dono is None:
                    errors += 1
                    continue

                # period único por pet: evita que 2 pets do mesmo dono
                # recebam apenas 1 recompensa (cada pet gera seu próprio cupom)
                reference_period = f"{today.isoformat()}-p{pet.id}"

                rewarded += self._reward_customer(
                    db=db,
                    campaign=campaign,
                    customer_id=pet.id,  # Chave de idempotência é o PET
                    customer_name=dono.nome,
                    customer_email=dono.email,
                    customer_push_token=None,
                    reference_period=reference_period,
                    params=params,
                    source_event_id=event.id,
                    prefix="PETANIV",
                    notification_extra=f" (aniversário do {pet.nome})",
                )
            except Exception as exc:
                errors += 1
                logger.warning(
                    "[BirthdayHandler] Erro ao recompensar pet_id=%d: %s",
                    pet.id,
                    exc,
                )

        logger.info(
            "[BirthdayHandler] birthday_pet tenant=%s avaliados=%d recompensados=%d erros=%d",
            campaign.tenant_id,
            evaluated,
            rewarded,
            errors,
        )
        return {"evaluated": evaluated, "rewarded": rewarded, "errors": errors}

    # ------------------------------------------------------------------
    # Método compartilhado: conceder recompensa (idempotente)
    # ------------------------------------------------------------------

    def _reward_customer(
        self,
        db: Session,
        campaign: Campaign,
        customer_id: int,
        customer_name: str,
        customer_email: str | None,
        customer_push_token: str | None,
        reference_period: str,
        params: dict,
        source_event_id: int,
        prefix: str,
        notification_extra: str = "",
    ) -> int:
        """
        Concede recompensa a um cliente de forma idempotente.

        Verifica se já existe execution. Se sim, skip (retorna 0).
        Se não, cria cupom + execution + notificação (retorna 1).
        """
        # Idempotência: verifica se já foi recompensado neste período
        existing = (
            db.query(CampaignExecution.id)
            .filter(
                CampaignExecution.tenant_id == campaign.tenant_id,
                CampaignExecution.campaign_id == campaign.id,
                CampaignExecution.customer_id == customer_id,
                CampaignExecution.reference_period == reference_period,
            )
            .first()
        )
        if existing:
            return 0  # Já recompensado — skip silencioso

        # Parâmetros da campanha (com defaults seguros)
        coupon_type = params.get("coupon_type", "fixed")
        coupon_value = params.get("coupon_value", 10.0)
        coupon_valid_days = params.get("coupon_valid_days", 7) or None
        coupon_channel = params.get("coupon_channel", "all")
        notification_msg = params.get(
            "notification_message",
            "Feliz aniversário{extra}! Use o cupom {code} em sua próxima compra.",
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
            meta={"reference_period": reference_period},
        )

        # Registra execução (idempotente pelo UNIQUE constraint)
        execution = CampaignExecution(
            tenant_id=campaign.tenant_id,
            campaign_id=campaign.id,
            customer_id=customer_id,
            reference_period=reference_period,
            reward_type=f"coupon:{coupon_type}",
            reward_value=coupon_value,
            reward_meta={"coupon_id": coupon.id, "coupon_code": coupon.code},
            source_event_id=source_event_id,
        )
        db.add(execution)

        # Enfileira notificação
        body = notification_msg.format(
            code=coupon.code,
            nome=customer_name,
            extra=notification_extra,
        )
        notif_key = f"bday:{campaign.id}:{customer_id}:{reference_period}"

        if customer_push_token:
            enqueue_push(
                db,
                tenant_id=campaign.tenant_id,
                customer_id=customer_id,
                body=body,
                idempotency_key=f"{notif_key}:push",
                push_token=customer_push_token,
            )

        if customer_email:
            enqueue_email(
                db,
                tenant_id=campaign.tenant_id,
                customer_id=customer_id,
                subject=f"Feliz aniversário{notification_extra}, {customer_name}! 🎂",
                body=body,
                email_address=customer_email,
                idempotency_key=f"{notif_key}:email",
            )

        return 1
