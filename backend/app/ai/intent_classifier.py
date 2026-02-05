"""
Intent Classifier

Classifica a intenção do usuário de forma rápida (GPT-4o-mini).
Usado para roteamento e métricas.

Intenções suportadas:
- saudacao: Olá, oi, bom dia
- consulta_produto: Perguntas sobre produtos
- consulta_preco: Perguntas sobre preço
- consulta_estoque: Disponibilidade
- consulta_entrega: Prazos, frete, horários
- pedido_recompra: Repetir pedido anterior
- pedido_novo: Fazer novo pedido
- reclamacao: Problemas, insatisfação
- suporte: Dúvidas gerais
- despedida: Tchau, obrigado
- outro: Não classificado
"""
import logging
from typing import Dict, Literal
from app.ai.llm_client import LLMClient

logger = logging.getLogger(__name__)

# Type hint para intenções
IntentType = Literal[
    "saudacao",
    "consulta_produto",
    "consulta_preco", 
    "consulta_estoque",
    "consulta_entrega",
    "pedido_recompra",
    "pedido_novo",
    "reclamacao",
    "suporte",
    "despedida",
    "outro"
]


class IntentClassifier:
    """
    Classifica intenção usando GPT-4o-mini (rápido e barato).
    """
    
    def __init__(self, openai_api_key: str):
        self.llm = LLMClient(api_key=openai_api_key)
    
    async def classify(self, message: str, context: Dict = None) -> Dict[str, any]:
        """
        Classifica intenção da mensagem.
        
        Args:
            message: Mensagem do usuário
            context: Contexto adicional (histórico, cliente, etc)
            
        Returns:
            {
                "intent": "consulta_produto",
                "confidence": 0.95,
                "entities": {"produto": "ração", "marca": "golden"}
            }
        """
        try:
            # System prompt para classificação
            system_prompt = self._build_classification_prompt()
            
            # Mensagem do usuário
            user_message = f"Classifique a intenção: '{message}'"
            
            # Adicionar contexto se disponível
            if context and context.get("historico_conversa"):
                last_messages = context["historico_conversa"][-3:]
                history_text = "\n".join([
                    f"{msg['tipo']}: {msg['conteudo']}" 
                    for msg in last_messages
                ])
                user_message += f"\n\nContexto recente:\n{history_text}"
            
            # Chamar LLM (força GPT-4o-mini para velocidade)
            response = await self.llm.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                model="gpt-4o-mini",
                temperature=0.3,  # Baixa temperatura para mais consistência
                max_tokens=150
            )
            
            # Parsear resposta
            content = response["content"].strip()
            result = self._parse_classification(content)
            
            logger.info(f"✅ Intent: {result['intent']} (confidence: {result['confidence']})")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Erro ao classificar intenção: {e}")
            return self._fallback_classification(message)
    
    def _build_classification_prompt(self) -> str:
        """Constrói prompt de classificação."""
        return """Você é um classificador de intenções para um pet shop.

Classifique a mensagem do usuário em UMA das seguintes categorias:

1. saudacao - Cumprimentos iniciais (oi, olá, bom dia)
2. consulta_produto - Perguntas sobre produtos específicos
3. consulta_preco - Perguntas sobre valores
4. consulta_estoque - Disponibilidade de produtos
5. consulta_entrega - Frete, prazo, horário de entrega
6. pedido_recompra - Quer repetir pedido anterior
7. pedido_novo - Quer fazer novo pedido
8. reclamacao - Insatisfação, problema
9. suporte - Dúvidas gerais, ajuda
10. despedida - Encerramento (tchau, obrigado)
11. outro - Não se encaixa nas categorias acima

Responda APENAS no formato:
INTENT: [categoria]
CONFIDENCE: [0.0-1.0]
ENTITIES: {key: value, ...}

Exemplo:
INTENT: consulta_produto
CONFIDENCE: 0.95
ENTITIES: {"produto": "ração", "marca": "golden", "tipo": "filhote"}
"""
    
    def _parse_classification(self, content: str) -> Dict:
        """Parseia resposta do LLM."""
        try:
            lines = content.strip().split("\n")
            result = {
                "intent": "outro",
                "confidence": 0.5,
                "entities": {}
            }
            
            for line in lines:
                if line.startswith("INTENT:"):
                    result["intent"] = line.split(":", 1)[1].strip()
                elif line.startswith("CONFIDENCE:"):
                    result["confidence"] = float(line.split(":", 1)[1].strip())
                elif line.startswith("ENTITIES:"):
                    entities_str = line.split(":", 1)[1].strip()
                    try:
                        import json
                        result["entities"] = json.loads(entities_str)
                    except:
                        result["entities"] = {}
            
            return result
            
        except Exception as e:
            logger.warning(f"Erro ao parsear classificação: {e}")
            return self._fallback_classification(content)
    
    def _fallback_classification(self, message: str) -> Dict:
        """
        Classificação baseada em regras (fallback).
        Usado quando LLM falha.
        """
        message_lower = message.lower()
        
        # Regras simples
        if any(word in message_lower for word in ["oi", "olá", "ola", "bom dia", "boa tarde", "boa noite"]):
            return {"intent": "saudacao", "confidence": 0.8, "entities": {}}
        
        if any(word in message_lower for word in ["tchau", "obrigado", "obrigada", "valeu", "até"]):
            return {"intent": "despedida", "confidence": 0.8, "entities": {}}
        
        if any(word in message_lower for word in ["preço", "preco", "valor", "quanto custa", "quanto é"]):
            return {"intent": "consulta_preco", "confidence": 0.7, "entities": {}}
        
        if any(word in message_lower for word in ["tem", "têm", "estoque", "disponível", "disponivel"]):
            return {"intent": "consulta_estoque", "confidence": 0.7, "entities": {}}
        
        if any(word in message_lower for word in ["entrega", "frete", "prazo", "demora"]):
            return {"intent": "consulta_entrega", "confidence": 0.7, "entities": {}}
        
        if any(word in message_lower for word in ["repetir", "mesmo pedido", "anterior", "de novo"]):
            return {"intent": "pedido_recompra", "confidence": 0.7, "entities": {}}
        
        if any(word in message_lower for word in ["comprar", "quero", "pedido", "pedir"]):
            return {"intent": "pedido_novo", "confidence": 0.6, "entities": {}}
        
        if any(word in message_lower for word in ["problema", "reclamação", "reclamacao", "insatisfeito", "ruim"]):
            return {"intent": "reclamacao", "confidence": 0.8, "entities": {}}
        
        # Default
        return {"intent": "consulta_produto", "confidence": 0.5, "entities": {}}


