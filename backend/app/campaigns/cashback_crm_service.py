"""Saldos reais e eventos de acompanhamento do CRM de cashback."""

from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal
from math import ceil
import re
from urllib.parse import urlencode

from fastapi import HTTPException
from sqlalchemy import case, func
from sqlalchemy.exc import IntegrityError

from app.campaigns.cashback_crm_models import CashbackContato
from app.campaigns.cashback_wallet import (
    get_cashback_wallet,
    replay_cashback_transactions,
)
from app.campaigns.models import CashbackTransaction
from app.campaigns.notification_service import (
    _CONSENT_ALIASES,
    can_send_marketing_whatsapp,
)
from app.models import Cliente
from app.utils.timezone import now_brasilia
from app.whatsapp.security import DataPrivacyConsent
from app.whatsapp.tenant_context import whatsapp_tenant_context


CRM_STATUSES = (
    "sem_contato",
    "conversa_aberta",
    "mensagem_enviada",
    "aguardando_retorno",
    "interessado",
    "retornar_depois",
    "concluido",
    "sem_interesse",
    "nao_contatar",
)


def pagination(page, per_page, total):
    return {
        "pagina": page,
        "por_pagina": per_page,
        "total": total,
        "paginas": max(1, ceil(total / per_page)),
    }


def normalize_phone(value):
    """Converte telefone brasileiro com DDD ou número internacional para wa.me."""
    raw = str(value or "").strip()
    digits = re.sub(r"\D", "", raw)
    if raw.startswith("+"):
        if digits.startswith("55"):
            return digits if len(digits) in (12, 13) else None
        return (
            digits if 10 <= len(digits) <= 15 and not digits.startswith("0") else None
        )
    if len(digits) in (10, 11) and not digits.startswith("0"):
        return f"55{digits}"
    if digits.startswith("55") and len(digits) in (12, 13):
        return digits
    return None


def customer_phone(customer):
    for value in (customer.celular, customer.telefone):
        phone = normalize_phone(value)
        if phone:
            return phone
    return None


def whatsapp_url(contact):
    return f"https://wa.me/{contact.telefone}?{urlencode({'text': contact.mensagem})}"


def serialize_contact(contact):
    return {
        "id": contact.id,
        "acao": contact.acao,
        "status": contact.status,
        "mensagem": contact.mensagem,
        "observacao": contact.observacao,
        "proximo_contato_em": contact.proximo_contato_em.isoformat()
        if contact.proximo_contato_em
        else None,
        "operador_nome": contact.operador_nome,
        "criado_em": contact.created_at.isoformat() if contact.created_at else None,
        "saldo_cashback": float(contact.saldo_cashback),
    }


def get_customer(db, *, tenant_id, customer_id, lock=False):
    query = db.query(Cliente).filter(
        Cliente.tenant_id == tenant_id, Cliente.id == customer_id
    )
    if lock:
        query = query.with_for_update()
    customer = query.first()
    if customer is None:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return customer


def _latest_contact(db, *, tenant_id, customer_id):
    return (
        db.query(CashbackContato)
        .filter(
            CashbackContato.tenant_id == tenant_id,
            CashbackContato.cliente_id == customer_id,
        )
        .order_by(CashbackContato.id.desc())
        .first()
    )


def _contact_summaries(db, *, tenant_id, customer_id=None):
    query = db.query(
        CashbackContato.cliente_id.label("cliente_id"),
        func.max(CashbackContato.id).label("ultimo_id"),
        func.count(CashbackContato.id).label("total"),
        func.max(
            case(
                (CashbackContato.acao == "conversa_aberta", CashbackContato.created_at),
                else_=None,
            )
        ).label("ultimo_contato"),
    ).filter(CashbackContato.tenant_id == tenant_id)
    if customer_id is not None:
        query = query.filter(CashbackContato.cliente_id == customer_id)
    summary = query.group_by(CashbackContato.cliente_id).subquery()
    rows = (
        db.query(CashbackContato, summary.c.total, summary.c.ultimo_contato)
        .join(
            summary,
            CashbackContato.id == summary.c.ultimo_id,
        )
        .filter(CashbackContato.tenant_id == tenant_id)
        .all()
    )
    return {
        contact.cliente_id: (contact, total, last_open)
        for contact, total, last_open in rows
    }


def _blocked_by_consent(db, *, tenant_id):
    """Mesmo último consentimento do serviço oficial, consultado em lote."""
    with whatsapp_tenant_context(tenant_id):
        consents = (
            db.query(DataPrivacyConsent)
            .filter(
                DataPrivacyConsent.tenant_id == tenant_id,
                DataPrivacyConsent.subject_type == "customer",
                DataPrivacyConsent.consent_type.in_(
                    _CONSENT_ALIASES["marketing_whatsapp"]
                ),
            )
            .order_by(
                DataPrivacyConsent.created_at.desc(), DataPrivacyConsent.id.desc()
            )
            .all()
        )
    latest = {}
    for consent in consents:
        latest.setdefault(consent.subject_id, consent)
    return {
        subject
        for subject, consent in latest.items()
        if not consent.consent_given or consent.revoked_at is not None
    }


