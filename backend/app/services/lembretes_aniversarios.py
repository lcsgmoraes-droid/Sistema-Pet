"""Fila e histórico de contatos para aniversários de tutores e pets."""

from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy import and_, extract, func, or_
from sqlalchemy.orm import joinedload

from app.campaigns.models import NotificationQueue
from app.models import Cliente, Pet, User
from app.produtos_models import AniversarioContato
from app.services.lembretes_relacionamento import queue_status_value

BIRTHDAY_TYPES = ("tutor", "pet")


def _as_date(value) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    return value if isinstance(value, date) else None


def next_birthday(value, *, today: date | None = None) -> date | None:
    """Retorna a próxima ocorrência, tratando 29/02 como 28/02 em ano comum."""
    birth_date = _as_date(value)
    if birth_date is None:
        return None
    base = today or date.today()

    def occurrence(year: int) -> date:
        day = min(birth_date.day, monthrange(year, birth_date.month)[1])
        return date(year, birth_date.month, day)

    result = occurrence(base.year)
    return result if result >= base else occurrence(base.year + 1)


def birthday_message(
    *,
    customer_name: str | None,
    pet_name: str | None = None,
    days_until: int = 0,
) -> str:
    first_name = str(customer_name or "").strip().split()
    greeting = f"Olá, {first_name[0].title()}!" if first_name else "Olá!"
    if pet_name:
        name = str(pet_name).strip()
        moment = (
            f"Hoje é dia de comemorar o aniversário do {name}!"
            if days_until == 0
            else (
                f"Amanhã é aniversário do {name}!"
                if days_until == 1
                else f"O aniversário do {name} está chegando!"
            )
        )
        return (
            f"{greeting} {moment} 🐾🎂 Desejamos muita saúde, alegria e muitos "
            "momentos felizes juntos. Um carinho especial da nossa equipe!"
        )

    moment = (
        "Hoje é o seu aniversário!"
        if days_until == 0
        else (
            "Amanhã é o seu aniversário!"
            if days_until == 1
            else "O seu aniversário está chegando!"
        )
    )
    return (
        f"{greeting} {moment} 🎉 Desejamos um novo ciclo cheio de saúde, alegria e "
        "bons momentos. A nossa equipe está feliz em celebrar com você!"
    )


def _birthday_window_filter(column, *, start: date, end: date):
    pairs = set()
    current = start
    while current <= end:
        pairs.add((current.month, current.day))
        if (
            current.month == 2
            and current.day == 28
            and monthrange(current.year, 2)[1] == 28
        ):
            pairs.add((2, 29))
        current += timedelta(days=1)
    return or_(
        *(
            and_(extract("month", column) == month, extract("day", column) == day)
            for month, day in sorted(pairs)
        )
    )


@dataclass(frozen=True)
class BirthdayTarget:
    tipo: str
    referencia_id: int
    cliente: object
    pet: object | None
    nascimento: date
    aniversario_em: date


def get_birthday_target(
    db,
    *,
    tenant_id,
    birthday_type: str,
    reference_id: int,
    today: date | None = None,
) -> BirthdayTarget | None:
    if birthday_type not in BIRTHDAY_TYPES:
        return None
    base = today or date.today()
    if birthday_type == "tutor":
        customer = (
            db.query(Cliente)
            .filter(
                Cliente.id == reference_id,
                Cliente.tenant_id == tenant_id,
                Cliente.tipo_cadastro == "cliente",
                Cliente.ativo.isnot(False),
                Cliente.data_nascimento.isnot(None),
            )
            .first()
        )
        if customer is None:
            return None
        birth_date = _as_date(customer.data_nascimento)
        pet = None
    else:
        pet = (
            db.query(Pet)
            .options(joinedload(Pet.cliente))
            .join(Cliente, Cliente.id == Pet.cliente_id)
            .filter(
                Pet.id == reference_id,
                Pet.tenant_id == tenant_id,
                Pet.ativo.isnot(False),
                Pet.data_nascimento.isnot(None),
                Cliente.tenant_id == tenant_id,
                Cliente.ativo.isnot(False),
            )
            .first()
        )
        if pet is None or pet.cliente is None:
            return None
        customer = pet.cliente
        birth_date = _as_date(pet.data_nascimento)

    occurrence = next_birthday(birth_date, today=base)
    if birth_date is None or occurrence is None:
        return None
    return BirthdayTarget(
        tipo=birthday_type,
        referencia_id=reference_id,
        cliente=customer,
        pet=pet,
        nascimento=birth_date,
        aniversario_em=occurrence,
    )


