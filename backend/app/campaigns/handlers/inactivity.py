"""
Handler: Clientes Inativos
===========================

Disparo:  weekly_inactivity_check (job semanal toda segunda às 09:00)
Campanha: inactivity

Lógica:
  1. Busca clientes que não compraram há N dias (configurável em params)
  2. Verifica campaign_executions com reference_period = semana ISO (ex: "2026-W10")
     para não reenviar na mesma semana
  3. Se elegível: gera cupom + registra execution + enfileira notificação

Parâmetros esperados em campaign.params:
  {
    "inactivity_days": 30,           # dias sem compra para ser elegível
    "coupon_type": "percent",
    "coupon_value": 10.0,            # 10% de desconto
    "coupon_valid_days": 7,
    "coupon_channel": "all",
    "notification_message": "Sentimos sua falta! Cupom de {value}%: {code}"
  }

Nota: O usuário pode criar múltiplas campanhas de inatividade
(30 dias, 60 dias, 90 dias) — cada uma é uma linha separada em `campaigns`.
"""

import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func
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

_SUPPORTED_EVENTS = frozenset({"weekly_inactivity_check"})


class InactivityHandler:
    """Handler para campanhas de retenção por inatividade."""

    def run(
        self,
        db: Session,
        campaign: Campaign,
        event: CampaignEventQueue,
    ) -> dict:
        """
        Busca clientes que não compraram nos últimos N dias e entrega cupom.
        reference_period = semana ISO (ex: "2026-W10") — não repete na mesma semana.
        Não commita — o commit fica no CampaignEngine.
        """
        if event.event_type not in _SUPPORTED_EVENTS:
            return {"evaluated": 0, "rewarded": 0, "errors": 0}
        if campaign.campaign_type != CampaignTypeEnum.inactivity:
            return {"evaluated": 0, "rewarded": 0, "errors": 0}

        from app.models import Cliente, User
        from app.vendas_models import Venda

        params = campaign.params or {}
        inactivity_days = int(params.get("inactivity_days", 30))
        cutoff = datetime.now(timezone.utc) - timedelta(days=inactivity_days)

        # Semana ISO como período — evita reenviar na mesma semana
        today = date.today()
        iso_year, iso_week, _ = today.isocalendar()
        reference_period = f"{iso_year}-W{iso_week:02d}"

        # Subquery: última compra finalizada por cliente neste tenant
        last_purchase_sq = (
            db.query(
                Venda.cliente_id,
                func.max(Venda.data_finalizacao).label("last_purchase"),
            )
            .join(User, User.id == Venda.user_id)
            .filter(
                User.tenant_id == campaign.tenant_id,
                Venda.status == "finalizada",
                Venda.cliente_id.isnot(None),
            )
            .group_by(Venda.cliente_id)
            .subquery()
        )

        # Clientes que a última compra foi ANTES do cutoff (inativos)
        clientes = (
            db.query(Cliente)
            .join(User, User.id == Cliente.user_id)
            .join(last_purchase_sq, last_purchase_sq.c.cliente_id == Cliente.id)
            .filter(
                User.tenant_id == campaign.tenant_id,
                last_purchase_sq.c.last_purchase < cutoff,
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
                    reference_period=reference_period,
                    params=params,
                    source_event_id=event.id,
                    inactivity_days=inactivity_days,
                )
            except Exception as exc:
                errors += 1
                logger.warning(
                    "[InactivityHandler] Erro cliente_id=%d: %s", cliente.id, exc
                )

        logger.info(
            "[InactivityHandler] tenant=%s days=%d period=%s avaliados=%d recompensados=%d erros=%d",
            campaign.tenant_id, inactivity_days, reference_period,
            evaluated, rewarded, errors,
        )
        return {"evaluated": evaluated, "rewarded": rewarded, "errors": errors}

    def _reward_customer(
        self, db, campaign, customer_id, customer_name, customer_email,
        reference_period, params, source_event_id, inactivity_days,
    ) -> int:
        # Idempotência: já recebeu nesta semana?
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
            return 0

        coupon_type = params.get("coupon_type", "percent")
        coupon_value = params.get("coupon_value", 10.0)
        coupon_valid_days = params.get("coupon_valid_days", 7) or None
        coupon_channel = params.get("coupon_channel", "all")
        notification_msg = params.get(
            "notification_message",
            "Sentimos sua falta, {nome}! Temos um cupom especial: {code}",
        )

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
            prefix="VOLTA",
            meta={"reference_period": reference_period, "inactivity_days": inactivity_days},
        )

        db.add(CampaignExecution(
            tenant_id=campaign.tenant_id,
            campaign_id=campaign.id,
            customer_id=customer_id,
            reference_period=reference_period,
            reward_type=f"coupon:{coupon_type}",
            reward_value=coupon_value,
            reward_meta={"coupon_id": coupon.id, "coupon_code": coupon.code},
            source_event_id=source_event_id,
        ))

        body = notification_msg.format(code=coupon.code, nome=customer_name)
        notif_key = f"inactivity:{campaign.id}:{customer_id}:{reference_period}"
        if customer_email:
            enqueue_email(
                db,
                tenant_id=campaign.tenant_id,
                customer_id=customer_id,
                subject=f"Sentimos sua falta, {customer_name}! Aqui está um presente 🎁",
                body=body,
                email_address=customer_email,
                idempotency_key=f"{notif_key}:email",
            )
        return 1
