"""
ABA 6: Chat IA - Logica de Negocio.

Fachada publica mantida para os imports existentes. A implementacao foi
separada em `app.ia.aba6_chat_ia_parts` para reduzir o arquivo monolitico.
"""

from app.ia.aba6_chat_ia_parts import (
    ChatIAService,
    criar_conversa_service,
    deletar_conversa_service,
    enviar_mensagem_service,
    listar_conversas_service,
)

__all__ = [
    "ChatIAService",
    "criar_conversa_service",
    "listar_conversas_service",
    "enviar_mensagem_service",
    "deletar_conversa_service",
]
