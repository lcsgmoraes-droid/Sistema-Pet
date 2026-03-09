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

        # Job 6: Execução automática de sorteios (diário às 10:00)
        self.scheduler.add_job(
            func=self._auto_execute_drawings,
            trigger=CronTrigger(hour=10, minute=0),
            id="campaign_auto_drawings",
            name="Campanhas: Executar Sorteios Automáticos",
            replace_existing=True,
        )

        # Job 7: Destaque Mensal automático (dia 1 às 08:00)
        self.scheduler.add_job(
            func=self._auto_enviar_destaque_mensal,
            trigger=CronTrigger(day=1, hour=8, minute=0),
            id="campaign_destaque_mensal",
            name="Campanhas: Destaque Mensal Automático",
            replace_existing=True,
        )

        # Job 8: Expiração de cashback + alertas (diário às 07:00)
        self.scheduler.add_job(
            func=self._cashback_expiration_check,
            trigger=CronTrigger(hour=7, minute=0),
            id="campaign_cashback_expiration",
            name="Campanhas: Expirar Cashback + Alertas",
            replace_existing=True,
        )

        logger.info("[CampaignScheduler] Jobs registrados:")
        logger.info("   - daily_birthday_check: 08:00")
        logger.info("   - weekly_inactivity_check: toda segunda às 09:00")
        logger.info("   - monthly_ranking_recalc: dia 1 às 06:00")
        logger.info("   - campaign_worker_tick: a cada 10s")
        logger.info("   - campaign_notification_tick: a cada 5 min")
        logger.info("   - auto_drawings: 10:00 diário")
        logger.info("   - destaque_mensal: dia 1 às 08:00")
        logger.info("   - cashback_expiration: 07:00 diário")

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

    def _auto_execute_drawings(self) -> None:
        """Executa automaticamente sorteios com auto_execute=True cuja draw_date já passou."""
        from datetime import datetime, timezone as _tz
        from app.campaigns.models import Drawing, DrawingEntry, DrawingStatusEnum
        from app.campaigns.notification_service import enqueue_email
        import hashlib, random as _random, uuid as _uuid

        db = SessionLocal()
        try:
            now = datetime.now(_tz.utc)
            due = (
                db.query(Drawing)
                .filter(
                    Drawing.auto_execute == True,
                    Drawing.status == DrawingStatusEnum.open,
                    Drawing.draw_date <= now,
                )
                .all()
            )
            for drawing in due:
                try:
                    entries = (
                        db.query(DrawingEntry)
                        .filter(DrawingEntry.drawing_id == drawing.id)
                        .order_by(DrawingEntry.id.asc())
                        .all()
                    )
                    if not entries:
                        logger.warning("[AutoDrawings] Sorteio %d sem participantes, pulando.", drawing.id)
                        continue

                    ids_csv = ",".join(str(e.id) for e in entries)
                    entries_hash = hashlib.sha256(ids_csv.encode()).hexdigest()
                    seed_uuid = _uuid.uuid4()
                    pool = []
                    for e in entries:
                        pool.extend([e] * max(1, e.ticket_count))
                    rng = _random.Random(str(seed_uuid))
                    rng.shuffle(pool)
                    winner_entry = pool[0]

                    drawing.status = DrawingStatusEnum.drawn
                    drawing.seed_uuid = seed_uuid
                    drawing.entries_hash = entries_hash
                    drawing.entries_frozen_at = now
                    drawing.winner_entry_id = winner_entry.id
                    db.flush()

                    # Notificar ganhador
                    from app.models import Cliente
                    cliente = db.query(Cliente).filter(
                        Cliente.id == winner_entry.customer_id,
                        Cliente.tenant_id == drawing.tenant_id,
                    ).first()
                    if cliente and cliente.email:
                        prize_text = drawing.prize_description or "o prêmio"
                        enqueue_email(
                            db,
                            tenant_id=drawing.tenant_id,
                            customer_id=cliente.id,
                            subject=f"🏆 Você ganhou o sorteio: {drawing.name}!",
                            body=(
                                f"Parabéns, {cliente.nome}! 🎉\n\n"
                                f"Você foi sorteado(a) como ganhador(a) do sorteio **{drawing.name}**.\n"
                                f"Prêmio: {prize_text}\n\n"
                                "Entre em contato conosco para retirar seu prêmio!"
                            ),
                            email_address=cliente.email,
                            idempotency_key=f"sorteio:{drawing.id}:ganhador:{cliente.id}",
                        )
                    logger.info(
                        "[AutoDrawings] Sorteio %d executado. Ganhador: customer_id=%d",
                        drawing.id, winner_entry.customer_id,
                    )
                except Exception as draw_exc:
                    logger.exception("[AutoDrawings] Erro no sorteio %d: %s", drawing.id, draw_exc)
            db.commit()
        except Exception as exc:
            logger.exception("[AutoDrawings] Erro geral: %s", exc)
            db.rollback()
        finally:
            db.close()

    def _auto_enviar_destaque_mensal(self) -> None:
        """
        Envia automaticamente o destaque mensal no dia 1 de cada mês,
        para tenants que têm auto_destaque_mensal=True na campanha ranking_monthly.
        """
        from datetime import datetime, timezone as _tz, timedelta
        from app.campaigns.models import Campaign, CampaignTypeEnum, Coupon, CouponStatusEnum
        from app.campaigns.coupon_service import create_coupon
        from app.campaigns.notification_service import enqueue_email
        from app.models import Tenant

        db = SessionLocal()
        try:
            tenants = db.query(Tenant).filter(Tenant.status == "active").all()
            now = datetime.now(_tz.utc)
            first_day_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            last_month = (first_day_this_month - timedelta(days=1))
            period = last_month.strftime("%Y-%m")

            for tenant in tenants:
                try:
                    # Checar se tem destaque automático ativado
                    campanha = (
                        db.query(Campaign)
                        .filter(
                            Campaign.tenant_id == tenant.id,
                            Campaign.campaign_type == CampaignTypeEnum.ranking_monthly,
                        )
                        .first()
                    )
                    if not campanha:
                        continue
                    params = campanha.params or {}
                    if not params.get("auto_destaque_mensal"):
                        continue

                    # Importar localmente para calcular vencedores
                    from app.vendas_models import Venda
                    from app.models import Cliente
                    from sqlalchemy import func as sqlfunc
                    from app.core.security import get_user_tenant_from_db
                    from app.models import User

                    agg = (
                        db.query(
                            Venda.cliente_id,
                            sqlfunc.sum(Venda.total).label("total_spent"),
                            sqlfunc.count(Venda.id).label("total_purchases"),
                        )
                        .join(User, User.id == Venda.user_id)
                        .filter(
                            User.tenant_id == tenant.id,
                            Venda.status == "finalizada",
                            Venda.cliente_id.isnot(None),
                            Venda.data_finalizacao >= first_day_this_month - timedelta(days=31),
                            Venda.data_finalizacao < first_day_this_month,
                        )
                        .group_by(Venda.cliente_id)
                        .all()
                    )
                    if not agg:
                        continue

                    rows = [
                        {
                            "customer_id": r.cliente_id,
                            "total_spent": float(r.total_spent or 0),
                            "total_purchases": r.total_purchases or 0,
                        }
                        for r in agg
                    ]
                    by_spent = sorted(rows, key=lambda x: x["total_spent"], reverse=True)
                    by_purchases = sorted(rows, key=lambda x: x["total_purchases"], reverse=True)

                    vencedores = {}
                    usados = set()
                    for categoria, lista in [("maior_gasto", by_spent), ("mais_compras", by_purchases)]:
                        for candidato in lista:
                            if candidato["customer_id"] not in usados:
                                vencedores[categoria] = candidato
                                usados.add(candidato["customer_id"])
                                break

                    coupon_value = float(params.get("auto_destaque_coupon_value", 50.0))
                    coupon_days = int(params.get("auto_destaque_coupon_days", 10))

                    for categoria, info in vencedores.items():
                        customer_id = info["customer_id"]
                        meta_key = f"destaque:{period}:{categoria}"
                        # Anti-duplicidade
                        existing = db.query(Coupon).filter(
                            Coupon.tenant_id == tenant.id,
                            Coupon.meta["destaque_key"].astext == meta_key,
                        ).first()
                        if existing:
                            continue
                        cliente = db.query(Cliente).filter(Cliente.id == customer_id).first()
                        if not cliente:
                            continue

                        coupon = create_coupon(
                            db,
                            tenant_id=tenant.id,
                            campaign=campanha,
                            customer_id=customer_id,
                            coupon_type="fixed",
                            discount_value=coupon_value,
                            channel="all",
                            valid_days=coupon_days,
                            prefix="DEST",
                            meta={"destaque_key": meta_key, "categoria": categoria, "periodo": period},
                        )
                        if cliente.email:
                            cat_label = "Maior Destaque do Mês" if categoria == "maior_gasto" else "Mais Compras do Mês"
                            enqueue_email(
                                db,
                                tenant_id=tenant.id,
                                customer_id=customer_id,
                                subject=f"🌟 Parabéns! Você é o {cat_label}!",
                                body=(
                                    f"Olá {cliente.nome}! 🥇\n\n"
                                    f"Você ganhou o prêmio de **{cat_label}** de {period}!\n"
                                    f"Seu cupom de R$ {coupon_value:.0f} de desconto: {coupon.code}\n"
                                    f"Válido por {coupon_days} dias. Aproveite!"
                                ),
                                email_address=cliente.email,
                                idempotency_key=f"destaque:{tenant.id}:{period}:{categoria}:email",
                            )
                        logger.info(
                            "[AutoDestaque] tenant=%s period=%s categoria=%s customer=%d cupom=%s",
                            tenant.id, period, categoria, customer_id, coupon.code,
                        )
                    db.commit()
                except Exception as tenant_exc:
                    logger.exception("[AutoDestaque] Erro no tenant %s: %s", tenant.id, tenant_exc)
                    db.rollback()
        except Exception as exc:
            logger.exception("[AutoDestaque] Erro geral: %s", exc)
        finally:
            db.close()

    def _auto_seed_all_tenants(self) -> None:
        """Garante que todos os tenants ativos têm campanhas padrão criadas."""
        db = SessionLocal()
        try:
            from app.models import Tenant
            tenants = db.query(Tenant).filter(Tenant.status == "active").all()
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

            tenants = db.query(Tenant).filter(Tenant.status == "active").all()
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

    def _cashback_expiration_check(self) -> None:
        """
        Job diário (07:00): processa expiração de cashback em dois passos:
        1. Insere lançamentos negativos para cashback que expirou HOJE (liquida saldo)
        2. Envia alerta (e-mail ou push) para clientes com cashback expirando nos
           próximos X dias (configurável via scheduler_config / alerta_dias_expiracao_cashback)
        """
        from datetime import timedelta, timezone
        from decimal import Decimal
        from sqlalchemy import and_, or_
        from app.campaigns.models import (
            CashbackTransaction, CashbackSourceTypeEnum,
            Campaign, CampaignTypeEnum, NotificationQueue,
            NotificationChannelEnum, NotificationStatusEnum,
        )
        from app.campaigns.notification_service import enqueue_email
        from app.models import Cliente, Tenant

        db = SessionLocal()
        try:
            now_utc = datetime.now(timezone.utc)
            today_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)

            tenants = db.query(Tenant).filter(Tenant.status == "active").all()

            for tenant in tenants:
                try:
                    # Lê configuração: quantos dias antes de alertar
                    cashback_campaign = (
                        db.query(Campaign)
                        .filter(
                            Campaign.tenant_id == tenant.id,
                            Campaign.campaign_type == CampaignTypeEnum.cashback,
                        )
                        .first()
                    )
                    params = cashback_campaign.params if cashback_campaign else {}
                    alerta_dias = int(params.get("cashback_alerta_dias", 7))

                    # --- PASSO 1: Expirar cashback vencido hoje ---
                    expirados_hoje = (
                        db.query(CashbackTransaction)
                        .filter(
                            CashbackTransaction.tenant_id == tenant.id,
                            CashbackTransaction.tx_type == "credit",
                            CashbackTransaction.expires_at >= today_start,
                            CashbackTransaction.expires_at < today_end,
                        )
                        .all()
                    )
                    for tx in expirados_hoje:
                        # Verifica se já existe um lançamento de expiração para este crédito
                        ja_expirou = (
                            db.query(CashbackTransaction.id)
                            .filter(
                                CashbackTransaction.tenant_id == tenant.id,
                                CashbackTransaction.customer_id == tx.customer_id,
                                CashbackTransaction.source_type == CashbackSourceTypeEnum.expiration,
                                CashbackTransaction.source_id == tx.id,
                            )
                            .first()
                        )
                        if ja_expirou:
                            continue
                        # Insere lançamento negativo (estorna o crédito expirado)
                        db.add(CashbackTransaction(
                            tenant_id=tenant.id,
                            customer_id=tx.customer_id,
                            amount=-tx.amount,
                            source_type=CashbackSourceTypeEnum.expiration,
                            source_id=tx.id,
                            description=f"Expiração do cashback #CBTX-{tx.id} (R$ {float(tx.amount):.2f})",
                            tx_type="expired",
                        ))
                        # Notifica o cliente
                        cliente = db.query(Cliente).filter(Cliente.id == tx.customer_id).first()
                        if cliente and cliente.email:
                            enqueue_email(
                                db,
                                tenant_id=tenant.id,
                                customer_id=tx.customer_id,
                                subject="Seu cashback expirou hoje 😢",
                                body=(
                                    f"Olá, {cliente.nome}! Infelizmente R$ {float(tx.amount):.2f} "
                                    f"de cashback venceu hoje sem ser utilizado. "
                                    f"Continue comprando para acumular novos créditos!"
                                ),
                                email_address=cliente.email,
                                idempotency_key=f"cashback_expired:{tenant.id}:{tx.id}:email",
                            )

                    # --- PASSO 2: Alertar quem expira em X dias ---
                    alerta_limite = now_utc + timedelta(days=alerta_dias)
                    expirando_em_breve = (
                        db.query(CashbackTransaction)
                        .filter(
                            CashbackTransaction.tenant_id == tenant.id,
                            CashbackTransaction.tx_type == "credit",
                            CashbackTransaction.expires_at > today_end,   # ainda não expirou hoje
                            CashbackTransaction.expires_at <= alerta_limite,
                        )
                        .all()
                    )
                    # Agrupa por cliente para não mandar múltiplos e-mails no mesmo dia
                    alertados: set = set()
                    for tx in expirando_em_breve:
                        if tx.customer_id in alertados:
                            continue
                        # Verifica idempotência: já enviou alerta hoje?
                        idem_key = f"cashback_alerta:{tenant.id}:{tx.customer_id}:{today_start.date().isoformat()}"
                        ja_alertou = (
                            db.query(NotificationQueue.id)
                            .filter(NotificationQueue.idempotency_key == idem_key)
                            .first()
                        )
                        if ja_alertou:
                            alertados.add(tx.customer_id)
                            continue
                        cliente = db.query(Cliente).filter(Cliente.id == tx.customer_id).first()
                        if not cliente:
                            continue
                        dias_rest = max(0, (tx.expires_at - now_utc).days)
                        if cliente.email:
                            enqueue_email(
                                db,
                                tenant_id=tenant.id,
                                customer_id=tx.customer_id,
                                subject=f"Seu cashback expira em {dias_rest} dia(s)! ⏰",
                                body=(
                                    f"Olá, {cliente.nome}! Você tem R$ {float(tx.amount):.2f} "
                                    f"de cashback que vai expirar em {dias_rest} dia(s). "
                                    f"Venha fazer uma compra e não perca seus créditos!"
                                ),
                                email_address=cliente.email,
                                idempotency_key=idem_key,
                            )
                        alertados.add(tx.customer_id)
                        logger.info(
                            "[CashbackExpiration] Alerta enviado: tenant=%s customer=%d dias=%d",
                            tenant.id, tx.customer_id, dias_rest,
                        )

                    db.commit()
                    logger.info(
                        "[CashbackExpiration] tenant=%s: %d expirado(s), %d alertado(s)",
                        tenant.id, len(expirados_hoje), len(alertados),
                    )

                except Exception as tenant_exc:
                    logger.exception("[CashbackExpiration] Erro no tenant %s: %s", tenant.id, tenant_exc)
                    db.rollback()

        except Exception as exc:
            logger.exception("[CashbackExpiration] Erro geral: %s", exc)
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
