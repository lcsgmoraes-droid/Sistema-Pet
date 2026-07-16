"""Aprendizado de recompra e notificacoes de produtos recorrentes."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from statistics import median
from typing import Iterable

from sqlalchemy import func
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

MIN_INTERVAL_DAYS = 3
MAX_INTERVAL_DAYS = 365
MIN_LEARNED_CONFIDENCE = 0.65
MAX_HISTORY_INTERVALS = 6


@dataclass(frozen=True)
class RecurrenceEstimate:
    interval_days: int | None
    confidence: float
    sample_count: int
    source: str | None


def estimate_recurrence(
    purchase_dates: Iterable[date | datetime],
    *,
    configured_interval_days: int | None = None,
) -> RecurrenceEstimate:
    """Estima o ciclo real sem deixar uma compra atipica dominar a previsao."""
    days = sorted(
        {
            value.date() if isinstance(value, datetime) else value
            for value in purchase_dates
            if value is not None
        }
    )
    intervals = [
        (current - previous).days
        for previous, current in zip(days, days[1:])
        if MIN_INTERVAL_DAYS <= (current - previous).days <= MAX_INTERVAL_DAYS
    ][-MAX_HISTORY_INTERVALS:]

    configured = _valid_interval(configured_interval_days)
    if len(intervals) < 2:
        return RecurrenceEstimate(
            configured,
            0.0,
            len(days),
            "configurado" if configured else None,
        )

    learned = max(MIN_INTERVAL_DAYS, min(MAX_INTERVAL_DAYS, round(median(intervals))))
    tolerance = max(2, round(learned * 0.25))
    consistent_ratio = sum(
        1 for interval in intervals if abs(interval - learned) <= tolerance
    ) / len(intervals)
    sample_factor = min(0.95, 0.55 + (0.10 * len(intervals)))
    confidence = round(consistent_ratio * sample_factor, 2)

    if confidence >= MIN_LEARNED_CONFIDENCE:
        return RecurrenceEstimate(learned, confidence, len(days), "aprendido")
    return RecurrenceEstimate(
        configured,
        confidence,
        len(days),
        "configurado" if configured else None,
    )


def notification_lead_days(interval_days: int) -> int:
    """Antecipa sem avisar cedo demais em ciclos curtos."""
    return min(7, max(1, interval_days // 4))


def process_finalized_sale_recurrence(
    db: Session,
    *,
    venda,
    tenant_id,
    user_id: int,
) -> dict:
    """Completa o ciclo anterior e cria a proxima oportunidade de recompra."""
    from app.models import Pet
    from app.produtos_models import Lembrete, Produto
    from app.vendas_models import Venda, VendaItem

    result = {"created": [], "completed": [], "skipped": []}
    if not getattr(venda, "cliente_id", None):
        return result

    purchase_at = getattr(venda, "data_finalizacao", None) or datetime.utcnow()
    processed: set[tuple[int, int | None]] = set()

    for item in getattr(venda, "itens", []):
        if getattr(item, "tipo", None) != "produto" or not getattr(
            item, "produto_id", None
        ):
            continue

        produto = (
            db.query(Produto)
            .filter(Produto.id == item.produto_id, Produto.tenant_id == tenant_id)
            .first()
        )
        if not produto:
            continue

        is_protocol = bool(
            getattr(produto, "numero_doses", None) and produto.numero_doses > 1
        )
        pet_id = item.pet_id if is_protocol else None
        key = (produto.id, pet_id)
        if key in processed:
            continue
        processed.add(key)

        pet = None
        if pet_id:
            pet = (
                db.query(Pet)
                .filter(
                    Pet.id == pet_id,
                    Pet.cliente_id == venda.cliente_id,
                    Pet.tenant_id == tenant_id,
                )
                .first()
            )
        if is_protocol and not pet:
            result["skipped"].append(
                {"produto": produto.nome, "motivo": "protocolo_sem_pet"}
            )
            continue

        processed_query = db.query(Lembrete.id).filter(
            Lembrete.tenant_id == tenant_id,
            Lembrete.venda_id == venda.id,
            Lembrete.produto_id == produto.id,
        )
        if is_protocol:
            processed_query = processed_query.filter(Lembrete.pet_id == pet_id)
        if processed_query.first():
            result["skipped"].append(
                {"produto": produto.nome, "motivo": "venda_ja_processada"}
            )
            continue

        purchase_rows = (
            db.query(Venda.data_finalizacao, Venda.data_venda)
            .join(VendaItem, VendaItem.venda_id == Venda.id)
            .filter(
                Venda.tenant_id == tenant_id,
                Venda.cliente_id == venda.cliente_id,
                Venda.status == "finalizada",
                VendaItem.produto_id == produto.id,
            )
            .order_by(Venda.data_finalizacao.asc(), Venda.data_venda.asc())
            .all()
        )
        purchase_dates = [
            finalized or sold
            for finalized, sold in purchase_rows
            if finalized or sold
        ]

        configured_interval = _valid_interval(
            getattr(produto, "intervalo_dias", None),
            minimum_days=1 if is_protocol else MIN_INTERVAL_DAYS,
        )
        if is_protocol:
            estimate = RecurrenceEstimate(
                configured_interval,
                1.0 if configured_interval else 0.0,
                len({value.date() for value in purchase_dates}),
                "configurado" if configured_interval else None,
            )
        else:
            estimate = estimate_recurrence(
                purchase_dates,
                configured_interval_days=configured_interval
                if getattr(produto, "tem_recorrencia", False)
                else None,
            )

        active_query = db.query(Lembrete).filter(
            Lembrete.tenant_id == tenant_id,
            Lembrete.cliente_id == venda.cliente_id,
            Lembrete.produto_id == produto.id,
            Lembrete.status.in_(["pendente", "notificado"]),
        )
        if is_protocol:
            active_query = active_query.filter(Lembrete.pet_id == pet_id)
        active = active_query.order_by(
            Lembrete.created_at.desc(), Lembrete.id.desc()
        ).all()
        previous = active[0] if active else None
        history = _history_from(previous)
        purchase_event = {
            "dose": previous.dose_atual if previous else 1,
            "data": purchase_at.isoformat(),
            "comprou": True,
            "status": "completado" if previous else "criado",
            "venda_id": venda.id,
        }
        updated_history = history + [purchase_event]
        for reminder in active:
            reminder.status = "completado"
            reminder.data_completado = purchase_at
            reminder.historico_doses = json.dumps(updated_history, ensure_ascii=False)
            result["completed"].append(reminder.id)

        if is_protocol:
            next_dose = previous.dose_atual + 1 if previous else 2
        else:
            next_dose = 1
        if (
            is_protocol
            and previous
            and previous.dose_total
            and previous.dose_atual >= previous.dose_total
        ):
            continue
        if not estimate.interval_days:
            result["skipped"].append(
                {"produto": produto.nome, "motivo": "historico_insuficiente"}
            )
            continue

        next_at = purchase_at + timedelta(days=estimate.interval_days)
        lead_days = notification_lead_days(estimate.interval_days)
        reminder = Lembrete(
            tenant_id=tenant_id,
            user_id=user_id,
            cliente_id=venda.cliente_id,
            pet_id=pet_id,
            produto_id=produto.id,
            venda_id=venda.id,
            data_compra=purchase_at,
            data_proxima_dose=next_at,
            data_notificacao_7_dias=next_at - timedelta(days=lead_days),
            status="pendente",
            metodo_notificacao="app",
            notificacao_enviada=False,
            quantidade_recomendada=float(item.quantidade),
            preco_estimado=float(produto.preco_venda or 0),
            dose_atual=next_dose,
            dose_total=produto.numero_doses if is_protocol else None,
            historico_doses=json.dumps(updated_history, ensure_ascii=False),
            origem_intervalo=estimate.source,
            intervalo_estimado_dias=estimate.interval_days,
            confianca_recorrencia=estimate.confidence,
            amostras_recorrencia=estimate.sample_count,
        )
        db.add(reminder)
        db.flush()
        result["created"].append(
            {
                "id": reminder.id,
                "produto": produto.nome,
                "pet": pet.nome if pet else None,
                "proxima_data": next_at.isoformat(),
                "intervalo_dias": estimate.interval_days,
                "origem": estimate.source,
                "confianca": estimate.confidence,
            }
        )

    return result


def run_due_recurrence_notifications(*, db_factory, logger_override=None) -> dict:
    """Enfileira no app os lembretes vencidos, por tenant e sem duplicacao."""
    from app.campaigns.models import NotificationQueue
    from app.campaigns.notification_service import enqueue_push
    from app.models import Tenant, User
    from app.produtos_models import Lembrete
    from app.tenancy.context import tenant_context

    log = logger_override or logger
    db = db_factory()
    stats = {"tenants": 0, "due": 0, "queued": 0}
    try:
        tenants = db.query(Tenant.id).filter(Tenant.status == "active").all()
        for (tenant_id,) in tenants:
            with tenant_context(tenant_id):
                try:
                    due = (
                        db.query(Lembrete)
                        .filter(
                            Lembrete.tenant_id == tenant_id,
                            Lembrete.status == "pendente",
                            Lembrete.notificacao_enviada.is_(False),
                            Lembrete.data_notificacao_7_dias <= datetime.utcnow(),
                        )
                        .order_by(Lembrete.data_notificacao_7_dias.asc())
                        .limit(200)
                        .all()
                    )
                    stats["tenants"] += 1
                    stats["due"] += len(due)
                    for reminder in due:
                        customer_email = str(
                            getattr(reminder.cliente, "email", "") or ""
                        ).strip().lower()
                        app_user = None
                        if customer_email:
                            app_user = (
                                db.query(User.id)
                                .filter(
                                    User.tenant_id == tenant_id,
                                    func.lower(User.email) == customer_email,
                                )
                                .first()
                            )
                        if not app_user:
                            # Sem conta no app ainda: preserva o lembrete para
                            # uma tentativa futura, sem enviar ao usuario errado.
                            continue

                        key = f"product_recurrence:{tenant_id}:{reminder.id}:app"
                        product_name = getattr(reminder.produto, "nome", "seu produto")
                        is_protocol = bool(
                            reminder.dose_total and reminder.dose_total > 1
                        )
                        body = (
                            f"A próxima dose de {product_name} está chegando. Confira no app."
                            if is_protocol
                            else f"Está na hora de repor {product_name}? Confira no app antes que acabe."
                        )
                        queued = enqueue_push(
                            db,
                            tenant_id=tenant_id,
                            customer_id=reminder.cliente_id,
                            subject="Lembrete CorePet",
                            body=body,
                            idempotency_key=key,
                            source="product_recurrence",
                            kind="repurchase_due",
                            payload={
                                "target": "product",
                                "reminder_id": reminder.id,
                                "produto_id": reminder.produto_id,
                                "product_id": reminder.produto_id,
                            },
                        )
                        exists = queued or db.query(NotificationQueue.id).filter(
                            NotificationQueue.idempotency_key == key
                        ).first() is not None
                        if exists:
                            reminder.notificacao_enviada = True
                            reminder.data_notificacao_enviada = datetime.utcnow()
                            reminder.status = "notificado"
                            reminder.metodo_notificacao = "app"
                            stats["queued"] += int(queued)
                    db.commit()
                except Exception:
                    db.rollback()
                    log.exception("[ProductRecurrence] Falha no tenant %s", tenant_id)
        return stats
    finally:
        db.close()


def _valid_interval(value, *, minimum_days: int = MIN_INTERVAL_DAYS) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if minimum_days <= parsed <= MAX_INTERVAL_DAYS else None


def _history_from(reminder) -> list[dict]:
    if not reminder or not reminder.historico_doses:
        return []
    try:
        value = json.loads(reminder.historico_doses)
        return value if isinstance(value, list) else []
    except (TypeError, ValueError):
        return []


__all__ = [
    "RecurrenceEstimate",
    "estimate_recurrence",
    "notification_lead_days",
    "process_finalized_sale_recurrence",
    "run_due_recurrence_notifications",
]
