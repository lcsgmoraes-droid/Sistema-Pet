"""Implementacoes dos jobs pesados do scheduler de campanhas."""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from app.campaigns.models import CampaignEventQueue, EventOriginEnum
from app.campaigns.scheduler_seed import seed_campaigns_for_tenant
from app.tenancy.context import clear_current_tenant, set_current_tenant

DbFactory = Callable[[], Any]


def run_auto_execute_drawings(*, db_factory: DbFactory, logger) -> None:
    """Executa automaticamente sorteios com auto_execute=True cuja draw_date já passou."""
    from datetime import datetime, timezone as _tz
    from app.campaigns.models import Drawing, DrawingEntry, DrawingStatusEnum
    from app.campaigns.notification_service import enqueue_email
    from app.models import Tenant
    import uuid as _uuid

    db = db_factory()
    try:
        now = datetime.now(_tz.utc)
        # Itera os tenants ativos e descobre os sorteios devidos COM contexto de
        # tenant (sob TenantScoped, um SELECT global em Drawing dispara fail-fast).
        tenants = db.query(Tenant.id).filter(Tenant.status == "active").all()
        due = []
        for (tenant_id_raw,) in tenants:
            set_current_tenant(_uuid.UUID(str(tenant_id_raw)))
            try:
                due.extend(
                    db.query(Drawing)
                    .filter(
                        Drawing.auto_execute.is_(True),
                        Drawing.status == DrawingStatusEnum.open,
                        Drawing.draw_date <= now,
                    )
                    .all()
                )
            finally:
                clear_current_tenant()
        for drawing in due:
            # Cada sorteio é processado sob o contexto da sua loja (queries em
            # DrawingEntry/Cliente e enfileiramento de e-mail ficam escopados).
            set_current_tenant(_uuid.UUID(str(drawing.tenant_id)))
            try:
                entries = (
                    db.query(DrawingEntry)
                    .filter(DrawingEntry.drawing_id == drawing.id)
                    .order_by(DrawingEntry.id.asc())
                    .all()
                )
                if not entries:
                    logger.warning(
                        "[AutoDrawings] Sorteio %d sem participantes, pulando.",
                        drawing.id,
                    )
                    continue

                ids_csv = ",".join(str(e.id) for e in entries)
                entries_hash = hashlib.sha256(ids_csv.encode()).hexdigest()
                seed_uuid = _uuid.uuid4()
                pool = []
                for e in entries:
                    pool.extend([e] * max(1, e.ticket_count))
                winner_entry = pool[secrets.randbelow(len(pool))]

                drawing.status = DrawingStatusEnum.drawn
                drawing.seed_uuid = seed_uuid
                drawing.entries_hash = entries_hash
                drawing.entries_frozen_at = now
                drawing.winner_entry_id = winner_entry.id
                db.flush()

                # Notificar ganhador
                from app.models import Cliente

                cliente = (
                    db.query(Cliente)
                    .filter(
                        Cliente.id == winner_entry.customer_id,
                        Cliente.tenant_id == drawing.tenant_id,
                    )
                    .first()
                )
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
                    drawing.id,
                    winner_entry.customer_id,
                )
            except Exception as draw_exc:
                logger.exception(
                    "[AutoDrawings] Erro no sorteio %d: %s", drawing.id, draw_exc
                )
            finally:
                clear_current_tenant()
        db.commit()
    except Exception as exc:
        logger.exception("[AutoDrawings] Erro geral: %s", exc)
        db.rollback()
    finally:
        db.close()


def run_auto_send_monthly_highlights(*, db_factory: DbFactory, logger) -> None:
    """
    Envia automaticamente o destaque mensal no dia 1 de cada mês,
    para tenants que têm auto_destaque_mensal=True na campanha ranking_monthly.
    """
    from datetime import datetime, timezone as _tz
    from app.models import Tenant

    db = db_factory()
    try:
        tenants = db.query(Tenant).filter(Tenant.status == "active").all()
        now = datetime.now(_tz.utc)
        first_day_this_month = now.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        last_month = first_day_this_month - timedelta(days=1)
        period = last_month.strftime("%Y-%m")

        for tenant in tenants:
            set_current_tenant(uuid.UUID(str(tenant.id)))
            try:
                processed = _process_monthly_highlights_for_tenant(
                    db, tenant, first_day_this_month, period, logger
                )
                if processed:
                    db.commit()
            except Exception as tenant_exc:
                logger.exception(
                    "[AutoDestaque] Erro no tenant %s: %s", tenant.id, tenant_exc
                )
                db.rollback()
            finally:
                clear_current_tenant()
    except Exception as exc:
        logger.exception("[AutoDestaque] Erro geral: %s", exc)
    finally:
        db.close()


