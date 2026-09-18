"""Geracao de respostas do chat IA."""

from typing import Any, Dict, Optional

from app.ia.aba6_resposta_simples import gerar_resposta_simples


class ChatIARespostasMixin:
    def gerar_resposta_ia(
        self,
        usuario_id: int,
        conversa_id: int,
        mensagem_usuario: str,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Gera resposta da IA baseada na mensagem do usuário"""

        # 1. Adicionar mensagem do usuário
        conversa = self.obter_conversa(conversa_id, usuario_id, tenant_id)
        if not conversa:
            raise ValueError("Conversa nao encontrada")

        try:
            # 1. Calcular contexto e resposta antes de gravar a pergunta. Algumas
            # rotinas financeiras legadas controlam a propria transacao; deixar a
            # mensagem pendente antes delas poderia consolidar uma pergunta orfa.
            contexto = self.obter_contexto_financeiro(usuario_id, tenant_id)
            resposta_texto = self._gerar_resposta_simples(
                mensagem_usuario, contexto, tenant_id=tenant_id
            )

            # 2. Persistir pergunta e resposta juntas.
            msg_usuario = self.adicionar_mensagem(
                conversa_id=conversa_id,
                tipo="usuario",
                conteudo=mensagem_usuario,
                tenant_id=tenant_id,
                commit=False,
            )

            msg_ia = self.adicionar_mensagem(
                conversa_id=conversa_id,
                tipo="assistente",
                conteudo=resposta_texto,
                tokens_usados=0,
                modelo_usado="regras_simples",
                contexto_usado=contexto,
                tenant_id=tenant_id,
                commit=False,
            )

            # A pergunta e a resposta formam uma unidade: ou ambas persistem,
            # ou nenhuma fica no historico em caso de erro.
            self.db.commit()
            self.db.refresh(msg_usuario)
            self.db.refresh(msg_ia)
        except Exception:
            self.db.rollback()
            raise

        return {
            "conversa_id": conversa_id,
            "mensagem_usuario": {
                "id": msg_usuario.id,
                "conteudo": msg_usuario.conteudo,
                "criado_em": msg_usuario.criado_em.isoformat(),
            },
            "mensagem_ia": {
                "id": msg_ia.id,
                "conteudo": msg_ia.conteudo,
                "criado_em": msg_ia.criado_em.isoformat(),
            },
            "contexto_usado": contexto,
        }

    def _gerar_resposta_simples(
        self, mensagem: str, contexto: Dict, tenant_id: Optional[str] = None
    ) -> str:
        """Gera resposta simples baseada em regras (temporario antes de OpenAI)"""
        return gerar_resposta_simples(self, mensagem, contexto, tenant_id)
