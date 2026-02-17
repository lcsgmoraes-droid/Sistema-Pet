"""
ConfidenceCalculator - Calculadora global de confiança do AI CORE.

Responsabilidades:
- Agregar scores de múltiplas fontes (regras, padrões, histórico)
- Normalizar para escala 0-100
- Garantir consistência semântica entre decisões
- Aplicar pesos configuráveis por tipo de decisão

Hierarquia de pesos (padrão):
1. Regras determinísticas: 60% (mais confiáveis)
2. Padrões aprendidos: 30% (médio)
3. Histórico de acerto: 10% (menos peso)
"""
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ConfidenceSource(str, Enum):
    """Fontes que contribuem para o cálculo de confiança"""
    RULE_BASED = "rule_based"              # Regras determinísticas (if/else)
    PATTERN_LEARNED = "pattern_learned"    # Padrões aprendidos de feedback
    HISTORICAL_ACCURACY = "historical_accuracy"  # Taxa de acerto histórica
    KEYWORD_MATCH = "keyword_match"        # Match de palavras-chave
    SIMILARITY_SCORE = "similarity_score"  # Similaridade com casos anteriores
    LLM_CONFIDENCE = "llm_confidence"      # Confiança do LLM
    CONSENSUS = "consensus"                # Consenso entre múltiplos modelos


@dataclass
class ConfidenceInput:
    """
    Input de uma fonte para cálculo de confiança.
    
    Example:
        ConfidenceInput(
            source=ConfidenceSource.RULE_BASED,
            score=95.0,
            weight=0.6,
            explanation="Palavra-chave 'ENERGISA' tem 95% de acerto"
        )
    """
    source: ConfidenceSource
    score: float  # 0-100
    weight: float  # 0.0-1.0
    explanation: str


