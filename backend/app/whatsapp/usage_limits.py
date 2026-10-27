"""Limites de uso da IA no atendimento por WhatsApp (CRM etapa 0.6).

Valvula de seguranca ate o sistema de creditos existir (tema T.1 do roadmap):

- Limite diario de tokens por loja, medido pelas mensagens enviadas ja gravadas
  (durável e igual para todos os processos, ao contrario do controle antigo em
  memoria).
- Limite de mensagens por telefone em uma janela curta, contra spam e laco de
  mensagens (um numero mandando centenas de mensagens faz a IA gastar sem parar).

Os limites sao configuraveis por ambiente; valor 0 ou negativo desliga o limite.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta

from sqlalchemy import func

from app.whatsapp.models import WhatsAppMessage

LIMITE_DIARIO = "limite_diario"
EXCESSO_DE_MENSAGENS = "excesso_de_mensagens"
SEM_CREDITOS = "sem_creditos"

LIMITE_DIARIO_TOKENS_PADRAO = 1_000_000
MENSAGENS_POR_JANELA_PADRAO = 15
JANELA_MINUTOS_PADRAO = 10


def _inteiro_do_ambiente(nome: str, padrao: int) -> int:
    bruto = (os.getenv(nome) or "").strip()
    try:
        return int(bruto) if bruto else padrao
    except ValueError:
        return padrao


def limite_diario_tokens() -> int:
    return _inteiro_do_ambiente(
        "WHATSAPP_IA_DAILY_TOKEN_LIMIT", LIMITE_DIARIO_TOKENS_PADRAO
    )


def limite_mensagens_por_janela() -> tuple[int, int]:
    """(maximo de mensagens do tutor, tamanho da janela em minutos)."""
    return (
        _inteiro_do_ambiente(
            "WHATSAPP_IA_MAX_MESSAGES_PER_WINDOW", MENSAGENS_POR_JANELA_PADRAO
        ),
        _inteiro_do_ambiente("WHATSAPP_IA_WINDOW_MINUTES", JANELA_MINUTOS_PADRAO),
    )


def tokens_usados_hoje(db, tenant_id, agora: datetime | None = None) -> int:
    """Tokens (entrada + saida) gastos pela loja nas respostas de hoje."""
    agora = agora or datetime.utcnow()
    inicio_do_dia = agora.replace(hour=0, minute=0, second=0, microsecond=0)
    total = (
        db.query(
            func.coalesce(
                func.sum(
                    func.coalesce(WhatsAppMessage.tokens_input, 0)
                    + func.coalesce(WhatsAppMessage.tokens_output, 0)
                ),
                0,
            )
        )
        .filter(
            WhatsAppMessage.tenant_id == tenant_id,
            WhatsAppMessage.tipo == "enviada",
            WhatsAppMessage.created_at >= inicio_do_dia,
        )
        .scalar()
    )
    return int(total or 0)


def mensagens_recentes_do_telefone(
    db, session_id, minutos: int, agora: datetime | None = None
) -> int:
    """Mensagens recebidas nesta conversa dentro da janela (inclui a atual)."""
    agora = agora or datetime.utcnow()
    return int(
        db.query(func.count(WhatsAppMessage.id))
        .filter(
            WhatsAppMessage.session_id == session_id,
            WhatsAppMessage.tipo == "recebida",
            WhatsAppMessage.created_at >= agora - timedelta(minutes=minutos),
        )
        .scalar()
        or 0
    )


def avaliar_limites(db, tenant_id, session_id) -> str | None:
    """Devolve o motivo de bloquear a IA agora, ou None se pode responder."""
    # Creditos: com o controle ligado e sem saldo, a IA para (a conversa vai para um atendente).
    from app.whatsapp import creditos_service

    if not creditos_service.pode_gastar(
        db, tenant_id, creditos_service.custo_em_creditos(db, "ia")
    ):
        return SEM_CREDITOS
    limite_tokens = limite_diario_tokens()
    if limite_tokens > 0 and tokens_usados_hoje(db, tenant_id) >= limite_tokens:
        return LIMITE_DIARIO

    maximo, janela = limite_mensagens_por_janela()
    if (
        maximo > 0
        and janela > 0
        and mensagens_recentes_do_telefone(db, session_id, janela) > maximo
    ):
        return EXCESSO_DE_MENSAGENS
    return None
