"""
Sentiment Analyzer - Análise de sentimento para detecção de frustração
Detecta quando cliente está insatisfeito e precisa de atendente humano
"""
from typing import Dict, List, Tuple
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """Analisa sentimento de mensagens do cliente"""
    
    # Keywords de sentimento negativo
    NEGATIVE_KEYWORDS = {
        # Raiva/Frustração
        "raiva": -0.8,
        "irritado": -0.7,
        "furioso": -0.9,
        "puto": -0.8,
        "chato": -0.6,
        "péssimo": -0.8,
        "horrível": -0.8,
        "terrível": -0.8,
        
        # Insatisfação
        "insatisfeito": -0.7,
        "decepcionado": -0.6,
        "desapontado": -0.6,
        "inaceitável": -0.8,
        "absurdo": -0.7,
        "ridículo": -0.7,
        
        # Reclamações
        "reclamar": -0.6,
        "reclamação": -0.6,
        "problema": -0.5,
        "erro": -0.5,
        "não funciona": -0.6,
        "não entrega": -0.7,
        "não resolve": -0.7,
        "não responde": -0.7,
        "não atende": -0.7,
        
        # Urgência/Desespero
        "urgente": -0.4,
        "urgência": -0.4,
        "desesperado": -0.6,
        "socorro": -0.5,
        "ajuda": -0.3,
        
        # Xingamentos (censurado)
        "merda": -0.9,
        "porcaria": -0.8,
        "lixo": -0.8,
        "bosta": -0.9,
    }
    
    # Keywords de sentimento positivo
    POSITIVE_KEYWORDS = {
        "obrigado": 0.6,
        "obrigada": 0.6,
        "valeu": 0.5,
        "ótimo": 0.7,
        "excelente": 0.8,
        "perfeito": 0.8,
        "maravilhoso": 0.8,
        "adorei": 0.7,
        "amei": 0.7,
        "legal": 0.5,
        "bom": 0.5,
        "boa": 0.5,
        "satisfeito": 0.7,
        "feliz": 0.6,
    }
    
    # Triggers que automaticamente transferem para humano
    HANDOFF_TRIGGERS = [
        "falar com atendente",
        "falar com humano",
        "falar com pessoa",
        "falar com alguém",
        "quero um atendente",
        "preciso de atendente",
        "atendente humano",
        "atendimento humano",
        "sair do bot",
        "desativar bot",
        "parar bot",
    ]
    
    def analyze(self, message: str, conversation_history: List[str] = None) -> Dict:
        """
        Analisa sentimento de uma mensagem
        
        Args:
            message: Mensagem a ser analisada
            conversation_history: Histórico de mensagens anteriores (opcional)
            
        Returns:
            Dict com score, label, confidence, emotions, triggers, should_handoff
        """
        message_lower = message.lower()
        
        # 1. Verificar triggers automáticos
        for trigger in self.HANDOFF_TRIGGERS:
            if trigger in message_lower:
                return {
                    "score": Decimal("-0.5"),
                    "label": "manual_request",
                    "confidence": 1.0,
                    "emotions": {"frustration": 0.5},
                    "triggers": [trigger],
                    "should_handoff": True,
                    "handoff_reason": "manual_request"
                }
        
        # 2. Calcular score baseado em keywords
        score = Decimal("0.0")
        matched_keywords = []
        emotions = {}
        
        # Negativos
        for keyword, weight in self.NEGATIVE_KEYWORDS.items():
            if keyword in message_lower:
                score += Decimal(str(weight))
                matched_keywords.append(keyword)
                
                # Classificar emoção
                if keyword in ["raiva", "irritado", "furioso", "puto"]:
                    emotions["anger"] = abs(weight)
                elif keyword in ["insatisfeito", "decepcionado", "desapontado"]:
                    emotions["disappointment"] = abs(weight)
                elif keyword in ["urgente", "urgência", "desesperado", "socorro"]:
                    emotions["urgency"] = abs(weight)
                else:
                    emotions["frustration"] = abs(weight)
        
        # Positivos
        for keyword, weight in self.POSITIVE_KEYWORDS.items():
            if keyword in message_lower:
                score += Decimal(str(weight))
                matched_keywords.append(keyword)
                emotions["satisfaction"] = weight
        
        # 3. Normalizar score (-1.0 a 1.0)
        score = max(Decimal("-1.0"), min(Decimal("1.0"), score))
        
        # 4. Determinar label
        if score <= Decimal("-0.7"):
            label = "very_negative"
        elif score <= Decimal("-0.3"):
            label = "negative"
        elif score <= Decimal("0.3"):
            label = "neutral"
        elif score <= Decimal("0.7"):
            label = "positive"
        else:
            label = "very_positive"
        
        # 5. Calcular confidence
        confidence = min(1.0, len(matched_keywords) * 0.3)
        if confidence == 0:
            confidence = 0.5  # Confiança média quando não há keywords
        
        # 6. Verificar se deve fazer handoff
        should_handoff = False
        handoff_reason = None
        
        if label in ["very_negative", "negative"]:
            if score <= Decimal("-0.6"):
                should_handoff = True
                handoff_reason = "auto_sentiment"
                logger.warning(f"Sentiment trigger: score={score}, keywords={matched_keywords}")
        
        # 7. Considerar histórico (se fornecido)
        if conversation_history:
            # Se cliente está insistindo/repetindo, aumenta chance de handoff
            repeated_count = sum(1 for msg in conversation_history if msg.lower() == message_lower)
            if repeated_count >= 2:
                should_handoff = True
                handoff_reason = "auto_repeat"
                logger.warning(f"Repeated message detected: {repeated_count} times")
        
        return {
            "score": score,
            "label": label,
            "confidence": confidence,
            "emotions": emotions,
            "triggers": matched_keywords,
            "should_handoff": should_handoff,
            "handoff_reason": handoff_reason
        }
    
    def analyze_conversation_trend(self, messages: List[Dict]) -> Dict:
        """
        Analisa tendência de sentimento ao longo da conversa
        
        Args:
            messages: Lista de mensagens com {"content": str, "role": "user"|"assistant"}
            
        Returns:
            Dict com trend, avg_score, deteriorating, should_handoff
        """
        user_messages = [msg for msg in messages if msg.get("role") == "user"]
        
        if len(user_messages) < 2:
            return {
                "trend": "insufficient_data",
                "avg_score": Decimal("0.0"),
                "deteriorating": False,
                "should_handoff": False
            }
        
        # Analisar cada mensagem
        scores = []
        for msg in user_messages:
            result = self.analyze(msg["content"])
            scores.append(float(result["score"]))
        
        # Calcular média
        avg_score = Decimal(str(sum(scores) / len(scores)))
        
        # Verificar se está piorando
        recent_avg = sum(scores[-3:]) / min(3, len(scores))
        older_avg = sum(scores[:-3]) / max(1, len(scores) - 3) if len(scores) > 3 else 0
        
        deteriorating = recent_avg < older_avg - 0.2
        
        # Determinar tendência
        if recent_avg < -0.5:
            trend = "declining"
        elif recent_avg > 0.5:
            trend = "improving"
        else:
            trend = "stable"
        
        # Decidir handoff
        should_handoff = deteriorating and recent_avg < -0.4
        
        if should_handoff:
            logger.warning(f"Conversation deteriorating: recent={recent_avg:.2f}, older={older_avg:.2f}")
        
        return {
            "trend": trend,
            "avg_score": avg_score,
            "recent_avg": Decimal(str(recent_avg)),
            "deteriorating": deteriorating,
            "should_handoff": should_handoff,
            "handoff_reason": "auto_sentiment" if should_handoff else None
        }


# Singleton instance
_sentiment_analyzer = None

def get_sentiment_analyzer() -> SentimentAnalyzer:
    """Retorna instância singleton do SentimentAnalyzer"""
    global _sentiment_analyzer
    if _sentiment_analyzer is None:
        _sentiment_analyzer = SentimentAnalyzer()
    return _sentiment_analyzer
