"""Aprendizado de recompra e notificacoes de produtos recorrentes."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from statistics import median
from typing import Iterable

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

MIN_INTERVAL_DAYS = 3
MAX_INTERVAL_DAYS = 365
MAX_CONFIGURED_INTERVAL_DAYS = 3650
MIN_LEARNED_CONFIDENCE = 0.65
MAX_HISTORY_INTERVALS = 6


@dataclass(frozen=True)
class RecurrenceEstimate:
    interval_days: int | None
    confidence: float
    sample_count: int
    source: str | None


@dataclass(frozen=True)
class ProtocolNextStep:
    kind: str
    due_at: datetime
    dose_number: int
    dose_total: int
    protocol_start_at: datetime | None
    interval_days: int


def calculate_next_protocol_step(
    dose_offsets: Iterable[int],
    *,
    completed_dose: int,
    protocol_start_at: datetime,
    completed_at: datetime,
    restart_after_days: int | None = None,
) -> ProtocolNextStep | None:
    """Calcula a proxima etapa sem deslocar o protocolo por compra antecipada."""
    offsets = [int(value) for value in dose_offsets]
    if not offsets or offsets[0] != 0:
        return None

    if completed_dose < len(offsets):
        next_index = completed_dose
        interval_days = offsets[next_index] - offsets[next_index - 1]
        return ProtocolNextStep(
            kind="proxima_dose",
            due_at=protocol_start_at + timedelta(days=offsets[next_index]),
            dose_number=completed_dose + 1,
            dose_total=len(offsets),
            protocol_start_at=protocol_start_at,
            interval_days=max(interval_days, 1),
        )

    restart_days = _valid_interval(
        restart_after_days,
        minimum_days=1,
        maximum_days=MAX_CONFIGURED_INTERVAL_DAYS,
    )
    if not restart_days:
        return None
    return ProtocolNextStep(
        kind="reinicio_protocolo",
        due_at=completed_at + timedelta(days=restart_days),
        dose_number=1,
        dose_total=len(offsets),
        protocol_start_at=None,
        interval_days=restart_days,
    )


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

    configured = _valid_interval(
        configured_interval_days,
        minimum_days=1,
        maximum_days=MAX_CONFIGURED_INTERVAL_DAYS,
    )
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
    from app.produtos_models import Lembrete, Produto, ProdutoProtocoloRecorrencia
    from app.vendas.racao_previsao import resolver_previsao_fim_racao
    from app.vendas_models import Venda, VendaItem

    result = {"created": [], "completed": [], "skipped": []}
    if not getattr(venda, "cliente_id", None):
        return result

    purchase_at = getattr(venda, "data_finalizacao", None) or datetime.utcnow()
    processed: set[tuple[int, int | None, int | None]] = set()

    sale_items = (
        db.query(VendaItem)
        .filter(
            VendaItem.tenant_id == tenant_id,
            VendaItem.venda_id == venda.id,
        )
        .all()
    )

    for item in sale_items:
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
        if bool(getattr(item, "ignorar_recorrencia", False)):
            result["skipped"].append(
                {"produto": produto.nome, "motivo": "recorrencia_ignorada_na_venda"}
            )
            continue

        protocolos = (
            db.query(ProdutoProtocoloRecorrencia)
            .filter(
                ProdutoProtocoloRecorrencia.tenant_id == tenant_id,
                ProdutoProtocoloRecorrencia.produto_id == produto.id,
                ProdutoProtocoloRecorrencia.ativo.is_(True),
            )
            .all()
        )
        pet = _load_sale_pet(
            db,
            Pet,
            tenant_id=tenant_id,
            cliente_id=venda.cliente_id,
            pet_id=getattr(item, "pet_id", None),
        )
        protocolo = _resolve_sale_protocol(
            protocolos,
            requested_id=getattr(item, "protocolo_recorrencia_id", None),
            pet=pet,
        )
        if protocolos and not protocolo:
            result["skipped"].append(
                {"produto": produto.nome, "motivo": "protocolo_nao_selecionado"}
            )
            continue

        is_protocol = (
            protocolo.tipo == "protocolo_doses"
            if protocolo
            else bool(
                getattr(produto, "numero_doses", None) and produto.numero_doses > 1
            )
        )
        previsao_manual = (
            resolver_previsao_fim_racao(item, data_compra=purchase_at)
            if produto.eh_racao
            else None
        )
        pet_id = item.pet_id if is_protocol else None
        protocolo_id = protocolo.id if protocolo else None
        key = (produto.id, pet_id, protocolo_id)
        if key in processed:
            continue
        processed.add(key)

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
        if protocolo:
            processed_query = processed_query.filter(
                Lembrete.protocolo_recorrencia_id == protocolo.id
            )
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
            finalized or sold for finalized, sold in purchase_rows if finalized or sold
        ]

        configured_interval = _valid_interval(
            (
                protocolo.intervalo_recompra_dias
                if protocolo and protocolo.tipo == "recompra_continua"
                else getattr(produto, "intervalo_dias", None)
            ),
            minimum_days=1 if protocolo or is_protocol else MIN_INTERVAL_DAYS,
            maximum_days=MAX_CONFIGURED_INTERVAL_DAYS,
        )
        if previsao_manual:
            estimate = RecurrenceEstimate(
                previsao_manual.intervalo_dias,
                1.0,
                len({value.date() for value in purchase_dates}),
                previsao_manual.origem,
            )
        elif is_protocol:
            estimate = RecurrenceEstimate(
                None,
                1.0,
                len({value.date() for value in purchase_dates}),
                "configurado",
            )
        else:
            ajustar_ao_historico = protocolo.ajustar_ao_historico if protocolo else True
            estimate = (
                estimate_recurrence(
                    purchase_dates,
                    configured_interval_days=(
                        configured_interval
                        if protocolo or getattr(produto, "tem_recorrencia", False)
                        else None
                    ),
                )
                if ajustar_ao_historico
                else RecurrenceEstimate(
                    configured_interval,
                    1.0 if configured_interval else 0.0,
                    len({value.date() for value in purchase_dates}),
                    "configurado" if configured_interval else None,
                )
            )

        active_query = db.query(Lembrete).filter(
            Lembrete.tenant_id == tenant_id,
            Lembrete.cliente_id == venda.cliente_id,
            Lembrete.produto_id == produto.id,
            Lembrete.status.in_(["pendente", "notificado"]),
        )
        if is_protocol:
            active_query = active_query.filter(Lembrete.pet_id == pet_id)
        if protocolo:
            active_query = active_query.filter(
                Lembrete.protocolo_recorrencia_id == protocolo.id
            )
        active = active_query.order_by(
            Lembrete.created_at.desc(), Lembrete.id.desc()
        ).all()
        previous = active[0] if active else None
        history = _history_from(previous)
        previous_kind = getattr(previous, "tipo_lembrete", None)
        completed_dose = (
            1
            if previous_kind == "reinicio_protocolo"
            else previous.dose_atual if previous and is_protocol else 1
        )
        purchase_event = {
            "dose": completed_dose,
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

        next_step = None
        if is_protocol:
            if protocolo:
                dose_offsets = [
                    dose.dias_desde_inicio
                    for dose in sorted(
                        protocolo.doses, key=lambda dose: dose.numero_dose
                    )
                ]
                restart_after_days = protocolo.reiniciar_apos_dias
            else:
                total_doses = int(getattr(produto, "numero_doses", 0) or 0)
                dose_offsets = (
                    [index * configured_interval for index in range(total_doses)]
                    if configured_interval and total_doses > 0
                    else []
                )
                restart_after_days = None

            protocol_start_at = (
                purchase_at
                if not previous or previous_kind == "reinicio_protocolo"
                else getattr(previous, "data_inicio_protocolo", None)
                or previous.data_compra
                or purchase_at
            )
            next_step = calculate_next_protocol_step(
                dose_offsets,
                completed_dose=completed_dose,
                protocol_start_at=protocol_start_at,
                completed_at=purchase_at,
                restart_after_days=restart_after_days,
            )
            if not next_step:
                continue
        elif not estimate.interval_days:
            result["skipped"].append(
                {"produto": produto.nome, "motivo": "historico_insuficiente"}
            )
            continue

        next_at = (
            next_step.due_at
            if next_step
            else (
                previsao_manual.data_prevista
                if previsao_manual
                else purchase_at + timedelta(days=estimate.interval_days)
            )
        )
        interval_days = (
            next_step.interval_days if next_step else int(estimate.interval_days)
        )
        lead_days = notification_lead_days(interval_days)
        reminder = Lembrete(
            tenant_id=tenant_id,
            user_id=user_id,
            cliente_id=venda.cliente_id,
            pet_id=pet_id,
            produto_id=produto.id,
            venda_id=venda.id,
            protocolo_recorrencia_id=protocolo_id,
            data_compra=purchase_at,
            data_proxima_dose=next_at,
            data_notificacao_7_dias=next_at - timedelta(days=lead_days),
            data_inicio_protocolo=(next_step.protocol_start_at if next_step else None),
            status="pendente",
            metodo_notificacao="app",
            notificacao_enviada=False,
            tipo_lembrete=next_step.kind if next_step else "recompra",
            quantidade_recomendada=float(item.quantidade),
            preco_estimado=float(produto.preco_venda or 0),
            observacoes=(
                protocolo.observacoes
                if protocolo and protocolo.observacoes
                else (
                    "Previsão de término da ração informada no PDV."
                    if previsao_manual
                    else None
                )
            ),
            dose_atual=next_step.dose_number if next_step else 1,
            dose_total=next_step.dose_total if next_step else None,
            historico_doses=json.dumps(updated_history, ensure_ascii=False),
            origem_intervalo=estimate.source,
            intervalo_estimado_dias=interval_days,
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
                "protocolo": protocolo.nome if protocolo else None,
                "proxima_data": next_at.isoformat(),
                "intervalo_dias": interval_days,
                "tipo_lembrete": reminder.tipo_lembrete,
                "origem": estimate.source,
                "confianca": estimate.confidence,
            }
        )

    return result


def run_due_recurrence_notifications(*, db_factory, logger_override=None) -> dict:
    """Enfileira no app os lembretes vencidos, por tenant e sem duplicacao."""
    from app.campaigns.models import NotificationQueue
    from app.campaigns.notification_service import enqueue_push
    from app.models import Tenant
    from app.services.app_notifications import resolve_customer_app_user_id
    from app.produtos_models import Lembrete, LembreteContato
    from app.tenancy.context import tenant_context
    from app.vendas_models import Venda  # noqa: F401 - registra a FK de lembretes

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
                    tenant_queued = 0
                    for reminder in due:
                        app_user_id = resolve_customer_app_user_id(
                            db,
                            tenant_id=tenant_id,
                            cliente=reminder.cliente,
                        )
                        if not app_user_id:
                            # Sem conta no app ainda: preserva o lembrete para
                            # uma tentativa futura, sem enviar ao usuario errado.
                            continue

                        key = f"product_recurrence:{tenant_id}:{reminder.id}:app"
                        product_name = getattr(reminder.produto, "nome", "seu produto")
                        reminder_kind = getattr(reminder, "tipo_lembrete", "recompra")
                        if reminder_kind == "reinicio_protocolo":
                            body = (
                                f"Está na hora de iniciar um novo protocolo de "
                                f"{product_name}. Confira no app."
                            )
                        elif reminder_kind == "proxima_dose":
                            body = (
                                f"A dose {reminder.dose_atual}/{reminder.dose_total} "
                                f"de {product_name} está chegando. Confira no app."
                            )
                        else:
                            body = (
                                f"Está na hora de repor {product_name}? "
                                "Confira no app antes que acabe."
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
                                "recurrence_kind": reminder_kind,
                            },
                        )
                        # TODO(WhatsApp): quando o modulo estiver operacional,
                        # enfileirar este mesmo evento no canal WhatsApp, com a
                        # mesma idempotencia e respeitando o consentimento.
                        queue = (
                            db.query(NotificationQueue)
                            .filter(NotificationQueue.idempotency_key == key)
                            .first()
                        )
                        exists = queued or queue is not None
                        if exists:
                            if queue is None:
                                db.flush()
                                queue = (
                                    db.query(NotificationQueue)
                                    .filter(NotificationQueue.idempotency_key == key)
                                    .first()
                                )
                            contact_key = f"contact:{key}"
                            contact_exists = (
                                db.query(LembreteContato.id)
                                .filter(
                                    LembreteContato.tenant_id == tenant_id,
                                    LembreteContato.idempotency_key == contact_key,
                                )
                                .first()
                            )
                            if not contact_exists:
                                db.add(
                                    LembreteContato(
                                        tenant_id=tenant_id,
                                        lembrete_id=reminder.id,
                                        cliente_id=reminder.cliente_id,
                                        produto_id=reminder.produto_id,
                                        usuario_id=None,
                                        notification_queue_id=(
                                            queue.id if queue is not None else None
                                        ),
                                        canal="push",
                                        acao="push_automatico",
                                        status="pendente",
                                        mensagem=body,
                                        resultado="Notificação automática enfileirada",
                                        idempotency_key=contact_key,
                                    )
                                )
                            reminder.notificacao_enviada = True
                            reminder.data_notificacao_enviada = datetime.utcnow()
                            reminder.status = "notificado"
                            reminder.metodo_notificacao = "app"
                            tenant_queued += int(queued)
                    db.commit()
                    stats["tenants"] += 1
                    stats["due"] += len(due)
                    stats["queued"] += tenant_queued
                except Exception:
                    db.rollback()
                    log.exception("[ProductRecurrence] Falha no tenant %s", tenant_id)
        return stats
    finally:
        db.close()


def _load_sale_pet(db, Pet, *, tenant_id, cliente_id, pet_id):
    if not pet_id:
        return None
    return (
        db.query(Pet)
        .filter(
            Pet.id == pet_id,
            Pet.cliente_id == cliente_id,
            Pet.tenant_id == tenant_id,
        )
        .first()
    )


def _normalize_species(value: str | None) -> str | None:
    normalized = str(value or "").strip().lower()
    if normalized in {"dog", "cao", "cão", "canino", "cachorro"}:
        return "dog"
    if normalized in {"cat", "gato", "felino"}:
        return "cat"
    return normalized or None


def _pet_life_stage(pet) -> str | None:
    months = getattr(pet, "idade_aproximada", None)
    if months is None and getattr(pet, "data_nascimento", None):
        born = pet.data_nascimento
        born_date = born.date() if isinstance(born, datetime) else born
        months = max((date.today() - born_date).days // 30, 0)
    if months is None:
        return None
    return "puppy" if int(months) < 12 else "adult"


def _protocol_matches_pet(protocol, pet) -> bool:
    species = getattr(protocol, "especie_compativel", "both") or "both"
    if species != "both":
        if not pet or _normalize_species(getattr(pet, "especie", None)) != species:
            return False

    phase = getattr(protocol, "fase_vida", "all") or "all"
    if phase == "all":
        return True
    stage = _pet_life_stage(pet) if pet else None
    if stage is None:
        return False
    return stage == phase


def _resolve_sale_protocol(protocols, *, requested_id, pet):
    if requested_id is not None:
        return next(
            (item for item in protocols if item.id == int(requested_id)), None
        )

    compatible = [
        item for item in protocols if _protocol_matches_pet(item, pet)
    ]
    return compatible[0] if len(compatible) == 1 else None


def _valid_interval(
    value,
    *,
    minimum_days: int = MIN_INTERVAL_DAYS,
    maximum_days: int = MAX_INTERVAL_DAYS,
) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if minimum_days <= parsed <= maximum_days else None


def _history_from(reminder) -> list[dict]:
    if not reminder or not reminder.historico_doses:
        return []
    try:
        value = json.loads(reminder.historico_doses)
        return value if isinstance(value, list) else []
    except (TypeError, ValueError):
        return []


__all__ = [
    "ProtocolNextStep",
    "RecurrenceEstimate",
    "calculate_next_protocol_step",
    "estimate_recurrence",
    "notification_lead_days",
    "process_finalized_sale_recurrence",
    "run_due_recurrence_notifications",
]
