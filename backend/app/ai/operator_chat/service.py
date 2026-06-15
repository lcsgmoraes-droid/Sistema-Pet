"""
Service para Chat do Operador

Este módulo implementa a lógica principal do chat interno do operador.

Responsabilidades:
1. Validar entrada
2. Validar tenant (multi-tenant)
3. Detectar intenção (via adapter)
4. Selecionar prompt (via biblioteca de prompts)
5. Chamar AI Engine (mock por enquanto)
6. Normalizar resposta
7. Garantir que NUNCA levanta exceção para fora

PRINCÍPIOS:
- EM ERRO: retorna resposta educada + vazia
- NUNCA quebra o sistema
- SEMPRE auditável
- SEMPRE multi-tenant
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import time

from .models import (
    OperatorChatContext,
    OperatorChatResponse,
    FONTE_HEURISTICA,
    FONTE_INSIGHT,
    FONTE_PDV_CONTEXT,
    FONTE_READ_MODEL,
)
from .adapter import preparar_contexto_completo


logger = logging.getLogger(__name__)


class OperatorChatService:
    """
    Serviço principal para processamento de perguntas do operador.
    
    Este serviço orquestra todo o fluxo:
    - Validação
    - Detecção de intenção
    - Preparação de contexto
    - Chamada à IA (mock)
    - Formatação de resposta
    
    IMPORTANTE: Este serviço NUNCA levanta exceção.
    Em caso de erro, retorna resposta educada explicando o problema.
    """
    
    def __init__(self):
        """Inicializa o serviço"""
        logger.info("[OperatorChatService] Serviço inicializado")
    
    def processar_pergunta(
        self,
        operator_context: OperatorChatContext
    ) -> OperatorChatResponse:
        """
        Processa uma pergunta do operador e retorna resposta.
        
        Este é o método principal do serviço.
        
        Fluxo:
        1. Validar entrada
        2. Preparar contexto (adapter)
        3. Gerar resposta (mock IA)
        4. Normalizar resposta
        5. Retornar
        
        Args:
            operator_context: Contexto completo da pergunta
            
        Returns:
            OperatorChatResponse com resposta da IA
        """
        inicio = time.time()
        
        try:
            # 1. Validar entrada
            self._validar_contexto(operator_context)
            
            # 2. Preparar contexto via adapter
            logger.info(
                f"[OperatorChat] Processando pergunta para tenant={operator_context.tenant_id}, "
                f"operador={operator_context.message.operador_id}"
            )
            
            contexto_preparado = preparar_contexto_completo(operator_context)
            
            # 3. Obter prompt formatado
            intencao = contexto_preparado["intencao"]
            pergunta = contexto_preparado["pergunta"]
            contexto_formatado = contexto_preparado["contexto_formatado"]
            
            logger.info(
                f"[OperatorChat] Intenção detectada: {intencao.intencao} "
                f"(confiança: {intencao.confianca:.2f})"
            )
            
            # 4. Gerar resposta (MOCK por enquanto)
            resposta_texto = self._gerar_resposta_mock(
                intencao.intencao,
                pergunta,
                contexto_formatado
            )
            
            # 5. Determinar fontes utilizadas
            fontes = self._determinar_fontes(operator_context, contexto_formatado)
            
            # 6. Calcular tempo de processamento
            tempo_ms = int((time.time() - inicio) * 1000)
            
            # 7. Montar resposta
            response = OperatorChatResponse(
                resposta=resposta_texto,
                confianca=intencao.confianca,
                fontes_utilizadas=fontes,
                contexto_usado=self._resumir_contexto_usado(contexto_formatado),
                timestamp=datetime.now(),
                tempo_processamento_ms=tempo_ms,
                origem="mock",
                intencao_detectada=intencao.intencao,
                sugestoes_acao=None  # Pode ser expandido no futuro
            )
            
            logger.info(
                f"[OperatorChat] Resposta gerada em {tempo_ms}ms "
                f"(confiança: {response.confianca:.2f})"
            )
            
            return response
            
        except ValueError as e:
            # Erro de validação - retornar resposta educada
            logger.warning(f"[OperatorChat] Erro de validação: {str(e)}")
            return self._resposta_erro_validacao(str(e))
        
        except Exception as e:
            # Erro inesperado - NÃO QUEBRAR O SISTEMA
            logger.error(f"[OperatorChat] Erro inesperado: {str(e)}", exc_info=True)
            return self._resposta_erro_generico()
    
    def _validar_contexto(self, context: OperatorChatContext) -> None:
        """
        Valida o contexto antes de processar.
        
        Args:
            context: Contexto a validar
            
        Raises:
            ValueError: Se contexto for inválido
        """
        if context.tenant_id <= 0:
            raise ValueError("tenant_id inválido")
        
        if not context.message:
            raise ValueError("Mensagem não pode ser vazia")
        
        if not context.message.pergunta.strip():
            raise ValueError("Pergunta não pode ser vazia")
    
    def _gerar_resposta_mock(
        self,
        intencao: str,
        pergunta: str,
        contexto: Dict[str, Any]
    ) -> str:
        """
        Gera resposta MOCK baseada na intenção.
        
        NO FUTURO: Aqui será chamado o AI Engine real (OpenAI/Claude)
        
        Args:
            intencao: Tipo de intenção detectada
            pergunta: Pergunta original
            contexto: Contexto formatado
            
        Returns:
            Texto da resposta
        """
        # Respostas mock baseadas na intenção
        respostas_mock = {
            "cliente": self._mock_resposta_cliente(contexto),
            "produto": self._mock_resposta_produto(contexto),
            "kit": self._mock_resposta_kit(contexto),
            "estoque": self._mock_resposta_estoque(contexto),
            "insight": self._mock_resposta_insight(contexto),
            "venda": self._mock_resposta_venda(contexto),
            "generica": self._mock_resposta_generica(pergunta),
        }
        
        return respostas_mock.get(intencao, self._mock_resposta_generica(pergunta))
    
    def _mock_resposta_cliente(self, contexto: Dict[str, Any]) -> str:
        """Resposta mock para perguntas sobre cliente"""
        if "contexto_cliente" in contexto and contexto["contexto_cliente"] != "Não disponível":
            return (
                "Baseado no histórico do cliente:\n\n"
                f"{contexto['contexto_cliente']}\n\n"
                "💡 **Sugestão:** Considere oferecer produtos relacionados às categorias "
                "preferidas do cliente para aumentar a satisfação e o ticket médio."
            )
        else:
            return (
                "Não tenho informações suficientes sobre este cliente no momento. "
                "Para uma análise mais detalhada, seria útil ter:\n"
                "- Histórico de compras\n"
                "- Preferências de categorias\n"
                "- Frequência de visitas\n\n"
                "Você pode consultar o histórico completo no sistema."
            )
    
    def _mock_resposta_produto(self, contexto: Dict[str, Any]) -> str:
        """Resposta mock para perguntas sobre produto"""
        if "contexto_produto" in contexto and contexto["contexto_produto"] != "Não disponível":
            return (
                "Sobre os produtos da venda:\n\n"
                f"{contexto['contexto_produto']}\n\n"
                "💡 **Sugestão:** Verifique se existem produtos complementares "
                "que poderiam agregar valor à compra do cliente."
            )
        else:
            return (
                "Não há produtos na venda atual. "
                "Adicione produtos à venda para que eu possa fornecer informações específicas."
            )
    
    def _mock_resposta_kit(self, contexto: Dict[str, Any]) -> str:
        """Resposta mock para perguntas sobre kits"""
        if "contexto_insights" in contexto and contexto["contexto_insights"] != "Não disponível":
            return (
                "Analisando os produtos da venda atual, identifiquei as seguintes oportunidades:\n\n"
                f"{contexto['contexto_insights']}\n\n"
                "💡 **Sugestão:** Se houver insights sobre kits vantajosos, "
                "apresente ao cliente destacando a economia."
            )
        else:
            return (
                "No momento não identifiquei kits específicos para esta venda. "
                "Isso pode acontecer porque:\n"
                "- A venda ainda não tem produtos suficientes\n"
                "- Os produtos atuais não fazem parte de kits cadastrados\n"
                "- Não há kits promocionais ativos\n\n"
                "Continue adicionando produtos e eu monitoro automaticamente."
            )
    
    def _mock_resposta_estoque(self, contexto: Dict[str, Any]) -> str:
        """Resposta mock para perguntas sobre estoque"""
        return (
            "Para informações sobre estoque, você pode:\n\n"
            "1. Consultar a tela de Estoque no sistema\n"
            "2. Verificar alertas de estoque baixo\n"
            "3. Consultar produtos alternativos similares\n\n"
            "💡 **Dica:** Se um produto estiver com estoque baixo ou zerado, "
            "sempre ofereça uma alternativa similar ao cliente."
        )
    
    def _mock_resposta_insight(self, contexto: Dict[str, Any]) -> str:
        """Resposta mock para perguntas sobre insights"""
        if "contexto_insights" in contexto and contexto["contexto_insights"] != "Não disponível":
            return (
                "Explicando os insights disponíveis:\n\n"
                f"{contexto['contexto_insights']}\n\n"
                "Esses insights são gerados automaticamente baseados em:\n"
                "- Histórico de compras do cliente\n"
                "- Padrões de vendas\n"
                "- Regras de negócio configuradas\n"
                "- Análise de eventos do sistema\n\n"
                "Use esses insights como orientação para melhorar o atendimento."
            )
        else:
            return (
                "Não há insights disponíveis para esta venda no momento. "
                "Insights são gerados automaticamente quando:\n"
                "- Um cliente é identificado\n"
                "- Produtos são adicionados à venda\n"
                "- Padrões específicos são detectados\n\n"
                "Continue com a venda e novos insights podem aparecer."
            )
    
    def _mock_resposta_venda(self, contexto: Dict[str, Any]) -> str:
        """Resposta mock para perguntas sobre a venda"""
        if "contexto_pdv" in contexto and contexto["contexto_pdv"] != "Não disponível":
            return (
                "Resumo da venda atual:\n\n"
                f"{contexto['contexto_pdv']}\n\n"
                "💡 **Oportunidades:**\n"
                "- Verifique se há produtos complementares\n"
                "- Confira se existe algum kit vantajoso\n"
                "- Considere o histórico do cliente\n"
                "- Fique atento aos insights do sistema"
            )
        else:
            return (
                "Não há venda em andamento no momento. "
                "Inicie uma venda adicionando produtos e identificando o cliente "
                "para que eu possa fornecer orientações específicas."
            )
    
    def _mock_resposta_generica(self, pergunta: str) -> str:
        """Resposta mock para perguntas genéricas"""
        return (
            f"Recebi sua pergunta: \"{pergunta}\"\n\n"
            "Posso ajudá-lo com:\n"
            "- Informações sobre clientes e histórico\n"
            "- Detalhes sobre produtos e estoque\n"
            "- Sugestões de kits e combos\n"
            "- Explicação de insights do sistema\n"
            "- Orientação sobre vendas em andamento\n\n"
            "💡 **Dica:** Seja mais específico na pergunta para que eu possa "
            "fornecer uma resposta mais útil."
        )
    
    def _determinar_fontes(
        self,
        operator_context: OperatorChatContext,
        contexto_formatado: Dict[str, Any]
    ) -> List[str]:
        """
        Determina quais fontes de dados foram utilizadas.
        
        Args:
            operator_context: Contexto original
            contexto_formatado: Contexto formatado pelo adapter
            
        Returns:
            Lista de fontes utilizadas
        """
        fontes = [FONTE_HEURISTICA]  # Sempre usa heurística para detectar intenção
        
        if operator_context.contexto_pdv:
            fontes.append(FONTE_PDV_CONTEXT)
        
        if operator_context.contexto_insights:
            fontes.append(FONTE_INSIGHT)
        
        if operator_context.contexto_cliente or operator_context.contexto_produto:
            fontes.append(FONTE_READ_MODEL)
        
        return fontes
    
    def _resumir_contexto_usado(self, contexto_formatado: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cria resumo do contexto usado (para auditoria).
        
        Args:
            contexto_formatado: Contexto completo formatado
            
        Returns:
            Resumo do contexto para incluir na resposta
        """
        resumo = {
            "tem_pdv": "contexto_pdv" in contexto_formatado and contexto_formatado["contexto_pdv"] != "Não disponível",
            "tem_cliente": "contexto_cliente" in contexto_formatado and contexto_formatado["contexto_cliente"] != "Não disponível",
            "tem_produto": "contexto_produto" in contexto_formatado and contexto_formatado["contexto_produto"] != "Não disponível",
            "tem_insights": "contexto_insights" in contexto_formatado and contexto_formatado["contexto_insights"] != "Não disponível",
        }
        return resumo
    
    def _resposta_erro_validacao(self, erro: str) -> OperatorChatResponse:
        """
        Cria resposta educada para erro de validação.
        
        Args:
            erro: Mensagem de erro
            
        Returns:
            OperatorChatResponse explicando o erro
        """
        return OperatorChatResponse(
            resposta=(
                "Desculpe, não consegui processar sua pergunta. "
                f"Motivo: {erro}\n\n"
                "Por favor, tente novamente."
            ),
            confianca=0.0,
            fontes_utilizadas=["validacao"],
            contexto_usado={},
            timestamp=datetime.now(),
            origem="validation_error"
        )
    
    def _resposta_erro_generico(self) -> OperatorChatResponse:
        """
        Cria resposta educada para erro genérico.
        
        Returns:
            OperatorChatResponse explicando que houve um erro
        """
        return OperatorChatResponse(
            resposta=(
                "Desculpe, ocorreu um erro inesperado ao processar sua pergunta. "
                "O erro foi registrado e será analisado.\n\n"
                "Por favor, tente novamente em alguns instantes."
            ),
            confianca=0.0,
            fontes_utilizadas=["error_handler"],
            contexto_usado={},
            timestamp=datetime.now(),
            origem="error"
        )


# ============================================================================
# INSTÂNCIA SINGLETON (OPCIONAL)
# ============================================================================

_service_instance: Optional[OperatorChatService] = None


def get_operator_chat_service() -> OperatorChatService:
    """
    Retorna instância singleton do serviço.
    
    Returns:
        OperatorChatService
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = OperatorChatService()
    return _service_instance
