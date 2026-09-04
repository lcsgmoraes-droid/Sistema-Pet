"""Leitura, mensagens e historico da central de lembretes."""

from __future__ import annotations

import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app.campaigns.models import NotificationQueue
from app.models import User
from app.produtos_models import Lembrete, LembreteContato

ACTIVE_REMINDER_STATUSES = ("pendente", "notificado")
QUEUE_STATUS_LABELS = {
    "pending": "pendente",
    "sent": "enviado",
    "failed": "falhou",
    "skipped": "ignorado",
}


def _plain(value) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(char for char in text if not unicodedata.combining(char)).lower()


def _first_name(value) -> str:
    parts = str(value or "").strip().split()
    return parts[0].title() if parts else ""


def classify_reminder(reminder) -> str:
    """Classifica a oportunidade sem confundir protocolo com ciclo aprendido."""
    recurrence_kind = getattr(reminder, "tipo_lembrete", None)
    if recurrence_kind == "reinicio_protocolo":
        return "reinicio_protocolo"
    if recurrence_kind == "proxima_dose":
        return "proxima_dose"
    if (getattr(reminder, "dose_total", None) or 0) > 1:
        return "protocolo"
    product = getattr(reminder, "produto", None)
    if product is not None and bool(getattr(product, "eh_racao", False)):
        return "racao"
    if _plain(getattr(reminder, "origem_intervalo", None)).startswith("aprendido"):
        return "ciclo_aprendido"
    return "recorrencia"


def suggested_message(reminder) -> str:
    """Gera um rascunho simples e contextual, sempre editavel pelo operador."""
    customer = getattr(reminder, "cliente", None)
    product = getattr(reminder, "produto", None)
    pet = getattr(reminder, "pet", None)
    customer_name = _first_name(getattr(customer, "nome", None))
    product_name = str(getattr(product, "nome", None) or "o produto").strip()
    pet_name = _first_name(getattr(pet, "nome", None))
    greeting = f"Olá, {customer_name}!" if customer_name else "Olá!"
    pet_reference = f" do {pet_name}" if pet_name else ""
    searchable_name = _plain(product_name)
    reminder_type = classify_reminder(reminder)

    if reminder_type == "reinicio_protocolo":
        context = (
            f"Está chegando o momento planejado para iniciar um novo protocolo de "
            f"{product_name}{pet_reference}."
        )
    elif re.search(
        r"carrapat|pulga|antiparasit|nexgard|simparic|bravecto", searchable_name
    ):
        context = (
            "Manter a proteção contra pulgas e carrapatos em dia ajuda a cuidar "
            f"da saúde e do bem-estar{pet_reference}."
        )
    elif re.search(r"vacina|v8|v10|antirrab", searchable_name):
        context = (
            f"Manter o protocolo de vacinação{pet_reference} em dia ajuda a preservar "
            "a proteção planejada."
        )
    elif reminder_type == "racao":
        context = (
            f"Pela previsão de consumo, {product_name} pode estar perto de acabar. "
            "Evitar interrupções ajuda a manter a rotina de alimentação."
        )
    elif reminder_type in {"protocolo", "proxima_dose"}:
        context = (
            f"Está chegando a data da próxima etapa de {product_name}{pet_reference}. "
            "Manter o protocolo em dia ajuda a seguir o cuidado planejado."
        )
    else:
        context = f"Está chegando o período previsto para repor {product_name}."

    return f"{greeting} {context} Quer que eu separe para você?"


def queue_status_value(queue) -> str | None:
    if queue is None:
        return None
    raw = getattr(queue, "status", None)
    value = getattr(raw, "value", raw)
    return QUEUE_STATUS_LABELS.get(str(value), str(value) if value else None)


