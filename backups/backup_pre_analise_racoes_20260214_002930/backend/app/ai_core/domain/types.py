"""
Enums e tipos do AI Core
"""
from enum import Enum


class DecisionType(str, Enum):
    """Tipos de decisão que a IA pode tomar"""
    CATEGORIZAR_LANCAMENTO = "categorizar_lancamento"
    SUGERIR_PRODUTO = "sugerir_produto"
    CALCULAR_FRETE = "calcular_frete"
    DETECTAR_INTENCAO = "detectar_intencao"
    PREVER_DEMANDA = "prever_demanda"
    OTIMIZAR_ROTA = "otimizar_rota"
    DETECTAR_ANOMALIA = "detectar_anomalia"
    RECOMENDAR_ACAO = "recomendar_acao"


class ConfidenceLevel(str, Enum):
    """
    Níveis categóricos de confiança - FRAMEWORK GLOBAL.
    
    Política de decisão baseada em confiança:
    
    - VERY_LOW (0-39):   Ignorar ou pedir mais dados
    - LOW (40-59):       Apenas sugerir, não executar
    - MEDIUM (60-79):    Exigir revisão humana antes de executar
    - HIGH (80-89):      Executar + log de auditoria detalhado
    - VERY_HIGH (90-100): Executar automaticamente com segurança
    
    Esta é a ÚNICA fonte de verdade para níveis de confiança no AI CORE.
    """
    VERY_LOW = "very_low"        # 0-39: Ignorar ou pedir mais dados
    LOW = "low"                  # 40-59: Apenas sugerir
    MEDIUM = "medium"            # 60-79: Exigir revisão humana
    HIGH = "high"                # 80-89: Executar + log de auditoria
    VERY_HIGH = "very_high"      # 90-100: Executar automaticamente
    
    @classmethod
    def from_score(cls, score: float) -> "ConfidenceLevel":
        """
        Converte score numérico (0-100) em nível categórico.
        
        Args:
            score: Score de confiança (0-100)
        
        Returns:
            ConfidenceLevel correspondente
        
        Examples:
            >>> ConfidenceLevel.from_score(95.0)
            <ConfidenceLevel.VERY_HIGH: 'very_high'>
            
            >>> ConfidenceLevel.from_score(75.0)
            <ConfidenceLevel.MEDIUM: 'medium'>
        """
        if score >= 90:
            return cls.VERY_HIGH
        elif score >= 80:
            return cls.HIGH
        elif score >= 60:
            return cls.MEDIUM
        elif score >= 40:
            return cls.LOW
        else:
            return cls.VERY_LOW


class FeedbackType(str, Enum):
    """Tipos de feedback humano"""
    APROVADO = "aprovado"              # Humano concordou
    REJEITADO = "rejeitado"            # Humano discordou
    CORRIGIDO = "corrigido"            # Humano alterou a sugestão
    IGNORADO = "ignorado"              # Humano não aplicou
    APLICADO_PARCIALMENTE = "aplicado_parcialmente"
