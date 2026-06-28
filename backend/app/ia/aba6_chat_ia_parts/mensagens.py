"""Operacoes de mensagens do chat IA."""

from datetime import datetime
from typing import Dict, List, Optional

from app.ia.aba6_models import Conversa, MensagemChat


class ChatIAMensagensMixin:
    def adicionar_mensagem(
        self,
        conversa_id: int,
        tipo: str,  # 'usuario' ou 'assistente'
        conteudo: str,
        tokens_usados: int = 0,
        modelo_usado: str = None,
        contexto_usado: Dict = None,
        tenant_id: Optional[str] = None,
    ) -> MensagemChat:
        """Adiciona mensagem à conversa"""
        conversa_query = self.db.query(Conversa).filter(Conversa.id == conversa_id)
        if tenant_id:
            conversa_query = conversa_query.filter(Conversa.tenant_id == str(tenant_id))
        conversa = conversa_query.first()
        if tenant_id and not conversa:
            raise ValueError("Conversa nao encontrada")

        # MensagemChat exige tenant_id não nulo: prioriza tenant recebido e
        # usa o tenant da conversa como fallback para manter consistência.
        tenant_id_resolvido = str(tenant_id) if tenant_id else None
        if not tenant_id_resolvido and conversa and conversa.tenant_id:
            tenant_id_resolvido = str(conversa.tenant_id)
        if not tenant_id_resolvido:
            raise ValueError("Não foi possível determinar o tenant da mensagem")

        mensagem = MensagemChat(
            conversa_id=conversa_id,
            tipo=tipo,
            conteudo=conteudo,
            tokens_usados=tokens_usados,
            modelo_usado=modelo_usado,
            contexto_usado=contexto_usado,
            tenant_id=tenant_id_resolvido,
            criado_em=datetime.utcnow(),
        )
        self.db.add(mensagem)

        # Atualizar última mensagem da conversa
        if conversa:
            conversa.atualizado_em = datetime.utcnow()

            # Se primeira mensagem e é do usuário, usar como título
            if not conversa.titulo and tipo == "usuario":
                conversa.titulo = conteudo[:50] + ("..." if len(conteudo) > 50 else "")

        self.db.commit()
        self.db.refresh(mensagem)
        return mensagem

    def obter_historico(
        self,
        conversa_id: int,
        tenant_id: Optional[str],
        limit: int = 50,
    ) -> List[MensagemChat]:
        """Obtém histórico de mensagens"""
        query = self.db.query(MensagemChat).filter(
            MensagemChat.conversa_id == conversa_id
        )
        if tenant_id:
            query = query.filter(MensagemChat.tenant_id == str(tenant_id))

        return query.order_by(MensagemChat.criado_em.asc()).limit(limit).all()