def serialize_contact(contact, queue=None) -> dict:
    operator = getattr(contact, "operador", None)
    customer = getattr(contact, "cliente", None)
    product = getattr(contact, "produto", None)
    status = queue_status_value(queue) or contact.status
    queue_results = {
        "enviado": "Notificação enviada pelo aplicativo",
        "falhou": "Falha no envio da notificação",
        "ignorado": "Envio ignorado por falta de destino válido",
        "pendente": "Notificação aguardando envio",
    }
    return {
        "id": contact.id,
        "lembrete_id": contact.lembrete_id,
        "canal": contact.canal,
        "acao": contact.acao,
        "status": status,
        "mensagem": contact.mensagem,
        "resultado": (
            queue_results.get(status, contact.resultado)
            if queue is not None
            else contact.resultado
        ),
        "cliente_nome": getattr(customer, "nome", None),
        "produto_nome": getattr(product, "nome", None),
        "operador_nome": getattr(operator, "nome", None),
        "criado_em": contact.created_at.isoformat() if contact.created_at else None,
    }


def _queue_map(db, contacts, *, tenant_id) -> dict:
    queue_ids = {
        contact.notification_queue_id
        for contact in contacts
        if contact.notification_queue_id is not None
    }
    if not queue_ids:
        return {}
    queues = (
        db.query(NotificationQueue)
        .filter(
            NotificationQueue.tenant_id == tenant_id,
            NotificationQueue.id.in_(queue_ids),
        )
        .all()
    )
    return {queue.id: queue for queue in queues}


def _contact_groups(db, *, tenant_id, reminder_ids) -> dict[int, list]:
    if not reminder_ids:
        return {}
    contacts = (
        db.query(LembreteContato)
        .options(
            joinedload(LembreteContato.operador),
            joinedload(LembreteContato.cliente),
            joinedload(LembreteContato.produto),
        )
        .filter(
            LembreteContato.tenant_id == tenant_id,
            LembreteContato.lembrete_id.in_(reminder_ids),
        )
        .order_by(LembreteContato.created_at.desc(), LembreteContato.id.desc())
        .all()
    )
    queues = _queue_map(db, contacts, tenant_id=tenant_id)
    grouped = defaultdict(list)
    for contact in contacts:
        grouped[contact.lembrete_id].append(
            serialize_contact(contact, queues.get(contact.notification_queue_id))
        )
    return grouped


def list_active_reminders(db, *, tenant_id) -> dict:
    reminders = (
        db.query(Lembrete)
        .options(
            joinedload(Lembrete.cliente),
            joinedload(Lembrete.pet),
            joinedload(Lembrete.produto),
        )
        .filter(
            Lembrete.tenant_id == tenant_id,
            Lembrete.status.in_(ACTIVE_REMINDER_STATUSES),
        )
        .order_by(Lembrete.data_proxima_dose.asc())
        .all()
    )
    grouped = _contact_groups(
        db, tenant_id=tenant_id, reminder_ids=[reminder.id for reminder in reminders]
    )
    linked_customer_ids = {
        reminder.cliente_id
        for reminder in reminders
        if reminder.cliente and getattr(reminder.cliente, "auth_user_id", None)
    }
    customer_emails = {
        str(getattr(reminder.cliente, "email", "") or "").strip().lower()
        for reminder in reminders
        if reminder.cliente and getattr(reminder.cliente, "email", None)
    }
    app_emails = set()
    if customer_emails:
        rows = (
            db.query(User.email)
            .filter(
                User.tenant_id == tenant_id,
                func.lower(User.email).in_(customer_emails),
            )
            .all()
        )
        app_emails = {str(email or "").strip().lower() for (email,) in rows}
    today = datetime.utcnow().date()
    payload = []
    for reminder in reminders:
        contacts = grouped.get(reminder.id, [])
        latest = contacts[0] if contacts else None
        customer = reminder.cliente
        product = reminder.produto
        customer_email = str(getattr(customer, "email", "") or "").strip().lower()
        customer_has_app = reminder.cliente_id in linked_customer_ids or (
            customer_email and customer_email in app_emails
        )
        payload.append(
            {
                "id": reminder.id,
                "cliente_id": reminder.cliente_id,
                "cliente_nome": getattr(customer, "nome", None),
                "cliente_telefone": (
                    getattr(customer, "celular", None)
                    or getattr(customer, "telefone", None)
                ),
                "cliente_tem_app": bool(customer_has_app),
                "pet_nome": getattr(reminder.pet, "nome", None),
                "produto_id": reminder.produto_id,
                "produto_nome": getattr(product, "nome", None),
                "tipo_lembrete": classify_reminder(reminder),
                "data_compra": (
                    reminder.data_compra.isoformat() if reminder.data_compra else None
                ),
                "data_proxima_dose": reminder.data_proxima_dose.isoformat(),
                "dias_restantes": (reminder.data_proxima_dose.date() - today).days,
                "status": reminder.status,
                "quantidade": reminder.quantidade_recomendada,
                "preco_estimado": reminder.preco_estimado,
                "dose_atual": reminder.dose_atual,
                "dose_total": reminder.dose_total,
                "origem_intervalo": reminder.origem_intervalo,
                "intervalo_estimado_dias": reminder.intervalo_estimado_dias,
                "confianca_recorrencia": reminder.confianca_recorrencia,
                "amostras_recorrencia": reminder.amostras_recorrencia,
                "mensagem_sugerida": suggested_message(reminder),
                "contatos_total": len(contacts),
                "ultimo_contato": latest,
                "contatado_hoje": bool(
                    latest
                    and latest.get("criado_em")
                    and datetime.fromisoformat(latest["criado_em"]).date() == today
                ),
            }
        )
    return {"total": len(payload), "lembretes": payload}