def _process_monthly_highlights_for_tenant(
    db, tenant, first_day_this_month, period: str, logger
) -> bool:
    from app.campaigns.models import Campaign, CampaignTypeEnum

    campaign = (
        db.query(Campaign)
        .filter(
            Campaign.tenant_id == tenant.id,
            Campaign.campaign_type == CampaignTypeEnum.ranking_monthly,
        )
        .first()
    )
    if not campaign:
        return False

    params = campaign.params or {}
    if not params.get("auto_destaque_mensal"):
        return False

    rows = _monthly_highlight_sales_rows(db, tenant.id, first_day_this_month)
    if not rows:
        return False

    winners = _select_monthly_highlight_winners(rows)
    coupon_value = float(params.get("auto_destaque_coupon_value", 50.0))
    coupon_days = int(params.get("auto_destaque_coupon_days", 10))

    for category, info in winners.items():
        _create_monthly_highlight_coupon(
            db,
            tenant=tenant,
            campaign=campaign,
            category=category,
            info=info,
            period=period,
            coupon_value=coupon_value,
            coupon_days=coupon_days,
            logger=logger,
        )
    return True


def _monthly_highlight_sales_rows(db, tenant_id, first_day_this_month) -> list[dict]:
    from app.models import User
    from app.vendas_models import Venda
    from sqlalchemy import func as sqlfunc

    agg = (
        db.query(
            Venda.cliente_id,
            sqlfunc.sum(Venda.total).label("total_spent"),
            sqlfunc.count(Venda.id).label("total_purchases"),
        )
        .join(User, User.id == Venda.user_id)
        .filter(
            User.tenant_id == tenant_id,
            Venda.status == "finalizada",
            Venda.cliente_id.isnot(None),
            Venda.data_finalizacao >= first_day_this_month - timedelta(days=31),
            Venda.data_finalizacao < first_day_this_month,
        )
        .group_by(Venda.cliente_id)
        .all()
    )
    return [
        {
            "customer_id": row.cliente_id,
            "total_spent": float(row.total_spent or 0),
            "total_purchases": row.total_purchases or 0,
        }
        for row in agg
    ]


def _select_monthly_highlight_winners(rows: list[dict]) -> dict[str, dict]:
    winners = {}
    used = set()
    categories = [
        ("maior_gasto", sorted(rows, key=lambda x: x["total_spent"], reverse=True)),
        (
            "mais_compras",
            sorted(rows, key=lambda x: x["total_purchases"], reverse=True),
        ),
    ]

    for category, candidates in categories:
        for candidate in candidates:
            if candidate["customer_id"] in used:
                continue
            winners[category] = candidate
            used.add(candidate["customer_id"])
            break
    return winners


def _create_monthly_highlight_coupon(
    db,
    *,
    tenant,
    campaign,
    category: str,
    info: dict,
    period: str,
    coupon_value: float,
    coupon_days: int,
    logger,
) -> None:
    from app.campaigns.coupon_service import create_coupon
    from app.campaigns.models import Coupon
    from app.campaigns.notification_service import enqueue_email
    from app.models import Cliente

    customer_id = info["customer_id"]
    meta_key = f"destaque:{period}:{category}"
    existing = (
        db.query(Coupon)
        .filter(
            Coupon.tenant_id == tenant.id,
            Coupon.meta["destaque_key"].astext == meta_key,
        )
        .first()
    )
    if existing:
        return

    cliente = db.query(Cliente).filter(Cliente.id == customer_id).first()
    if not cliente:
        return

    coupon = create_coupon(
        db,
        tenant_id=tenant.id,
        campaign=campaign,
        customer_id=customer_id,
        coupon_type="fixed",
        discount_value=coupon_value,
        channel="all",
        valid_days=coupon_days,
        prefix="DEST",
        meta={
            "destaque_key": meta_key,
            "categoria": category,
            "periodo": period,
        },
    )
    if cliente.email:
        cat_label = (
            "Maior Destaque do Mês"
            if category == "maior_gasto"
            else "Mais Compras do Mês"
        )
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
            idempotency_key=f"destaque:{tenant.id}:{period}:{category}:email",
        )
    logger.info(
        "[AutoDestaque] tenant=%s period=%s categoria=%s customer=%d cupom=%s",
        tenant.id,
        period,
        category,
        customer_id,
        coupon.code,
    )


