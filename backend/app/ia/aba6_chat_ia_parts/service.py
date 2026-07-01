"""Composicao do servico de chat IA."""

from app.ia.aba6_chat_ia_parts.base import ChatIABase
from app.ia.aba6_chat_ia_parts.contexto import ChatIAContextoMixin
from app.ia.aba6_chat_ia_parts.conversas import ChatIAConversasMixin
from app.ia.aba6_chat_ia_parts.mensagens import ChatIAMensagensMixin
from app.ia.aba6_chat_ia_parts.metricas import ChatIAMetricasMixin
from app.ia.aba6_chat_ia_parts.periodos import ChatIAPeriodosMixin
from app.ia.aba6_chat_ia_parts.respostas import ChatIARespostasMixin


class ChatIAService(
    ChatIAConversasMixin,
    ChatIAMensagensMixin,
    ChatIAContextoMixin,
    ChatIAMetricasMixin,
    ChatIAPeriodosMixin,
    ChatIARespostasMixin,
    ChatIABase,
):
    """Servico para gerenciar chat com IA."""