def get_active_reminder(db, *, tenant_id, reminder_id: int):
    return (
        db.query(Lembrete)
        .options(
            joinedload(Lembrete.cliente),
            joinedload(Lembrete.pet),
            joinedload(Lembrete.produto),
        )
        .filter(
            Lembrete.id == reminder_id,
            Lembrete.tenant_id == tenant_id,
            Lembrete.status.in_(ACTIVE_REMINDER_STATUSES),
        )
        .first()
    )


def list_contacts(db, *, tenant_id, reminder_id: int) -> list[dict]:
    grouped = _contact_groups(db, tenant_id=tenant_id, reminder_ids=[reminder_id])
    return grouped.get(reminder_id, [])


def build_report(db, *, tenant_id, days: int) -> dict:
    since = datetime.utcnow() - timedelta(days=days)
    contacts = (
        db.query(LembreteContato)
        .options(
            joinedload(LembreteContato.operador),
            joinedload(LembreteContato.cliente),
            joinedload(LembreteContato.produto),
        )
        .filter(
            LembreteContato.tenant_id == tenant_id,
            LembreteContato.created_at >= since,
        )
        .order_by(LembreteContato.created_at.desc(), LembreteContato.id.desc())
        .all()
    )
    queues = _queue_map(db, contacts, tenant_id=tenant_id)
    serialized = [
        serialize_contact(contact, queues.get(contact.notification_queue_id))
        for contact in contacts
    ]
    reminder_ids = {contact.lembrete_id for contact in contacts}
    first_contact = {}
    for contact in contacts:
        current = first_contact.get(contact.lembrete_id)
        if current is None or contact.created_at < current:
            first_contact[contact.lembrete_id] = contact.created_at
    reminders = (
        db.query(Lembrete)
        .filter(
            Lembrete.tenant_id == tenant_id,
            Lembrete.id.in_(reminder_ids),
        )
        .all()
        if reminder_ids
        else []
    )
    conversions = sum(
        1
        for reminder in reminders
        if reminder.status == "completado"
        and reminder.data_completado
        and reminder.data_completado.date() >= first_contact.get(reminder.id).date()
    )
    status_counts = Counter(item["status"] for item in serialized)
    channel_counts = Counter(item["canal"] for item in serialized)
    opportunities = len(reminder_ids)
    return {
        "periodo_dias": days,
        "contatos_total": len(contacts),
        "oportunidades_contatadas": opportunities,
        "recompras_apos_contato": conversions,
        "taxa_conversao": (
            round((conversions / opportunities * 100), 1) if opportunities else 0
        ),
        "por_canal": dict(channel_counts),
        "por_status": dict(status_counts),
        "historico": serialized[:50],
    }