# ============================================================================
# ROUTER DE INTENTS (decide ação baseada na intenção)
# ============================================================================

class IntentRouter:
    """
    Decide qual ação tomar baseado na intenção.
    """
    
    @staticmethod
    def should_transfer_to_human(intent: str, confidence: float) -> bool:
        """
        Decide se deve transferir para humano.
        
        Transfere se:
        - Reclamação
        - Confidence muito baixa
        - Intent "suporte" específico
        """
        if intent == "reclamacao":
            return True
        
        if confidence < 0.4:
            return True
        
        return False
    
    @staticmethod
    def requires_context_enrichment(intent: str) -> bool:
        """
        Decide se precisa buscar contexto adicional no ERP.
        
        Busca contexto para:
        - Consultas de produto/preço/estoque
        - Pedidos
        """
        needs_context = [
            "consulta_produto",
            "consulta_preco",
            "consulta_estoque",
            "pedido_recompra",
            "pedido_novo"
        ]
        
        return intent in needs_context
    
    @staticmethod
    def get_quick_response(intent: str, bot_name: str = "Assistente") -> str:
        """
        Resposta rápida para intents simples (sem chamar IA).
        
        Usado para saudações e despedidas.
        """
        quick_responses = {
            "saudacao": f"🐾 Olá! Sou o {bot_name}, como posso ajudar você e seu pet hoje?",
            "despedida": "Até logo! Qualquer coisa é só chamar! 🐾",
        }
        
        return quick_responses.get(intent)
    
    @staticmethod
    def should_use_advanced_model(intent: str, context: Dict) -> bool:
        """
        Decide se deve usar GPT-4.1 (modelo avançado).
        
        Usa modelo avançado para:
        - Pedidos complexos
        - Múltiplas consultas
        - Recomendações
        """
        advanced_intents = [
            "pedido_novo",
            "pedido_recompra"
        ]
        
        if intent in advanced_intents:
            return True
        
        # Se conversa longa
        if context.get("session", {}).get("message_count", 0) > 5:
            return True
        
        return False