class ConfidenceCalculator:
    """
    Calculadora de confiança com pesos configuráveis.
    
    Uso:
        calculator = ConfidenceCalculator()
        
        inputs = [
            ConfidenceInput(
                source=ConfidenceSource.RULE_BASED,
                score=95.0,
                weight=0.6,
                explanation="Regra exata aplicada"
            ),
            ConfidenceInput(
                source=ConfidenceSource.PATTERN_LEARNED,
                score=88.0,
                weight=0.3,
                explanation="23 aplicações bem-sucedidas"
            ),
            ConfidenceInput(
                source=ConfidenceSource.HISTORICAL_ACCURACY,
                score=92.0,
                weight=0.1,
                explanation="Taxa de acerto geral: 92%"
            )
        ]
        
        final_score = calculator.calculate(inputs)
        # Resultado: 92.5 (média ponderada normalizada)
    """
    
    # Pesos padrão por tipo de decisão
    DEFAULT_WEIGHTS = {
        "categorizar_lancamento": {
            ConfidenceSource.RULE_BASED: 0.5,
            ConfidenceSource.PATTERN_LEARNED: 0.3,
            ConfidenceSource.KEYWORD_MATCH: 0.1,
            ConfidenceSource.HISTORICAL_ACCURACY: 0.1
        },
        "sugerir_produto": {
            ConfidenceSource.PATTERN_LEARNED: 0.4,
            ConfidenceSource.SIMILARITY_SCORE: 0.3,
            ConfidenceSource.HISTORICAL_ACCURACY: 0.2,
            ConfidenceSource.RULE_BASED: 0.1
        },
        "detectar_intencao": {
            ConfidenceSource.LLM_CONFIDENCE: 0.5,
            ConfidenceSource.KEYWORD_MATCH: 0.3,
            ConfidenceSource.PATTERN_LEARNED: 0.2
        },
        # Adicionar outros tipos conforme necessário
    }
    
    def __init__(
        self,
        decision_type: Optional[str] = None,
        custom_weights: Optional[Dict[ConfidenceSource, float]] = None
    ):
        """
        Inicializa calculadora.
        
        Args:
            decision_type: Tipo de decisão para usar pesos específicos
            custom_weights: Pesos customizados (sobrescreve padrão)
        """
        self.decision_type = decision_type
        self.custom_weights = custom_weights
    
    def calculate(self, inputs: List[ConfidenceInput]) -> float:
        """
        Calcula confiança final agregando múltiplas fontes.
        
        Algoritmo:
        1. Normaliza pesos para somar 1.0
        2. Calcula média ponderada
        3. Aplica penalidades se necessário
        4. Garante range 0-100
        
        Args:
            inputs: Lista de scores de diferentes fontes
        
        Returns:
            Score final de confiança (0-100)
        
        Raises:
            ValueError: Se inputs vazio ou pesos inválidos
        """
        if not inputs:
            logger.warning("⚠️  ConfidenceCalculator: nenhum input fornecido")
            return 0.0
        
        # Validar inputs
        for inp in inputs:
            if not 0 <= inp.score <= 100:
                raise ValueError(f"Score deve estar entre 0-100, recebido: {inp.score}")
            if not 0 <= inp.weight <= 1:
                raise ValueError(f"Weight deve estar entre 0-1, recebido: {inp.weight}")
        
        # Normalizar pesos para somar 1.0
        total_weight = sum(inp.weight for inp in inputs)
        
        if total_weight == 0:
            logger.warning("⚠️  Peso total é 0, usando pesos iguais")
            normalized_inputs = [
                ConfidenceInput(
                    source=inp.source,
                    score=inp.score,
                    weight=1.0 / len(inputs),
                    explanation=inp.explanation
                )
                for inp in inputs
            ]
        else:
            normalized_inputs = [
                ConfidenceInput(
                    source=inp.source,
                    score=inp.score,
                    weight=inp.weight / total_weight,
                    explanation=inp.explanation
                )
                for inp in inputs
            ]
        
        # Calcular média ponderada
        weighted_sum = sum(
            inp.score * inp.weight 
            for inp in normalized_inputs
        )
        
        # Aplicar penalidades
        final_score = self._apply_penalties(weighted_sum, normalized_inputs)
        
        # Garantir range
        final_score = max(0.0, min(100.0, final_score))
        
        logger.debug(
            f"🧮 Confiança calculada: {final_score:.2f}% "
            f"(de {len(inputs)} fontes)"
        )
        
        return final_score
    
    def _apply_penalties(
        self,
        base_score: float,
        inputs: List[ConfidenceInput]
    ) -> float:
        """
        Aplica penalidades ao score base.
        
        Penalidades aplicadas:
        1. Discordância entre fontes (-5% a -15%)
        2. Falta de fontes importantes (-10%)
        3. Score muito baixo em fonte crítica (-20%)
        
        Args:
            base_score: Score base antes de penalidades
            inputs: Inputs normalizados
        
        Returns:
            Score com penalidades aplicadas
        """
        penalty = 0.0
        
        # 1. Penalidade por discordância
        if len(inputs) >= 2:
            scores = [inp.score for inp in inputs]
            max_diff = max(scores) - min(scores)
            
            if max_diff > 30:
                penalty += 15.0  # Grande discordância
            elif max_diff > 20:
                penalty += 10.0  # Média discordância
            elif max_diff > 10:
                penalty += 5.0   # Pequena discordância
        
        # 2. Penalidade por falta de regras determinísticas
        has_rules = any(
            inp.source == ConfidenceSource.RULE_BASED 
            for inp in inputs
        )
        if not has_rules and self.decision_type == "categorizar_lancamento":
            penalty += 10.0
        
        # 3. Penalidade por score muito baixo em fonte crítica
        for inp in inputs:
            if inp.source == ConfidenceSource.RULE_BASED and inp.score < 50:
                penalty += 20.0
                break
        
        final_score = base_score - penalty
        
        if penalty > 0:
            logger.debug(f"  ⚠️  Penalidade aplicada: -{penalty:.1f}%")
        
        return final_score
    
    def get_default_weights_for_type(
        self,
        decision_type: str
    ) -> Dict[ConfidenceSource, float]:
        """
        Retorna pesos padrão para um tipo de decisão.
        
        Args:
            decision_type: Tipo de decisão
        
        Returns:
            Dicionário de pesos por fonte
        """
        return self.DEFAULT_WEIGHTS.get(
            decision_type,
            {
                # Fallback genérico
                ConfidenceSource.RULE_BASED: 0.5,
                ConfidenceSource.PATTERN_LEARNED: 0.3,
                ConfidenceSource.HISTORICAL_ACCURACY: 0.2
            }
        )
    
    @staticmethod
    def create_from_simple_scores(
        rule_score: Optional[float] = None,
        pattern_score: Optional[float] = None,
        history_score: Optional[float] = None,
        llm_score: Optional[float] = None
    ) -> List[ConfidenceInput]:
        """
        Helper para criar inputs rapidamente.
        
        Args:
            rule_score: Score de regras determinísticas (0-100)
            pattern_score: Score de padrões aprendidos (0-100)
            history_score: Score de histórico de acerto (0-100)
            llm_score: Score de confiança do LLM (0-100)
        
        Returns:
            Lista de ConfidenceInput prontos para use
        
        Example:
            inputs = ConfidenceCalculator.create_from_simple_scores(
                rule_score=95.0,
                pattern_score=88.0,
                history_score=92.0
            )
            
            calculator = ConfidenceCalculator()
            final = calculator.calculate(inputs)
        """
        inputs = []
        
        if rule_score is not None:
            inputs.append(ConfidenceInput(
                source=ConfidenceSource.RULE_BASED,
                score=rule_score,
                weight=0.5,
                explanation=f"Score de regras: {rule_score:.1f}%"
            ))
        
        if pattern_score is not None:
            inputs.append(ConfidenceInput(
                source=ConfidenceSource.PATTERN_LEARNED,
                score=pattern_score,
                weight=0.3,
                explanation=f"Score de padrões: {pattern_score:.1f}%"
            ))
        
        if history_score is not None:
            inputs.append(ConfidenceInput(
                source=ConfidenceSource.HISTORICAL_ACCURACY,
                score=history_score,
                weight=0.1,
                explanation=f"Taxa de acerto histórica: {history_score:.1f}%"
            ))
        
        if llm_score is not None:
            inputs.append(ConfidenceInput(
                source=ConfidenceSource.LLM_CONFIDENCE,
                score=llm_score,
                weight=0.1,
                explanation=f"Confiança do LLM: {llm_score:.1f}%"
            ))
        
        return inputs
