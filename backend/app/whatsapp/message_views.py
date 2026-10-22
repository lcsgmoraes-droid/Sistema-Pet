"""Formato unico das mensagens de WhatsApp para a tela (CRM etapa 0.8).

Antes cada ponto montava a mensagem do seu jeito (ou devolvia o modelo cru). A
tela do atendente espera `sender_type`, `content`, `timestamp` e `read`; o
historico do cliente espera `direcao`, `status` e `preview`.
"""

from __future__ import annotations

from typing import Any


def quem_enviou(mensagem: Any) -> str:
    """customer (tutor), agent (atendente humano) ou bot (IA/sistema)."""
    if mensagem.tipo == "recebida":
        return "customer"
    if getattr(mensagem, "sent_by_user_id", None):
        return "agent"
    return "bot"


def serializar_mensagem(mensagem: Any) -> dict[str, Any]:
    """Mensagem no formato do chat do atendente (mantem os nomes antigos tambem)."""
    quando = mensagem.created_at.isoformat() if mensagem.created_at else None
    return {
        "id": str(mensagem.id),
        "session_id": str(mensagem.session_id),
        "sender_type": quem_enviou(mensagem),
        "content": mensagem.conteudo,
        "timestamp": quando,
        "read": True,
        # Nomes antigos, para quem ainda le o formato anterior.
        "tipo": mensagem.tipo,
        "conteudo": mensagem.conteudo,
        "created_at": quando,
        "sent_by_user_id": getattr(mensagem, "sent_by_user_id", None),
    }


def serializar_para_historico_do_cliente(mensagem: Any) -> dict[str, Any]:
    """Mensagem no formato do historico de WhatsApp da ficha do cliente."""
    conteudo = mensagem.conteudo or ""
    return {
        "id": str(mensagem.id),
        "direcao": mensagem.tipo,
        "status": "recebido" if mensagem.tipo == "recebida" else "enviado",
        "created_at": mensagem.created_at.isoformat() if mensagem.created_at else None,
        "conteudo": conteudo,
        "preview": conteudo[:120],
    }