def run_auto_seed_all_tenants(*, db_factory: DbFactory, logger) -> None:
    """Garante que todos os tenants ativos têm campanhas padrão criadas."""
    db = db_factory()
    try:
        from app.models import Tenant

        tenants = db.query(Tenant).filter(Tenant.status == "active").all()
        seeded = 0
        for tenant in tenants:
            set_current_tenant(uuid.UUID(str(tenant.id)))
            try:
                count = seed_campaigns_for_tenant(db, tenant.id)
                if count > 0:
                    seeded += count
                    logger.info(
                        "[CampaignScheduler] Auto-seed: %d campanha(s) criada(s) para tenant %s",
                        count,
                        tenant.id,
                    )
            except Exception as exc:
                logger.warning(
                    "[CampaignScheduler] Erro ao seed tenant %s: %s", tenant.id, exc
                )
            finally:
                clear_current_tenant()
        if seeded:
            logger.info(
                "[CampaignScheduler] Auto-seed concluído: %d campanha(s) criada(s) no total",
                seeded,
            )
    except Exception as exc:
        logger.exception("[CampaignScheduler] Erro no auto-seed: %s", exc)
    finally:
        db.close()


def publish_scheduled_event_for_all_tenants(
    event_type: str, *, db_factory: DbFactory, logger
) -> None:
    """
    Publica um evento agendado para todos os tenants ativos.
    Cada tenant recebe seu próprio evento na fila.
    """
    db = db_factory()
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


def run_cashback_expiration_check(*, db_factory: DbFactory, logger) -> None:
    """
    Job diário (07:00): processa expiração de cashback em dois passos:
    1. Insere lançamentos negativos para cashback que expirou HOJE (liquida saldo)
    2. Envia alerta (e-mail ou push) para clientes com cashback expirando nos
       próximos X dias (configurável via scheduler_config / alerta_dias_expiracao_cashback)
    """
    from app.models import Tenant

    db = db_factory()
    try:
        now_utc = datetime.now(timezone.utc)
        today_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        tenants = db.query(Tenant).filter(Tenant.status == "active").all()

        for tenant in tenants:
            set_current_tenant(uuid.UUID(str(tenant.id)))
            try:
                expired_count, alerted_count = _process_cashback_expiration_for_tenant(
                    db,
                    tenant,
                    now_utc=now_utc,
                    today_start=today_start,
                    today_end=today_end,
                    logger=logger,
                )
                db.commit()
                logger.info(
                    "[CashbackExpiration] tenant=%s: %d expirado(s), %d alertado(s)",
                    tenant.id,
                    expired_count,
                    alerted_count,
                )

            except Exception as tenant_exc:
                logger.exception(
                    "[CashbackExpiration] Erro no tenant %s: %s",
                    tenant.id,
                    tenant_exc,
                )
                db.rollback()
            finally:
                clear_current_tenant()

    except Exception as exc:
        logger.exception("[CashbackExpiration] Erro geral: %s", exc)
    finally:
        db.close()


def _process_cashback_expiration_for_tenant(
    db, tenant, *, now_utc, today_start, today_end, logger
) -> tuple[int, int]:
    alert_days = _cashback_alert_days(db, tenant.id)
    expiring_today = _cashback_credits_expiring_today(
        db, tenant.id, today_start, today_end
    )
    for tx in expiring_today:
        _expire_cashback_credit_if_needed(db, tenant, tx)

    expiring_soon = _cashback_credits_expiring_soon(
        db,
        tenant.id,
        today_end=today_end,
        alert_limit=now_utc + timedelta(days=alert_days),
    )
    alerted = _send_cashback_expiration_alerts(
        db,
        tenant,
        expiring_soon,
        now_utc=now_utc,
        today_start=today_start,
        logger=logger,
    )
    return len(expiring_today), len(alerted)