def _expiry(rows, wallet):
    active = [
        tx
        for tx in rows
        if wallet.remaining_by_credit.get(tx.id, 0) > 0 and tx.expires_at
    ]
    if not active:
        return None, 0.0
    expiry = min(tx.expires_at for tx in active)
    amount = sum(
        (wallet.remaining_by_credit[tx.id] for tx in active if tx.expires_at == expiry),
        Decimal("0.00"),
    )
    return expiry.isoformat(), float(amount)


def _serialize_customer(customer, *, wallet, transactions, contact_summary, opted_out):
    latest, count, last_open = contact_summary
    status = latest.status if latest else "sem_contato"
    next_contact = latest.proximo_contato_em if latest else None
    phone = customer_phone(customer)
    reason = None
    if status == "nao_contatar":
        reason = "Cliente marcado como não contatar neste acompanhamento"
    elif opted_out:
        reason = "Cliente não autorizou contatos de marketing pelo WhatsApp"
    elif not phone:
        reason = "Cliente sem telefone válido com DDD"
    elif wallet.available <= 0:
        reason = "Cliente não possui mais saldo de cashback disponível"
    expiry, expiry_amount = _expiry(transactions, wallet)
    return {
        "cliente_id": customer.id,
        "codigo": customer.codigo,
        "nome": customer.nome,
        "ativo": customer.ativo is not False,
        "telefone": phone or customer.celular or customer.telefone,
        "saldo_cashback": float(wallet.available),
        "proxima_expiracao": expiry,
        "valor_a_expirar": expiry_amount,
        "status": status,
        "ultimo_contato": last_open.isoformat() if last_open else None,
        "total_contatos": int(count),
        "proximo_contato_em": next_contact.isoformat() if next_contact else None,
        "whatsapp_disponivel": reason is None,
        "motivo_bloqueio": reason,
    }


def customer_snapshot(db, *, tenant_id, customer_id):
    """Atualiza o modal mesmo quando o cliente saiu da lista por saldo ou filtros."""
    customer = get_customer(db, tenant_id=tenant_id, customer_id=customer_id)
    now = datetime.now(timezone.utc)
    transactions = (
        db.query(CashbackTransaction)
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.customer_id == customer_id,
            CashbackTransaction.created_at <= now,
        )
        .order_by(CashbackTransaction.id)
        .all()
    )
    summaries = _contact_summaries(db, tenant_id=tenant_id, customer_id=customer_id)
    return _serialize_customer(
        customer,
        wallet=replay_cashback_transactions(transactions, as_of=now),
        transactions=transactions,
        contact_summary=summaries.get(customer_id, (None, 0, None)),
        opted_out=not can_send_marketing_whatsapp(
            db, tenant_id=tenant_id, customer_id=customer_id
        ),
    )


def list_customers(
    db, *, tenant_id, search=None, crm_status=None, due_only=False, page=1, per_page=25
):
    now = datetime.now(timezone.utc)
    today = now_brasilia().date()
    ledger = (
        db.query(CashbackTransaction)
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.created_at <= now,
        )
        .order_by(CashbackTransaction.customer_id, CashbackTransaction.id)
        .all()
    )
    grouped = defaultdict(list)
    for tx in ledger:
        grouped[tx.customer_id].append(tx)
    wallets = {
        customer_id: replay_cashback_transactions(rows, as_of=now)
        for customer_id, rows in grouped.items()
    }
    positive_ids = {
        customer_id for customer_id, wallet in wallets.items() if wallet.available > 0
    }
    if not positive_ids:
        return {
            "clientes": [],
            "resumo": {
                "total_clientes": 0,
                "saldo_total": 0.0,
                "sem_contato": 0,
                "retornos_pendentes": 0,
            },
            "paginacao": pagination(page, per_page, 0),
        }

    # Uma consulta de cadastro; evita uma consulta de carteira por pessoa e limite oculto.
    customers = db.query(Cliente).filter(Cliente.tenant_id == tenant_id).all()
    summaries = _contact_summaries(db, tenant_id=tenant_id)
    blocked = _blocked_by_consent(db, tenant_id=tenant_id)
    result = []
    for customer in customers:
        if customer.id not in positive_ids:
            continue
        result.append(
            _serialize_customer(
                customer,
                wallet=wallets[customer.id],
                transactions=grouped[customer.id],
                contact_summary=summaries.get(customer.id, (None, 0, None)),
                opted_out=str(customer.id) in blocked,
            )
        )
    summary = {
        "total_clientes": len(result),
        "saldo_total": float(
            sum(
                (wallets[row["cliente_id"]].available for row in result),
                Decimal("0.00"),
            )
        ),
        "sem_contato": sum(row["status"] == "sem_contato" for row in result),
        "retornos_pendentes": sum(
            bool(
                row["proximo_contato_em"]
                and date.fromisoformat(row["proximo_contato_em"]) <= today
            )
            for row in result
        ),
    }
    term = str(search or "").strip().casefold()
    if term:
        result = [
            row
            for row in result
            if any(
                term in str(row[key] or "").casefold()
                for key in ("nome", "codigo", "telefone")
            )
        ]
    if crm_status:
        result = [row for row in result if row["status"] == crm_status]
    if due_only:
        result = [
            row
            for row in result
            if row["proximo_contato_em"]
            and date.fromisoformat(row["proximo_contato_em"]) <= today
        ]
    result.sort(
        key=lambda row: (
            -row["saldo_cashback"],
            str(row["nome"] or "").casefold(),
            row["cliente_id"],
        )
    )
    total = len(result)
    start = (page - 1) * per_page
    return {
        "clientes": result[start : start + per_page],
        "resumo": summary,
        "paginacao": pagination(page, per_page, total),
    }


