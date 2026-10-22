"""Conversas de WhatsApp na exportacao e na anonimizacao LGPD (CRM etapa 0.7).

Usado pelo servico central de LGPD (dossie e anonimizacao do cliente): quando o
titular pede exclusao, as conversas dele nao podem ficar para tras, com telefone
e mensagens, depois que o cadastro e anonimizado.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any
from uuid import UUID

from app.whatsapp.consent_service import chave_contato
from app.whatsapp.customer_lookup import chave_telefone, telefones_compativeis
from app.whatsapp.models import WhatsAppMessage, WhatsAppSession
from app.whatsapp.models_handoff import WhatsAppHandoff, WhatsAppInternalNote
from app.whatsapp.security import DataPrivacyConsent
from app.whatsapp.tenant_context import whatsapp_tenant_context

CONTEUDO_REMOVIDO = "[conteudo removido a pedido do titular]"


def sessoes_do_tutor(db, tenant_id, cliente_id, telefones) -> list:
    telefones = [t for t in telefones if t]
    sessoes: dict[str, Any] = {}

    for sessao in (
        db.query(WhatsAppSession)
        .filter(
            WhatsAppSession.tenant_id == UUID(str(tenant_id)),
            WhatsAppSession.cliente_id == cliente_id,
        )
        .all()
    ):
        sessoes[sessao.id] = sessao

    for telefone in telefones:
        chave = chave_telefone(telefone)
        if chave is None:
            continue
        candidatas = (
            db.query(WhatsAppSession)
            .filter(
                WhatsAppSession.tenant_id == UUID(str(tenant_id)),
                WhatsAppSession.phone_number.ilike(f"%{chave[1][-4:]}%"),
            )
            .all()
        )
        for sessao in candidatas:
            if telefones_compativeis(telefone, sessao.phone_number):
                sessoes[sessao.id] = sessao
    return list(sessoes.values())


def _anonimo(valor: str) -> str:
    return "anon-" + hashlib.sha256(str(valor).encode("utf-8")).hexdigest()[:16]


def anonimizar_conversas_do_tutor(
    db, tenant_id, cliente_id, telefones, agora: datetime | None = None
) -> dict[str, int]:
    """Remove mensagens e telefone das conversas do tutor, mantendo so a contagem.

    Devolve quantas conversas, mensagens, atendimentos, notas e registros de
    contato foram tratados.
    """
    agora = agora or datetime.utcnow()
    resumo = {
        "conversas": 0,
        "mensagens": 0,
        "atendimentos": 0,
        "notas": 0,
        "consentimentos_de_contato": 0,
    }

    with whatsapp_tenant_context(tenant_id):
        for sessao in sessoes_do_tutor(db, tenant_id, cliente_id, telefones):
            anonimo = _anonimo(f"{sessao.id}:{sessao.phone_number}")

            for mensagem in db.query(WhatsAppMessage).filter(
                WhatsAppMessage.session_id == sessao.id
            ):
                mensagem.conteudo = CONTEUDO_REMOVIDO
                mensagem.message_metadata = None
                resumo["mensagens"] += 1

            for atendimento in db.query(WhatsAppHandoff).filter(
                WhatsAppHandoff.session_id == sessao.id
            ):
                atendimento.phone_number = anonimo
                atendimento.customer_name = None
                atendimento.reason_details = None
                atendimento.resolution_notes = None
                atendimento.rating_feedback = None
                resumo["atendimentos"] += 1

            for nota in db.query(WhatsAppInternalNote).filter(
                WhatsAppInternalNote.session_id == sessao.id
            ):
                nota.note = CONTEUDO_REMOVIDO
                resumo["notas"] += 1

            sessao.phone_number = anonimo
            sessao.context = None
            sessao.last_intent = None
            sessao.cliente_id = None
            sessao.assigned_to = None
            sessao.status = "closed"
            sessao.closed_at = agora
            resumo["conversas"] += 1

        for telefone in [t for t in telefones if t]:
            chave = chave_contato(telefone)
            if not chave:
                continue
            for registro in db.query(DataPrivacyConsent).filter(
                DataPrivacyConsent.tenant_id == UUID(str(tenant_id)),
                DataPrivacyConsent.subject_type == "contact",
                DataPrivacyConsent.subject_id == chave,
            ):
                registro.subject_id = _anonimo(chave)
                registro.phone_number = None
                registro.email = None
                if registro.revoked_at is None:
                    registro.revoked_at = agora
                    registro.revoke_reason = "anonimizacao_lgpd"
                resumo["consentimentos_de_contato"] += 1
    return resumo


def exportar_conversas_do_tutor(db, tenant_id, cliente_id, telefones) -> dict[str, Any]:
    """Conversas e atendimentos do tutor para o dossie LGPD."""
    with whatsapp_tenant_context(tenant_id):
        conversas = []
        atendimentos = []
        for sessao in sessoes_do_tutor(db, tenant_id, cliente_id, telefones):
            mensagens = (
                db.query(WhatsAppMessage)
                .filter(WhatsAppMessage.session_id == sessao.id)
                .order_by(WhatsAppMessage.created_at)
                .all()
            )
            conversas.append(
                {
                    "id": sessao.id,
                    "status": sessao.status,
                    "criada_em": sessao.started_at.isoformat()
                    if sessao.started_at
                    else None,
                    "mensagens": [
                        {
                            "tipo": m.tipo,
                            "conteudo": m.conteudo,
                            "em": m.created_at.isoformat() if m.created_at else None,
                        }
                        for m in mensagens
                    ],
                }
            )
            for atendimento in db.query(WhatsAppHandoff).filter(
                WhatsAppHandoff.session_id == sessao.id
            ):
                atendimentos.append(
                    {
                        "conversa_id": sessao.id,
                        "motivo": atendimento.reason,
                        "status": atendimento.status,
                        "criado_em": atendimento.created_at.isoformat()
                        if atendimento.created_at
                        else None,
                    }
                )
    return {"conversas": conversas, "atendimentos": atendimentos}
