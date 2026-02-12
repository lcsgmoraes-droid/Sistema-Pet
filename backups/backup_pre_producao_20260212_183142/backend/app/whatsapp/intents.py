"""
Sistema de Detecção de Intenções para WhatsApp IA
Classifica mensagens dos clientes em categorias para respostas personalizadas
"""

from typing import Dict, List, Optional, Tuple
from enum import Enum
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class IntentType(str, Enum):
    """Tipos de intenções do usuário"""
    SAUDACAO = "saudacao"
    CONSULTA_HORARIO = "consulta_horario"
    AGENDAMENTO = "agendamento"
    PRODUTOS = "produtos"
    ENTREGA = "entrega"
    DUVIDA = "duvida"
    RECLAMACAO = "reclamacao"
    ELOGIO = "elogio"
    DESPEDIDA = "despedida"
    DESCONHECIDO = "desconhecido"


# Keywords para detecção de intenções
INTENT_KEYWORDS: Dict[IntentType, List[str]] = {
    IntentType.SAUDACAO: [
        "oi", "olá", "ola", "bom dia", "boa tarde", "boa noite",
        "e ai", "eai", "hey", "opa", "oiii", "oie"
    ],
    
    IntentType.CONSULTA_HORARIO: [
        "horário", "horario", "funciona", "aberto", "abre", "fecha",
        "que horas", "até que horas", "ate que horas", "trabalha",
        "domingo", "feriado", "hoje abre"
    ],
    
    IntentType.AGENDAMENTO: [
        "agendar", "marcar", "consulta", "banho", "tosa", "veterinário",
        "veterinario", "horário disponível", "horario disponivel",
        "disponibilidade", "vaga", "atendimento", "avaliação", "avaliacao"
    ],
    
    IntentType.PRODUTOS: [
        "produto", "ração", "racao", "brinquedo", "preço", "preco",
        "valor", "custa", "quanto", "tem ", "vende", "vender",
        "comprar", "coleira", "remédio", "remedio", "shampoo",
        "petisco", "arranhador", "cama", "aquário", "aquario"
    ],
    
    IntentType.ENTREGA: [
        "entrega", "pedido", "onde está", "onde esta", "chegou",
        "status", "rastreio", "enviado", "saiu", "caminho",
        "chegar", "demora", "prazo", "envio"
    ],
    
    IntentType.RECLAMACAO: [
        "reclamação", "reclamacao", "problema", "errado", "ruim",
        "péssimo", "pessimo", "horrível", "horrivel", "insatisfeito",
        "demora", "demora demais", "não funciona", "nao funciona",
        "não chegou", "nao chegou", "perdido", "atrasado"
    ],
    
    IntentType.ELOGIO: [
        "obrigado", "obrigada", "valeu", "agradeço", "agradeco",
        "excelente", "ótimo", "otimo", "maravilhoso", "perfeito",
        "adorei", "amei", "parabéns", "parabens", "top"
    ],
    
    IntentType.DESPEDIDA: [
        "tchau", "até logo", "ate logo", "até mais", "ate mais",
        "falou", "abraço", "abraco", "bye", "flw", "obrigado tchau",
        "valeu tchau"
    ],
    
    IntentType.DUVIDA: [
        "dúvida", "duvida", "ajuda", "como", "posso", "ajudar",
        "informação", "informacao", "saber", "explicar", "entender",
        "funciona", "fazer", "consigo"
    ]
}


# Prompts específicos por intenção
INTENT_PROMPTS: Dict[IntentType, str] = {
    IntentType.SAUDACAO: """
Responda com uma saudação amigável e profissional.
Pergunte como pode ajudar o cliente hoje.
Seja breve e caloroso.
""",
    
    IntentType.CONSULTA_HORARIO: """
Informe os horários de funcionamento do pet shop de forma clara.
Se possível, mencione dias especiais ou exceções.
Seja objetivo e útil.
""",
    
    IntentType.AGENDAMENTO: """
Ajude o cliente a agendar um serviço.
Pergunte qual serviço deseja (banho, tosa, consulta, etc.).
Pergunte a data e horário de preferência.
Pergunte o nome e raça do pet.
Seja organizado e confirme cada informação.
""",
    
    IntentType.PRODUTOS: """
Ajude o cliente a encontrar produtos.
Faça perguntas específicas sobre o que procura.
Se souber o produto, forneça preço e disponibilidade.
Seja prestativo e sugira alternativas se necessário.
""",
    
    IntentType.ENTREGA: """
Ajude o cliente a rastrear seu pedido.
Pergunte o número do pedido se necessário.
Forneça informações claras sobre o status.
Seja transparente e tranquilizador.
""",
    
    IntentType.RECLAMACAO: """
Demonstre empatia e compreensão.
Peça desculpas pelo inconveniente.
Pergunte detalhes do problema.
Ofereça solução ou transferência para atendente humano.
Seja paciente e profissional.
""",
    
    IntentType.ELOGIO: """
Agradeça o feedback positivo.
Seja genuíno e simpático.
Pergunte se há algo mais em que possa ajudar.
""",
    
    IntentType.DESPEDIDA: """
Despeça-se de forma cordial.
Agradeça pelo contato.
Deixe a porta aberta para futuras interações.
""",
    
    IntentType.DUVIDA: """
Ajude o cliente a esclarecer sua dúvida.
Seja didático e claro nas explicações.
Forneça exemplos quando apropriado.
Pergunte se ficou alguma dúvida restante.
""",
}