def _cashback_alert_days(db, tenant_id) -> int:
    from app.campaigns.models import Campaign, CampaignTypeEnum

    campaign = (
        db.query(Campaign)
        .filter(
            Campaign.tenant_id == tenant_id,
            Campaign.campaign_type == CampaignTypeEnum.cashback,
        )
        .first()
    )
    params = campaign.params if campaign else {}
    return int(params.get("cashback_alerta_dias", 7))


def _cashback_credits_expiring_today(db, tenant_id, today_start, today_end):
    from app.campaigns.models import CashbackTransaction

    return (
        db.query(CashbackTransaction)
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.tx_type == "credit",
            CashbackTransaction.expires_at >= today_start,
            CashbackTransaction.expires_at < today_end,
        )
        .all()
    )


def _expire_cashback_credit_if_needed(db, tenant, tx) -> None:
    from app.campaigns.models import CashbackSourceTypeEnum, CashbackTransaction
    from app.campaigns.notification_service import enqueue_email
    from app.models import Cliente

    already_expired = (
        db.query(CashbackTransaction.id)
        .filter(
            CashbackTransaction.tenant_id == tenant.id,
            CashbackTransaction.customer_id == tx.customer_id,
            CashbackTransaction.source_type == CashbackSourceTypeEnum.expiration,
            CashbackTransaction.source_id == tx.id,
        )
        .first()
    )
    if already_expired:
        return

    db.add(
        CashbackTransaction(
            tenant_id=tenant.id,
            customer_id=tx.customer_id,
            amount=-tx.amount,
            source_type=CashbackSourceTypeEnum.expiration,
            source_id=tx.id,
            description=f"Expiração do cashback #CBTX-{tx.id} (R$ {float(tx.amount):.2f})",
            tx_type="expired",
        )
    )
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


def _cashback_credits_expiring_soon(db, tenant_id, *, today_end, alert_limit):
    from app.campaigns.models import CashbackTransaction

    return (
        db.query(CashbackTransaction)
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.tx_type == "credit",
            CashbackTransaction.expires_at > today_end,
            CashbackTransaction.expires_at <= alert_limit,
        )
        .all()
    )


def _send_cashback_expiration_alerts(
    db, tenant, transactions, *, now_utc, today_start, logger
) -> set:
    alerted = set()
    for tx in transactions:
        if tx.customer_id in alerted:
            continue
        if _send_cashback_expiration_alert(
            db,
            tenant,
            tx,
            now_utc=now_utc,
            today_start=today_start,
            logger=logger,
        ):
            alerted.add(tx.customer_id)
    return alerted


def _send_cashback_expiration_alert(
    db, tenant, tx, *, now_utc, today_start, logger
) -> bool:
    from app.campaigns.models import NotificationQueue
    from app.campaigns.notification_service import enqueue_email
    from app.models import Cliente

    idem_key = (
        f"cashback_alerta:{tenant.id}:{tx.customer_id}:{today_start.date().isoformat()}"
    )
    already_alerted = (
        db.query(NotificationQueue.id)
        .filter(NotificationQueue.idempotency_key == idem_key)
        .first()
    )
    if already_alerted:
        return True

    cliente = db.query(Cliente).filter(Cliente.id == tx.customer_id).first()
    if not cliente:
        return False

    remaining_days = max(0, (tx.expires_at - now_utc).days)
    if cliente.email:
        enqueue_email(
            db,
            tenant_id=tenant.id,
            customer_id=tx.customer_id,
            subject=f"Seu cashback expira em {remaining_days} dia(s)! ⏰",
            body=(
                f"Olá, {cliente.nome}! Você tem R$ {float(tx.amount):.2f} "
                f"de cashback que vai expirar em {remaining_days} dia(s). "
                f"Venha fazer uma compra e não perca seus créditos!"
            ),
            email_address=cliente.email,
            idempotency_key=idem_key,
        )
    logger.info(
        "[CashbackExpiration] Alerta enviado: tenant=%s customer=%d dias=%d",
        tenant.id,
        tx.customer_id,
        remaining_days,
    )
    return True


__all__ = [
    "publish_scheduled_event_for_all_tenants",
    "run_auto_execute_drawings",
    "run_auto_seed_all_tenants",
    "run_auto_send_monthly_highlights",
    "run_cashback_expiration_check",
]