def _serialize_contact(contact, queue=None) -> dict:
    status = queue_status_value(queue) or contact.status
    queue_results = {
        "enviado": "Notificação enviada pelo aplicativo",
        "falhou": "Falha no envio da notificação",
        "ignorado": "Envio ignorado por falta de destino válido",
        "pendente": "Notificação aguardando envio",
    }
    operator = getattr(contact, "operador", None)
    customer = getattr(contact, "cliente", None)
    pet = getattr(contact, "pet", None)
    return {
        "id": contact.id,
        "tipo_aniversario": contact.tipo,
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
        "pet_nome": getattr(pet, "nome", None),
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


def _load_contacts(db, *, tenant_id, start: date, end: date) -> list:
    return (
        db.query(AniversarioContato)
        .options(
            joinedload(AniversarioContato.operador),
            joinedload(AniversarioContato.cliente),
            joinedload(AniversarioContato.pet),
        )
        .filter(
            AniversarioContato.tenant_id == tenant_id,
            AniversarioContato.aniversario_em >= start,
            AniversarioContato.aniversario_em <= end,
        )
        .order_by(AniversarioContato.created_at.desc(), AniversarioContato.id.desc())
        .all()
    )


def list_birthday_contacts(db, *, tenant_id, target: BirthdayTarget) -> list[dict]:
    query = db.query(AniversarioContato).options(
        joinedload(AniversarioContato.operador),
        joinedload(AniversarioContato.cliente),
        joinedload(AniversarioContato.pet),
    )
    filters = [
        AniversarioContato.tenant_id == tenant_id,
        AniversarioContato.tipo == target.tipo,
        AniversarioContato.cliente_id == target.cliente.id,
        AniversarioContato.aniversario_em == target.aniversario_em,
    ]
    filters.append(
        AniversarioContato.pet_id == target.pet.id
        if target.pet is not None
        else AniversarioContato.pet_id.is_(None)
    )
    contacts = (
        query.filter(*filters)
        .order_by(AniversarioContato.created_at.desc(), AniversarioContato.id.desc())
        .all()
    )
    queues = _queue_map(db, contacts, tenant_id=tenant_id)
    return [
        _serialize_contact(contact, queues.get(contact.notification_queue_id))
        for contact in contacts
    ]


def list_upcoming_birthdays(
    db, *, tenant_id, days: int = 30, today: date | None = None
) -> dict:
    base = today or date.today()
    end = base + timedelta(days=days)
    customers = (
        db.query(Cliente)
        .filter(
            Cliente.tenant_id == tenant_id,
            Cliente.tipo_cadastro == "cliente",
            Cliente.ativo.isnot(False),
            Cliente.data_nascimento.isnot(None),
            _birthday_window_filter(Cliente.data_nascimento, start=base, end=end),
        )
        .all()
    )
    pets = (
        db.query(Pet)
        .options(joinedload(Pet.cliente))
        .join(Cliente, Cliente.id == Pet.cliente_id)
        .filter(
            Pet.tenant_id == tenant_id,
            Pet.ativo.isnot(False),
            Pet.data_nascimento.isnot(None),
            _birthday_window_filter(Pet.data_nascimento, start=base, end=end),
            Cliente.tenant_id == tenant_id,
            Cliente.ativo.isnot(False),
        )
        .all()
    )
    contacts = _load_contacts(db, tenant_id=tenant_id, start=base, end=end)
    queues = _queue_map(db, contacts, tenant_id=tenant_id)
    grouped: dict[tuple, list[dict]] = {}
    for contact in contacts:
        key = (
            contact.tipo,
            contact.pet_id if contact.tipo == "pet" else contact.cliente_id,
            contact.aniversario_em,
        )
        grouped.setdefault(key, []).append(
            _serialize_contact(contact, queues.get(contact.notification_queue_id))
        )

    customer_ids = {customer.id for customer in customers}
    customer_ids.update(pet.cliente_id for pet in pets if pet.cliente is not None)
    linked_customer_ids = {
        customer.id
        for customer in customers
        if customer.id in customer_ids and getattr(customer, "auth_user_id", None)
    }
    linked_customer_ids.update(
        pet.cliente_id
        for pet in pets
        if pet.cliente is not None and getattr(pet.cliente, "auth_user_id", None)
    )
    emails = {
        str(getattr(customer, "email", "") or "").strip().lower()
        for customer in customers
        if customer.id in customer_ids and getattr(customer, "email", None)
    }
    emails.update(
        str(getattr(pet.cliente, "email", "") or "").strip().lower()
        for pet in pets
        if pet.cliente is not None and getattr(pet.cliente, "email", None)
    )
    app_emails = set()
    if emails:
        rows = (
            db.query(User.email)
            .filter(User.tenant_id == tenant_id, func.lower(User.email).in_(emails))
            .all()
        )
        app_emails = {str(email or "").strip().lower() for (email,) in rows}

    items = []
    candidates = [
        ("tutor", customer.id, customer, None, customer.data_nascimento)
        for customer in customers
    ]
    candidates.extend(
        ("pet", pet.id, pet.cliente, pet, pet.data_nascimento)
        for pet in pets
        if pet.cliente is not None
    )
    for birthday_type, reference_id, customer, pet, birth_value in candidates:
        birth_date = _as_date(birth_value)
        occurrence = next_birthday(birth_date, today=base)
        if birth_date is None or occurrence is None or occurrence > end:
            continue
        days_until = (occurrence - base).days
        key = (birthday_type, reference_id, occurrence)
        event_contacts = grouped.get(key, [])
        latest = event_contacts[0] if event_contacts else None
        customer_email = str(getattr(customer, "email", "") or "").strip().lower()
        has_app = customer.id in linked_customer_ids or (
            customer_email and customer_email in app_emails
        )
        birthday_name = pet.nome if pet is not None else customer.nome
        items.append(
            {
                "id": f"{birthday_type}-{reference_id}-{occurrence.isoformat()}",
                "contato_tipo": "aniversario",
                "contato_chave": f"aniversario-{birthday_type}-{reference_id}",
                "tipo_aniversario": birthday_type,
                "referencia_id": reference_id,
                "cliente_id": customer.id,
                "cliente_nome": customer.nome,
                "cliente_telefone": customer.celular or customer.telefone,
                "cliente_tem_app": bool(has_app),
                "pet_nome": getattr(pet, "nome", None),
                "aniversariante_nome": birthday_name,
                "contexto_nome": (
                    f"Aniversário de {pet.nome}"
                    if pet is not None
                    else "Aniversário do tutor"
                ),
                "historico_titulo": "Histórico deste aniversário",
                "data_aniversario": occurrence.isoformat(),
                "dias_restantes": days_until,
                "idade": max(0, occurrence.year - birth_date.year),
                "mensagem_sugerida": birthday_message(
                    customer_name=customer.nome,
                    pet_name=getattr(pet, "nome", None),
                    days_until=days_until,
                ),
                "contatos_total": len(event_contacts),
                "ultimo_contato": latest,
                "contatado_hoje": bool(
                    latest
                    and latest.get("criado_em")
                    and datetime.fromisoformat(latest["criado_em"]).date() == base
                ),
            }
        )
    items.sort(
        key=lambda item: (
            item["dias_restantes"],
            item["tipo_aniversario"],
            str(item["aniversariante_nome"] or "").lower(),
        )
    )
    return {"total": len(items), "dias": days, "aniversariantes": items}
