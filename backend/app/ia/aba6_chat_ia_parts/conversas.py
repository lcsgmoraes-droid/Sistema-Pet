"""Operacoes de conversas do chat IA."""

from datetime import datetime
from typing import List, Optional

from app.ia.aba6_models import Conversa


class ChatIAConversasMixin:
    def criar_conversa(
        self, usuario_id: int, tenant_id: Optional[str] = None
    ) -> Conversa:
        """Cria nova conversa"""
        tenant_id_resolvido = self._resolver_tenant_id(usuario_id, tenant_id)
        if not tenant_id_resolvido:
            raise ValueError("Não foi possível determinar o tenant da conversa")

        conversa = Conversa(
            usuario_id=usuario_id,
            tenant_id=tenant_id_resolvido,
            criado_em=datetime.utcnow(),
        )
        self.db.add(conversa)
        self.db.commit()
        self.db.refresh(conversa)
        return conversa

    def listar_conversas(
        self, usuario_id: int, tenant_id: Optional[str], limit: int = 20
    ) -> List[Conversa]:
        """Lista conversas do usuário"""
        tenant_id_resolvido = self._resolver_tenant_id(usuario_id, tenant_id)
        if not tenant_id_resolvido:
            return []

        return (
            self.db.query(Conversa)
            .filter(
                Conversa.usuario_id == usuario_id,
                Conversa.tenant_id == tenant_id_resolvido,
            )
            .order_by(Conversa.atualizado_em.desc())
            .limit(limit)
            .all()
        )

    def obter_conversa(
        self,
        conversa_id: int,
        usuario_id: int,
        tenant_id: Optional[str] = None,
    ) -> Optional[Conversa]:
        """Obtém conversa específica"""
        tenant_id_resolvido = self._resolver_tenant_id(usuario_id, tenant_id)
        if not tenant_id_resolvido:
            return None

        return (
            self.db.query(Conversa)
            .filter(
                Conversa.id == conversa_id,
                Conversa.usuario_id == usuario_id,
                Conversa.tenant_id == tenant_id_resolvido,
            )
            .first()
        )

    def deletar_conversa(
        self, conversa_id: int, usuario_id: int, tenant_id: Optional[str]
    ) -> bool:
        """Deleta conversa"""
        conversa = self.obter_conversa(conversa_id, usuario_id, tenant_id)
        if not conversa:
            return False

        self.db.delete(conversa)
        self.db.commit()
        return True