class IntentDetector:
    """Detector de intenções em mensagens do WhatsApp"""
    
    def __init__(self):
        self.keywords = INTENT_KEYWORDS
        self.prompts = INTENT_PROMPTS
        self.detection_history: List[Dict] = []
    
    def detect_intent(
        self, 
        message: str, 
        context: Optional[List[str]] = None
    ) -> Tuple[IntentType, float]:
        """
        Detecta a intenção principal de uma mensagem
        
        Args:
            message: Mensagem do usuário
            context: Mensagens anteriores do contexto (opcional)
            
        Returns:
            Tupla (intent_type, confidence_score)
        """
        if not message or not message.strip():
            return IntentType.DESCONHECIDO, 0.0
        
        message_lower = message.lower().strip()
        
        # Contadores de matches por intenção
        intent_scores: Dict[IntentType, int] = {
            intent: 0 for intent in IntentType
        }
        
        # Conta quantas keywords de cada intenção aparecem na mensagem
        for intent, keywords in self.keywords.items():
            for keyword in keywords:
                if keyword in message_lower:
                    intent_scores[intent] += 1
        
        # Remove intenção desconhecida da análise
        intent_scores.pop(IntentType.DESCONHECIDO, None)
        
        # Se não encontrou nenhuma keyword
        if not any(intent_scores.values()):
            detected_intent = IntentType.DESCONHECIDO
            confidence = 0.0
        else:
            # Pega a intenção com mais matches
            detected_intent = max(intent_scores, key=intent_scores.get)
            max_score = intent_scores[detected_intent]
            total_possible = len(self.keywords[detected_intent])
            
            # Calcula confiança (0.0 a 1.0)
            # Quanto mais keywords encontradas, maior a confiança
            confidence = min(max_score / 3, 1.0)  # Máximo 3 keywords = 100%
        
        # Considera contexto se disponível
        if context and confidence < 0.8:
            context_intent = self._analyze_context(context)
            if context_intent and context_intent != IntentType.DESCONHECIDO:
                # Aumenta confiança se o contexto reforça a intenção
                if context_intent == detected_intent:
                    confidence = min(confidence + 0.2, 1.0)
        
        # Log da detecção
        detection = {
            "timestamp": datetime.now().isoformat(),
            "message": message[:50],  # Primeiros 50 chars
            "intent": detected_intent.value,
            "confidence": confidence,
            "scores": {k.value: v for k, v in intent_scores.items()}
        }
        self.detection_history.append(detection)
        logger.info(f"Intent detected: {detected_intent.value} (confidence: {confidence:.2f})")
        
        return detected_intent, confidence
    
    def _analyze_context(self, context: List[str]) -> Optional[IntentType]:
        """
        Analisa mensagens anteriores para entender o contexto
        
        Args:
            context: Lista de mensagens anteriores
            
        Returns:
            Intenção predominante no contexto
        """
        if not context:
            return None
        
        # Detecta intenção das últimas mensagens
        context_intents = []
        for msg in context[-3:]:  # Últimas 3 mensagens
            intent, confidence = self.detect_intent(msg)
            if confidence > 0.5:
                context_intents.append(intent)
        
        # Retorna a intenção mais comum
        if context_intents:
            return max(set(context_intents), key=context_intents.count)
        
        return None
    
    def get_prompt_for_intent(self, intent: IntentType) -> str:
        """
        Retorna o prompt específico para uma intenção
        
        Args:
            intent: Tipo de intenção
            
        Returns:
            Prompt para a IA
        """
        return self.prompts.get(intent, self.prompts[IntentType.DUVIDA])
    
    def get_all_scores(self, message: str) -> Dict[IntentType, float]:
        """
        Calcula scores de confiança para todas as intenções
        
        Args:
            message: Mensagem do usuário
            
        Returns:
            Dicionário com scores para cada intenção
        """
        if not message or not message.strip():
            return {intent: 0.0 for intent in IntentType}
        
        message_lower = message.lower().strip()
        scores = {}
        
        # Calcular score para cada intenção
        for intent in IntentType:
            if intent == IntentType.DESCONHECIDO:
                continue
                
            keywords = self.keywords.get(intent, [])
            if not keywords:
                scores[intent] = 0.0
                continue
            
            # Contar matches
            matches = sum(1 for keyword in keywords if keyword in message_lower)
            
            # Calcular score normalizado (0.0 a 1.0)
            score = min(matches / 3.0, 1.0)
            scores[intent] = score
        
        scores[IntentType.DESCONHECIDO] = 0.0
        
        return scores
    
    def get_statistics(self) -> Dict:
        """
        Retorna estatísticas sobre as intenções detectadas
        
        Returns:
            Dicionário com estatísticas
        """
        if not self.detection_history:
            return {"total": 0, "by_intent": {}}
        
        intent_counts = {}
        total_confidence = 0.0
        
        for detection in self.detection_history:
            intent = detection["intent"]
            intent_counts[intent] = intent_counts.get(intent, 0) + 1
            total_confidence += detection["confidence"]
        
        return {
            "total": len(self.detection_history),
            "by_intent": intent_counts,
            "average_confidence": total_confidence / len(self.detection_history),
            "last_10": self.detection_history[-10:]
        }
    
    def reset_history(self):
        """Limpa o histórico de detecções"""
        self.detection_history = []
        logger.info("Intent detection history reset")


# Singleton global
_intent_detector = None


def get_intent_detector() -> IntentDetector:
    """Retorna a instância singleton do detector de intenções"""
    global _intent_detector
    if _intent_detector is None:
        _intent_detector = IntentDetector()
    return _intent_detector


# Instância singleton para uso global
intent_detector = IntentDetector()


# Funções helper para compatibilidade
def detect_intent_with_confidence(message: str) -> Tuple[IntentType, float]:
    """
    Função helper para detecção rápida de intenção com confiança
    
    Args:
        message: Mensagem do usuário
        
    Returns:
        Tupla (intent, confidence)
    """
    return intent_detector.detect_intent(message)