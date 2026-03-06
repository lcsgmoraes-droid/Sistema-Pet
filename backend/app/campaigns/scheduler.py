"""
Campaign Scheduler — Jobs Agendados (APScheduler)
==================================================

Registra os jobs periódicos do motor de campanhas no APScheduler
já existente no projeto (acerto_scheduler.py usa o mesmo padrão).

Regra: O scheduler NUNCA contém lógica de campanha.
Ele apenas publica um evento na campaign_event_queue e retorna.
Toda a lógica fica nos handlers.

Jobs registrados:
  - daily_birthday_check    → todo dia às 08:00
  - weekly_inactivity_check → toda segunda-feira às 09:00
  - monthly_ranking_recalc  → dia 1 de cada mês às 06:00
  - campaign_worker_tick    → a cada 10 segundos (processa a fila)

Para registrar no main.py:
    from app.campaigns.scheduler import CampaignScheduler
    campaign_scheduler = CampaignScheduler()
    campaign_scheduler.start()
"""

import logging
import uuid
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.db import SessionLocal
from app.campaigns.models import CampaignEventQueue, EventOriginEnum
from app.campaigns.worker import CampaignWorker

logger = logging.getLogger(__name__)


class CampaignScheduler:
    """
    Gerencia os jobs agendados de campanhas.

    Integra com o APScheduler já existente no projeto.
    """

    def __init__(self):
        self.scheduler = BackgroundScheduler(
            job_defaults={"coalesce": True, "max_instances": 1}
        )
        self._register_jobs()

    def _register_jobs(self) -> None:
        # Job 1: Verificação diária de aniversários (08:00)
        self.scheduler.add_job(
            func=self._publish_daily_birthday_check,
            trigger=CronTrigger(hour=8, minute=0),
            id="campaign_daily_birthday_check",
            name="Campanhas: Verificação de Aniversários",
            replace_existing=True,
        )

        # Job 2: Verificação semanal de inatividade (segunda às 09:00)
        self.scheduler.add_job(
            func=self._publish_weekly_inactivity_check,
            trigger=CronTrigger(day_of_week="mon", hour=9, minute=0),
            id="campaign_weekly_inactivity_check",
            name="Campanhas: Clientes Inativos",
            replace_existing=True,
        )

        # Job 3: Recálculo mensal de ranking (dia 1 às 06:00)
        self.scheduler.add_job(
            func=self._publish_monthly_ranking_recalc,
            trigger=CronTrigger(day=1, hour=6, minute=0),
            id="campaign_monthly_ranking_recalc",
            name="Campanhas: Recálculo de Ranking",
            replace_existing=True,
        )

        # Job 4: Worker da fila (a cada 10 segundos)
        self.scheduler.add_job(
            func=self._tick_worker,
            trigger=IntervalTrigger(seconds=10),
            id="campaign_worker_tick",
            name="Campanhas: Processar Fila",
            replace_existing=True,
        )

        # Job 5: Envio de notificações (a cada 5 minutos)
        self.scheduler.add_job(
            func=self._tick_notifications,
            trigger=IntervalTrigger(minutes=5),
            id="campaign_notification_tick",
            name="Campanhas: Enviar Notificações",
            replace_existing=True,
        )

        logger.info("[CampaignScheduler] Jobs registrados:")
        logger.info("   - daily_birthday_check: 08:00")
        logger.info("   - weekly_inactivity_check: toda segunda às 09:00")
        logger.info("   - monthly_ranking_recalc: dia 1 às 06:00")
        logger.info("   - campaign_worker_tick: a cada 10s")
        logger.info("   - campaign_notification_tick: a cada 5 min")

    def start(self) -> None:
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("[CampaignScheduler] Iniciado.")
            # Garantir que todos os tenants têm campanhas padrão
            self._auto_seed_all_tenants()

    def shutdown(self, wait: bool = True) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=wait)
            logger.info("[CampaignScheduler] Encerrado.")

    # ------------------------------------------------------------------
    # Publicadores de eventos (1 método por job)
    # Apenas publicam o evento na fila — sem lógica de campanha.
    # ------------------------------------------------------------------

    def _publish_daily_birthday_check(self) -> None:
        self._publish_event_for_all_tenants("daily_birthday_check")

    def _publish_weekly_inactivity_check(self) -> None:
        self._publish_event_for_all_tenants("weekly_inactivity_check")

    def _publish_monthly_ranking_recalc(self) -> None:
        self._publish_event_for_all_tenants("monthly_ranking_recalc")

    def _tick_worker(self) -> None:
        """Processa eventos pendentes na fila."""
        try:
            worker = CampaignWorker(db_factory=SessionLocal)
            count = worker.process_batch()
            if count > 0:
                logger.info("[CampaignScheduler] Worker processou %d evento(s)", count)
        except Exception as exc:
            logger.exception("[CampaignScheduler] Erro no worker tick: %s", exc)

    def _tick_notifications(self) -> None:
        """Despacha notificações pendentes (e-mail, push)."""
        try:
            from app.campaigns.notification_sender import NotificationSender
            sender = NotificationSender(db_factory=SessionLocal)
            stats = sender.process_batch()
            if stats["processed"] > 0:
                logger.info("[CampaignScheduler] Notificações: %s", stats)
        except Exception as exc:
            logger.exception("[CampaignScheduler] Erro no notification tick: %s", exc)

    def _auto_seed_all_tenants(self) -> None:
        """Garante que todos os tenants ativos têm campanhas padrão criadas."""
        db = SessionLocal()
        try:
            from app.models import Tenant
            tenants = db.query(Tenant).filter(Tenant.ativo == True).all()
            seeded = 0
            for tenant in tenants:
                try:
                    count = seed_campaigns_for_tenant(db, tenant.id)
                    if count > 0:
                        seeded += count
                        logger.info(
                            "[CampaignScheduler] Auto-seed: %d campanha(s) criada(s) para tenant %s",
                            count, tenant.id,
                        )
                except Exception as exc:
                    logger.warning("[CampaignScheduler] Erro ao seed tenant %s: %s", tenant.id, exc)
            if seeded:
                logger.info("[CampaignScheduler] Auto-seed concluído: %d campanha(s) criada(s) no total", seeded)
        except Exception as exc:
            logger.exception("[CampaignScheduler] Erro no auto-seed: %s", exc)
        finally:
            db.close()

    def _publish_event_for_all_tenants(self, event_type: str) -> None:
        """
        Publica um evento agendado para todos os tenants ativos.
        Cada tenant recebe seu próprio evento na fila.
        """
        db = SessionLocal()
        try:
            from app.models import Tenant  # Import local para evitar circular

            tenants = db.query(Tenant).filter(Tenant.ativo == True).all()
            for tenant in tenants:
                event = CampaignEventQueue(
                    tenant_id=tenant.id,
                    event_type=event_type,
                    event_origin=EventOriginEnum.system_scheduled,
                    event_depth=0,
                    payload={
                        "triggered_by": "scheduler",
                        "triggered_at": datetime.now().isoformat(),
                    },
                )
                db.add(event)
            db.commit()
            logger.info(
                "[CampaignScheduler] Evento '%s' publicado para %d tenant(s)",
                event_type,
                len(tenants),
            )
        except Exception as exc:
            logger.exception(
                "[CampaignScheduler] Erro ao publicar '%s': %s", event_type, exc
            )
            db.rollback()
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Função standalone: seed de campanhas padrão por tenant
# Pode ser chamada pelo scheduler ou por endpoint admin.
# ---------------------------------------------------------------------------

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