def list_contacts(db, *, tenant_id, customer_id, page=1, per_page=25):
    get_customer(db, tenant_id=tenant_id, customer_id=customer_id)
    query = db.query(CashbackContato).filter(
        CashbackContato.tenant_id == tenant_id,
        CashbackContato.cliente_id == customer_id,
    )
    total = query.count()
    contacts = (
        query.order_by(CashbackContato.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return {
        "contatos": [serialize_contact(contact) for contact in contacts],
        "total": total,
        "paginacao": pagination(page, per_page, total),
    }


def _existing(db, *, tenant_id, customer_id, action, request_key):
    return (
        db.query(CashbackContato)
        .filter(
            CashbackContato.tenant_id == tenant_id,
            CashbackContato.cliente_id == customer_id,
            CashbackContato.acao == action,
            CashbackContato.chave_cliente == str(request_key),
        )
        .first()
    )


def _save(db, contact):
    tenant_id, customer_id, action, key = (
        contact.tenant_id,
        contact.cliente_id,
        contact.acao,
        contact.chave_cliente,
    )
    db.add(contact)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = _existing(
            db,
            tenant_id=tenant_id,
            customer_id=customer_id,
            action=action,
            request_key=key,
        )
        if existing:
            return existing
        raise
    db.refresh(contact)
    return contact


def create_contact(
    db,
    *,
    tenant_id,
    customer_id,
    user,
    request_key,
    message=None,
    crm_status=None,
    note=None,
    next_contact=None,
):
    customer = get_customer(db, tenant_id=tenant_id, customer_id=customer_id, lock=True)
    action = "conversa_aberta" if message is not None else "acompanhamento"
    previous = _existing(
        db,
        tenant_id=tenant_id,
        customer_id=customer_id,
        action=action,
        request_key=request_key,
    )
    if previous and action != "conversa_aberta":
        return previous
    latest = _latest_contact(db, tenant_id=tenant_id, customer_id=customer_id)
    balance = get_cashback_wallet(
        db, tenant_id=tenant_id, customer_id=customer_id
    ).available
    phone = None
    if action == "conversa_aberta":
        message = str(message).strip()
        if not message or len(message) > 2000:
            raise HTTPException(
                status_code=422, detail="Informe uma mensagem de até 2.000 caracteres"
            )
        if latest and latest.status == "nao_contatar":
            raise HTTPException(
                status_code=403,
                detail="Cliente marcado como não contatar neste acompanhamento",
            )
        if balance <= 0:
            raise HTTPException(
                status_code=409,
                detail="Cliente não possui mais saldo de cashback disponível. Atualize a lista.",
            )
        phone = customer_phone(customer)
        if not phone:
            raise HTTPException(
                status_code=422, detail="Cliente sem telefone válido com DDD"
            )
        if not can_send_marketing_whatsapp(
            db, tenant_id=tenant_id, customer_id=customer_id
        ):
            raise HTTPException(
                status_code=403,
                detail="Cliente não autorizou contatos de marketing pelo WhatsApp",
            )
        # Uma repetição não pode reabrir o link após bloqueio ou consumo do saldo.
        if previous:
            return previous
        crm_status = (
            latest.status
            if latest and latest.status != "sem_contato"
            else "conversa_aberta"
        )
        next_contact = latest.proximo_contato_em if latest else None
    elif crm_status not in CRM_STATUSES:
        raise HTTPException(status_code=422, detail="Status de acompanhamento inválido")
    note = str(note or "").strip() or None
    if note and len(note) > 2000:
        raise HTTPException(
            status_code=422, detail="A observação deve ter até 2.000 caracteres"
        )
    if crm_status == "retornar_depois" and next_contact is None:
        raise HTTPException(status_code=422, detail="Informe a data do próximo contato")
    if action == "acompanhamento" and crm_status in (
        "sem_contato",
        "concluido",
        "sem_interesse",
        "nao_contatar",
    ):
        next_contact = None
    return _save(
        db,
        CashbackContato(
            tenant_id=tenant_id,
            cliente_id=customer_id,
            usuario_id=user.id,
            operador_nome=str(
                getattr(user, "nome", None) or getattr(user, "email", None) or "Usuário"
            )[:200],
            acao=action,
            status=crm_status,
            mensagem=message,
            observacao=note,
            telefone=phone,
            proximo_contato_em=next_contact,
            saldo_cashback=balance,
            chave_cliente=str(request_key),
        ),
    )
