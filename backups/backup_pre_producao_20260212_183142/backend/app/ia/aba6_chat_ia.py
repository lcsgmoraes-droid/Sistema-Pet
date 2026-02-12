"""
ABA 6: Chat IA - Lógica de Negócio

Sistema de chat com IA que responde perguntas sobre finanças
usando contexto do usuário (ABA 5: Fluxo de Caixa)
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import os
import json

from app.utils.logger import logger
from app.ia.aba6_models import Conversa, MensagemChat, ContextoFinanceiro
from app.ia.aba5_fluxo_caixa import (
    calcular_indices_saude,
    obter_projecoes_proximos_dias,
    gerar_alertas_caixa
)


class ChatIAService:
    """Serviço para gerenciar chat com IA"""
    
    def __init__(self, db: Session):
        self.db = db
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
    
    # ==================== CONVERSAS ====================
    
    def criar_conversa(self, usuario_id: int) -> Conversa:
        """Cria nova conversa"""
        conversa = Conversa(
            usuario_id=usuario_id,
            criado_em=datetime.utcnow()
        )
        self.db.add(conversa)
        self.db.commit()
        self.db.refresh(conversa)
        return conversa
    
    def listar_conversas(self, usuario_id: int, limit: int = 20) -> List[Conversa]:
        """Lista conversas do usuário"""
        return (
            self.db.query(Conversa)
            .filter(Conversa.usuario_id == usuario_id)
            .order_by(Conversa.atualizado_em.desc())
            .limit(limit)
            .all()
        )
    
    def obter_conversa(self, conversa_id: int, usuario_id: int) -> Optional[Conversa]:
        """Obtém conversa específica"""
        return (
            self.db.query(Conversa)
            .filter(
                Conversa.id == conversa_id,
                Conversa.usuario_id == usuario_id
            )
            .first()
        )
    
    def deletar_conversa(self, conversa_id: int, usuario_id: int) -> bool:
        """Deleta conversa"""
        conversa = self.obter_conversa(conversa_id, usuario_id)
        if not conversa:
            return False
        
        self.db.delete(conversa)
        self.db.commit()
        return True
    
    # ==================== MENSAGENS ====================
    
    def adicionar_mensagem(
        self,
        conversa_id: int,
        tipo: str,  # 'usuario' ou 'assistente'
        conteudo: str,
        tokens_usados: int = 0,
        modelo_usado: str = None,
        contexto_usado: Dict = None
    ) -> MensagemChat:
        """Adiciona mensagem à conversa"""
        mensagem = MensagemChat(
            conversa_id=conversa_id,
            tipo=tipo,
            conteudo=conteudo,
            tokens_usados=tokens_usados,
            modelo_usado=modelo_usado,
            contexto_usado=contexto_usado,
            criado_em=datetime.utcnow()
        )
        self.db.add(mensagem)
        
        # Atualizar última mensagem da conversa
        conversa = self.db.query(Conversa).filter(Conversa.id == conversa_id).first()
        if conversa:
            conversa.atualizado_em = datetime.utcnow()
            
            # Se primeira mensagem e é do usuário, usar como título
            if not conversa.titulo and tipo == "usuario":
                conversa.titulo = conteudo[:50] + ("..." if len(conteudo) > 50 else "")
        
        self.db.commit()
        self.db.refresh(mensagem)
        return mensagem
    
    def obter_historico(self, conversa_id: int, limit: int = 50) -> List[MensagemChat]:
        """Obtém histórico de mensagens"""
        return (
            self.db.query(MensagemChat)
            .filter(MensagemChat.conversa_id == conversa_id)
            .order_by(MensagemChat.criado_em.asc())
            .limit(limit)
            .all()
        )
    
    # ==================== CONTEXTO FINANCEIRO ====================
    
    def obter_contexto_financeiro(self, usuario_id: int) -> Dict[str, Any]:
        """Obtém contexto financeiro do usuário (dados do ABA 5)"""
        contexto = {}
        
        try:
            # 1. Índices de saúde
            indices = calcular_indices_saude(usuario_id, self.db)
            contexto["indices_saude"] = {
                "saldo_atual": float(indices.get('saldo_atual', 0)),
                "dias_de_caixa": float(indices.get('dias_de_caixa', 0)),
                "status": indices.get('status', 'desconhecido'),
                "tendencia": indices.get('tendencia', 'estavel'),
                "score_saude": int(indices.get('score_saude', 0))
            }
            
            # 2. Projeções 15 dias
            projecoes = obter_projecoes_proximos_dias(usuario_id, dias=15, db=self.db)
            contexto["projecoes"] = [
                {
                    "data": p.get('data_projetada'),
                    "saldo_estimado": float(p.get('saldo_estimado', 0)),
                    "entrada_prevista": float(p.get('entrada_prevista', 0)),
                    "saida_prevista": float(p.get('saida_prevista', 0))
                }
                for p in projecoes[:7]  # Últimos 7 dias para resumo
            ]
            
            # 3. Alertas
            alertas = gerar_alertas_caixa(usuario_id, self.db)
            contexto["alertas"] = [
                {
                    "tipo": a.get("tipo", ""),
                    "titulo": a.get("titulo", ""),
                    "mensagem": a.get("mensagem", "")
                }
                for a in alertas
            ]
            
        except Exception as e:
            logger.info(f"Erro ao obter contexto financeiro: {e}")
            contexto["erro"] = str(e)
        
        return contexto
    
    # ==================== IA RESPONSE ====================
    
    def gerar_resposta_ia(
        self,
        usuario_id: int,
        conversa_id: int,
        mensagem_usuario: str
    ) -> Dict[str, Any]:
        """Gera resposta da IA baseada na mensagem do usuário"""
        
        # 1. Adicionar mensagem do usuário
        msg_usuario = self.adicionar_mensagem(
            conversa_id=conversa_id,
            tipo="usuario",
            conteudo=mensagem_usuario
        )
        
        # 2. Obter contexto financeiro
        contexto = self.obter_contexto_financeiro(usuario_id)
        
        # 3. Obter histórico da conversa
        historico = self.obter_historico(conversa_id, limit=10)
        
        # 4. Por enquanto, resposta simples (sem OpenAI)
        # TODO: Integrar OpenAI/Anthropic depois
        resposta_texto = self._gerar_resposta_simples(mensagem_usuario, contexto)
        
        # 5. Adicionar resposta da IA
        msg_ia = self.adicionar_mensagem(
            conversa_id=conversa_id,
            tipo="assistente",
            conteudo=resposta_texto,
            tokens_usados=0,  # TODO: calcular quando integrar OpenAI
            modelo_usado="regras_simples",  # Temporário
            contexto_usado=contexto
        )
        
        return {
            "conversa_id": conversa_id,
            "mensagem_usuario": {
                "id": msg_usuario.id,
                "conteudo": msg_usuario.conteudo,
                "criado_em": msg_usuario.criado_em.isoformat()
            },
            "mensagem_ia": {
                "id": msg_ia.id,
                "conteudo": msg_ia.conteudo,
                "criado_em": msg_ia.criado_em.isoformat()
            },
            "contexto_usado": contexto
        }
    
    def _gerar_resposta_simples(self, mensagem: str, contexto: Dict) -> str:
        """Gera resposta simples baseada em regras (temporário antes de OpenAI)"""
        
        msg_lower = mensagem.lower()
        
        # Análise de contexto
        indices = contexto.get("indices_saude", {})
        alertas = contexto.get("alertas", [])
        projecoes = contexto.get("projecoes", [])
        
        saldo = indices.get("saldo_atual", 0)
        dias_caixa = indices.get("dias_de_caixa", 0)
        status = indices.get("status", "").lower()
        
        # Perguntas sobre saldo
        if any(palavra in msg_lower for palavra in ["saldo", "quanto tenho", "dinheiro"]):
            return f"📊 Seu saldo atual é de **R$ {saldo:,.2f}**.\n\nVocê tem **{dias_caixa:.1f} dias de caixa**, o que significa que consegue cobrir suas despesas por esse período sem novas receitas.\n\n{'⚠️ Status: ' + status.upper() if status in ['critico', 'alerta'] else '✅ Status: OK'}"
        
        # Perguntas sobre dias de caixa
        if any(palavra in msg_lower for palavra in ["dias de caixa", "quanto tempo", "quantos dias"]):
            interpretacao = ""
            if dias_caixa < 7:
                interpretacao = "🔴 **CRÍTICO**: Menos de uma semana! Ação urgente necessária."
            elif dias_caixa < 15:
                interpretacao = "🟡 **ALERTA**: Menos de duas semanas. Monitore com atenção."
            else:
                interpretacao = "🟢 **OK**: Situação confortável."
            
            return f"Você tem **{dias_caixa:.1f} dias de caixa**.\n\n{interpretacao}\n\nIsso é calculado dividindo seu saldo atual (R$ {saldo:,.2f}) pela despesa média diária."
        
        # Perguntas sobre status/saúde
        if any(palavra in msg_lower for palavra in ["como está", "situação", "saúde", "status"]):
            if status == "critico":
                return f"🔴 **Situação CRÍTICA!**\n\nSeu caixa está com apenas {dias_caixa:.1f} dias.\n\n**Ações recomendadas:**\n- Cortar despesas não essenciais\n- Acelerar cobranças\n- Buscar empréstimo/capital\n- Revisar planejamento urgentemente"
            elif status == "alerta":
                return f"🟡 **Situação de ALERTA**\n\nVocê tem {dias_caixa:.1f} dias de caixa.\n\n**Recomendações:**\n- Monitorar diariamente\n- Evitar grandes gastos\n- Planejar com cuidado\n- Cobrar clientes em atraso"
            else:
                return f"🟢 **Situação OK!**\n\nVocê tem {dias_caixa:.1f} dias de caixa.\n\nSeu negócio está saudável financeiramente. Continue monitorando e aproveite para investir em crescimento."
        
        # Perguntas sobre alertas
        if any(palavra in msg_lower for palavra in ["alerta", "aviso", "problema", "risco"]):
            if alertas:
                resposta = f"⚠️ **Você tem {len(alertas)} alerta(s):**\n\n"
                for i, alerta in enumerate(alertas[:3], 1):
                    resposta += f"{i}. **{alerta.get('titulo', 'Alerta')}**\n   {alerta.get('mensagem', '')}\n\n"
                return resposta
            else:
                return "✅ **Nenhum alerta no momento!**\n\nSeu caixa está saudável e não há riscos iminentes."
        
        # Perguntas sobre projeções
        if any(palavra in msg_lower for palavra in ["projeção", "previsão", "futuro", "próximos dias"]):
            if projecoes:
                resposta = "📈 **Projeção dos próximos 7 dias:**\n\n"
                for proj in projecoes[:7]:
                    data = proj.get("data", "").split("T")[0]
                    saldo_est = proj.get("saldo_estimado", 0)
                    resposta += f"- **{data}**: R$ {saldo_est:,.2f}\n"
                return resposta
            else:
                return "Não há projeções disponíveis no momento. Clique em 'Atualizar Projeção' no Dashboard."
        
        # Resposta genérica
        return f"Olá! 👋 Sou seu assistente financeiro com IA.\n\n**Algumas perguntas que posso responder:**\n- \"Qual é meu saldo atual?\"\n- \"Quantos dias de caixa tenho?\"\n- \"Como está minha situação financeira?\"\n- \"Há algum alerta?\"\n- \"Qual a projeção para os próximos dias?\"\n\n📊 **Resumo rápido:**\n- Saldo: R$ {saldo:,.2f}\n- Dias de caixa: {dias_caixa:.1f}\n- Status: {status.upper()}"


# Funções auxiliares para endpoints
def criar_conversa_service(db: Session, usuario_id: int) -> Conversa:
    """Helper para criar conversa"""
    service = ChatIAService(db)
    return service.criar_conversa(usuario_id)


def listar_conversas_service(db: Session, usuario_id: int, limit: int = 20) -> List[Conversa]:
    """Helper para listar conversas"""
    service = ChatIAService(db)
    return service.listar_conversas(usuario_id, limit)


def enviar_mensagem_service(
    db: Session,
    usuario_id: int,
    conversa_id: int,
    mensagem: str
) -> Dict[str, Any]:
    """Helper para enviar mensagem e obter resposta"""
    service = ChatIAService(db)
    return service.gerar_resposta_ia(usuario_id, conversa_id, mensagem)


def deletar_conversa_service(db: Session, conversa_id: int, usuario_id: int) -> bool:
    """Helper para deletar conversa"""
    service = ChatIAService(db)
    return service.deletar_conversa(conversa_id, usuario_id)
