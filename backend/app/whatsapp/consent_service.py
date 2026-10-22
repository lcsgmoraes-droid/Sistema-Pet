"""Consentimento de mensagens por WhatsApp (CRM etapa 0.7).

Um unico lugar decide se a loja pode falar com o tutor e registra a recusa
quando ele responde SAIR. Usa a tabela de consentimentos que o sistema ja tem
(`DataPrivacyConsent`): para quem tem cadastro, o titular e o cliente; para quem
ainda e so um telefone (lead), o titular e o contato, identificado pelo numero.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from typing import Any
from uuid import UUID

from app.whatsapp.customer_lookup import somente_digitos
from app.whatsapp.security import DataPrivacyConsent
from app.whatsapp.tenant_context import whatsapp_tenant_context

TIPO_CONSENTIMENTO = "marketing_whatsapp"
_TIPOS_EQUIVALENTES = ("marketing_whatsapp", "whatsapp", "marketing")

# Mensagens inteiras (sem outras palavras) que valem como pedido para parar.
PALAVRAS_DE_SAIDA = frozenset(
    {
        "sair",
        "parar",
        "stop",
        "descadastrar",
        "cancelar mensagens",
        "nao quero receber",
        "nao quero mais receber",
    }
)

CONFIRMACAO_DE_SAIDA = (
    "Tudo certo! Você não receberá mais mensagens automáticas desta loja."
)


def _normalizar(texto: Any) -> str:
    sem_acento = "".join(
        c
        for c in unicodedata.normalize("NFKD", str(texto or ""))
        if not unicodedata.combining(c)
    )
    return re.sub(r"[^a-z0-9]+", " ", sem_acento.lower()).strip()


def e_pedido_de_saida(texto: Any) -> bool:
    """True quando a mensagem inteira e um pedido para parar de receber."""
    return _normalizar(texto) in PALAVRAS_DE_SAIDA


def chave_contato(phone: Any) -> str:
    """Identificador do contato sem cadastro: so os digitos (ou o @lid)."""
    texto = str(phone or "").strip().lower()
    return texto if "@lid" in texto else somente_digitos(texto)


def _ultimo_registro(db, tenant_id, subject_type: str, subject_id: str):
    return (
        db.query(DataPrivacyConsent)
        .filter(
            DataPrivacyConsent.tenant_id == UUID(str(tenant_id)),
            DataPrivacyConsent.subject_type == subject_type,
            DataPrivacyConsent.subject_id == subject_id,
            DataPrivacyConsent.consent_type.in_(_TIPOS_EQUIVALENTES),
        )
        .order_by(DataPrivacyConsent.created_at.desc(), DataPrivacyConsent.id.desc())
        .first()
    )


def recusou_mensagens(db, tenant_id, phone: Any, cliente_id: int | None = None) -> bool:
    """True quando o registro mais recente do tutor e uma recusa (cadastro ou contato).

    Sem nenhum registro, nao ha recusa (a regra de pedir o aceite e decidida a
    parte, etapa 0.7 do roadmap).
    """
    with whatsapp_tenant_context(tenant_id):
        registros = []
        if cliente_id:
            registros.append(
                _ultimo_registro(db, tenant_id, "customer", str(cliente_id))
            )
        chave = chave_contato(phone)
        if chave:
            registros.append(_ultimo_registro(db, tenant_id, "contact", chave))
    registros = [r for r in registros if r is not None]
    if not registros:
        return False
    mais_recente = max(registros, key=lambda r: (r.created_at, r.id))
    return (not mais_recente.consent_given) or mais_recente.revoked_at is not None


def registrar_recusa(
    db,
    tenant_id,
    phone: Any,
    cliente_id: int | None = None,
    agora: datetime | None = None,
) -> DataPrivacyConsent:
    """Grava que o tutor pediu para parar (resposta SAIR)."""
    agora = agora or datetime.utcnow()
    if cliente_id:
        tipo_titular, titular = "customer", str(cliente_id)
    else:
        tipo_titular, titular = "contact", chave_contato(phone)
    with whatsapp_tenant_context(tenant_id):
        registro = DataPrivacyConsent(
            tenant_id=UUID(str(tenant_id)),
            subject_type=tipo_titular,
            subject_id=titular,
            consent_type=TIPO_CONSENTIMENTO,
            consent_given=False,
            consent_text="Recusa do tutor ao responder SAIR no WhatsApp",
            revoked_at=agora,
            revoke_reason="sair_whatsapp",
        )
        db.add(registro)
        db.commit()
    return registro


def pode_enviar_whatsapp(
    db,
    tenant_id,
    phone: Any,
    cliente_id: int | None = None,
    *,
    resposta_ao_tutor: bool = False,
    permitir_resposta_a_recusa: bool = False,
) -> tuple[bool, str]:
    """Regra unica para qualquer envio: quem recusou nao recebe nada.

    Unica excecao, quando a loja escolher assim: responder a algo que o proprio
    tutor acabou de escrever (`resposta_ao_tutor`).
    """
    if recusou_mensagens(db, tenant_id, phone, cliente_id):
        if resposta_ao_tutor and permitir_resposta_a_recusa:
            return True, ""
        return False, "recusou_mensagens"
    return True, ""
