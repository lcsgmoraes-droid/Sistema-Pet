"""Helpers publicos do servico de chat IA."""

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.ia.aba6_chat_ia_parts.service import ChatIAService
from app.ia.aba6_models import Conversa


def criar_conversa_service(
    db: Session, usuario_id: int, tenant_id: Optional[str] = None
) -> Conversa:
    """Helper para criar conversa"""
    service = ChatIAService(db)
    return service.criar_conversa(usuario_id, tenant_id=tenant_id)


def listar_conversas_service(
    db: Session,
    usuario_id: int,
    tenant_id: Optional[str],
    limit: int = 20,
) -> List[Conversa]:
    """Helper para listar conversas"""
    service = ChatIAService(db)
    return service.listar_conversas(usuario_id, tenant_id, limit)


def enviar_mensagem_service(
    db: Session,
    usuario_id: int,
    tenant_id: Optional[str],
    conversa_id: int,
    mensagem: str,
) -> Dict[str, Any]:
    """Helper para enviar mensagem e obter resposta"""
    service = ChatIAService(db)
    return service.gerar_resposta_ia(
        usuario_id, conversa_id, mensagem, tenant_id=tenant_id
    )


def deletar_conversa_service(
    db: Session,
    conversa_id: int,
    usuario_id: int,
    tenant_id: Optional[str],
) -> bool:
    """Helper para deletar conversa"""
    service = ChatIAService(db)
    return service.deletar_conversa(conversa_id, usuario_id, tenant_id)
