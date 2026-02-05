"""
Testes automatizados do Framework Global de Confiança.

Execute com: pytest backend/tests/test_confidence_framework.py -v
"""

import pytest
import sys
sys.path.append("backend")

from app.ai_core.domain.types import ConfidenceLevel
from app.ai_core.utils.confidence_calculator import (
    ConfidenceCalculator,
    ConfidenceInput,
    ConfidenceSource
)
from app.ai_core.services.decision_policy import DecisionPolicy, DecisionAction


class TestConfidenceLevel:
    """Testes para ConfidenceLevel enum"""
    
    def test_from_score_very_high(self):
        """Testa conversão para VERY_HIGH (90-100)"""
        assert ConfidenceLevel.from_score(100) == ConfidenceLevel.VERY_HIGH
        assert ConfidenceLevel.from_score(95) == ConfidenceLevel.VERY_HIGH
        assert ConfidenceLevel.from_score(90) == ConfidenceLevel.VERY_HIGH
    
    def test_from_score_high(self):
        """Testa conversão para HIGH (80-89)"""
        assert ConfidenceLevel.from_score(89) == ConfidenceLevel.HIGH
        assert ConfidenceLevel.from_score(85) == ConfidenceLevel.HIGH
        assert ConfidenceLevel.from_score(80) == ConfidenceLevel.HIGH
    
    def test_from_score_medium(self):
        """Testa conversão para MEDIUM (60-79)"""
        assert ConfidenceLevel.from_score(79) == ConfidenceLevel.MEDIUM
        assert ConfidenceLevel.from_score(70) == ConfidenceLevel.MEDIUM
        assert ConfidenceLevel.from_score(60) == ConfidenceLevel.MEDIUM
    
    def test_from_score_low(self):
        """Testa conversão para LOW (40-59)"""
        assert ConfidenceLevel.from_score(59) == ConfidenceLevel.LOW
        assert ConfidenceLevel.from_score(50) == ConfidenceLevel.LOW
        assert ConfidenceLevel.from_score(40) == ConfidenceLevel.LOW
    
    def test_from_score_very_low(self):
        """Testa conversão para VERY_LOW (0-39)"""
        assert ConfidenceLevel.from_score(39) == ConfidenceLevel.VERY_LOW
        assert ConfidenceLevel.from_score(20) == ConfidenceLevel.VERY_LOW
        assert ConfidenceLevel.from_score(0) == ConfidenceLevel.VERY_LOW


class TestConfidenceCalculator:
    """Testes para ConfidenceCalculator"""
    
    def test_calculate_simple(self):
        """Testa cálculo simples com média ponderada"""
        calculator = ConfidenceCalculator()
        
        inputs = [
            ConfidenceInput(ConfidenceSource.RULE_BASED, 100.0, 0.5, "Regra"),
            ConfidenceInput(ConfidenceSource.PATTERN_LEARNED, 80.0, 0.5, "Padrão")
        ]
        
        result = calculator.calculate(inputs)
        assert result == 90.0  # (100 * 0.5) + (80 * 0.5)
    
    def test_calculate_weighted(self):
        """Testa cálculo com pesos diferentes"""
        calculator = ConfidenceCalculator()
        
        inputs = [
            ConfidenceInput(ConfidenceSource.RULE_BASED, 100.0, 0.6, "Regra"),
            ConfidenceInput(ConfidenceSource.PATTERN_LEARNED, 80.0, 0.3, "Padrão"),
            ConfidenceInput(ConfidenceSource.HISTORICAL_ACCURACY, 90.0, 0.1, "Histórico")
        ]
        
        result = calculator.calculate(inputs)
        # (100 * 0.6) + (80 * 0.3) + (90 * 0.1) = 93
        assert result == 93.0
    
    def test_calculate_normalizes_weights(self):
        """Testa normalização automática de pesos"""
        calculator = ConfidenceCalculator()
        
        # Pesos que não somam 1.0
        inputs = [
            ConfidenceInput(ConfidenceSource.RULE_BASED, 100.0, 0.6, "Regra"),
            ConfidenceInput(ConfidenceSource.PATTERN_LEARNED, 80.0, 0.3, "Padrão")
        ]
        
        result = calculator.calculate(inputs)
        # Deve normalizar: 0.6/0.9 e 0.3/0.9
        # (100 * 0.667) + (80 * 0.333) ≈ 93.33
        assert 93.0 <= result <= 94.0
    
    def test_calculate_empty_raises_error(self):
        """Testa que inputs vazios retornam 0"""
        calculator = ConfidenceCalculator()
        result = calculator.calculate([])
        assert result == 0.0
    
    def test_calculate_invalid_score_raises_error(self):
        """Testa que score inválido levanta exceção"""
        calculator = ConfidenceCalculator()
        
        with pytest.raises(ValueError):
            calculator.calculate([
                ConfidenceInput(ConfidenceSource.RULE_BASED, 150.0, 1.0, "Inválido")
            ])
    
    def test_create_from_simple_scores(self):
        """Testa helper rápido"""
        inputs = ConfidenceCalculator.create_from_simple_scores(
            rule_score=100.0,
            pattern_score=80.0,
            history_score=90.0
        )
        
        assert len(inputs) == 3
        assert inputs[0].source == ConfidenceSource.RULE_BASED
        assert inputs[1].source == ConfidenceSource.PATTERN_LEARNED
        assert inputs[2].source == ConfidenceSource.HISTORICAL_ACCURACY
    
    def test_penalties_for_disagreement(self):
        """Testa penalidades por discordância"""
        calculator = ConfidenceCalculator()
        
        # Alta concordância (sem penalidade)
        inputs_high = [
            ConfidenceInput(ConfidenceSource.RULE_BASED, 90.0, 0.5, "R"),
            ConfidenceInput(ConfidenceSource.PATTERN_LEARNED, 92.0, 0.5, "P")
        ]
        score_high = calculator.calculate(inputs_high)
        
        # Grande discordância (com penalidade)
        inputs_low = [
            ConfidenceInput(ConfidenceSource.RULE_BASED, 90.0, 0.5, "R"),
            ConfidenceInput(ConfidenceSource.PATTERN_LEARNED, 40.0, 0.5, "P")
        ]
        score_low = calculator.calculate(inputs_low)
        
        # Score com discordância deve ser menor que a média simples
        assert score_low < 65.0  # Média seria 65, mas penalidade aplica


class TestDecisionPolicy:
    """Testes para DecisionPolicy"""
    
    def test_evaluate_very_high(self):
        """Testa política para VERY_HIGH (90-100)"""
        policy = DecisionPolicy()
        result = policy.evaluate(95, "categorizar_lancamento")
        
        assert result.confidence_level == ConfidenceLevel.VERY_HIGH
        assert result.action == DecisionAction.EXECUTE
        assert result.requires_human_review == False
        assert result.audit_level == "basic"
    
    def test_evaluate_high(self):
        """Testa política para HIGH (80-89)"""
        policy = DecisionPolicy()
        result = policy.evaluate(85, "categorizar_lancamento")
        
        assert result.confidence_level == ConfidenceLevel.HIGH
        assert result.action == DecisionAction.EXECUTE_WITH_AUDIT
        assert result.requires_human_review == False
        assert result.audit_level == "detailed"
    
    def test_evaluate_medium(self):
        """Testa política para MEDIUM (60-79)"""
        policy = DecisionPolicy()
        result = policy.evaluate(70, "categorizar_lancamento")
        
        assert result.confidence_level == ConfidenceLevel.MEDIUM
        assert result.action == DecisionAction.REQUIRE_REVIEW
        assert result.requires_human_review == True
        assert result.audit_level == "full"
    
    def test_evaluate_low(self):
        """Testa política para LOW (40-59)"""
        policy = DecisionPolicy()
        result = policy.evaluate(50, "categorizar_lancamento")
        
        assert result.confidence_level == ConfidenceLevel.LOW
        assert result.action == DecisionAction.SUGGEST_ONLY
        assert result.requires_human_review == True
    
    def test_evaluate_very_low(self):
        """Testa política para VERY_LOW (0-39)"""
        policy = DecisionPolicy()
        result = policy.evaluate(30, "categorizar_lancamento")
        
        assert result.confidence_level == ConfidenceLevel.VERY_LOW
        assert result.action == DecisionAction.IGNORE
        assert result.requires_human_review == False
    
    def test_can_execute_automatically(self):
        """Testa helper can_execute_automatically"""
        assert DecisionPolicy.can_execute_automatically(95) == True  # VERY_HIGH
        assert DecisionPolicy.can_execute_automatically(85) == True  # HIGH
        assert DecisionPolicy.can_execute_automatically(70) == False  # MEDIUM
        assert DecisionPolicy.can_execute_automatically(50) == False  # LOW
        assert DecisionPolicy.can_execute_automatically(30) == False  # VERY_LOW
    
    def test_requires_human_review(self):
        """Testa helper requires_human_review"""
        assert DecisionPolicy.requires_human_review(95) == False  # VERY_HIGH
        assert DecisionPolicy.requires_human_review(85) == False  # HIGH
        assert DecisionPolicy.requires_human_review(70) == True  # MEDIUM
        assert DecisionPolicy.requires_human_review(50) == True  # LOW
        assert DecisionPolicy.requires_human_review(30) == False  # VERY_LOW
    
    def test_strict_mode(self):
        """Testa modo estrito"""
        policy_normal = DecisionPolicy(strict_mode=False)
        policy_strict = DecisionPolicy(strict_mode=True)
        
        # Em modo estrito, MEDIUM sempre exige revisão
        result_normal = policy_normal.evaluate(70, "detectar_intencao")
        result_strict = policy_strict.evaluate(70, "detectar_intencao")
        
        # Normal pode executar em chat
        assert result_normal.action == DecisionAction.EXECUTE_WITH_AUDIT
        assert result_normal.requires_human_review == False
        
        # Estrito sempre exige revisão
        assert result_strict.requires_human_review == True
    
    def test_decision_type_overrides(self):
        """Testa overrides por tipo de decisão"""
        policy = DecisionPolicy()
        
        # Chat: MEDIUM pode executar
        result_chat = policy.evaluate(70, "detectar_intencao")
        assert result_chat.action == DecisionAction.EXECUTE_WITH_AUDIT
        
        # Financeiro: MEDIUM exige revisão
        result_finance = policy.evaluate(70, "categorizar_lancamento")
        assert result_finance.action == DecisionAction.REQUIRE_REVIEW


class TestIntegration:
    """Testes de integração do framework completo"""
    
    def test_full_flow_high_confidence(self):
        """Testa fluxo completo com alta confiança"""
        # 1. Calcular confiança
        calculator = ConfidenceCalculator()
        inputs = calculator.create_from_simple_scores(
            rule_score=95.0,
            pattern_score=88.0,
            history_score=92.0
        )
        confidence_score = calculator.calculate(inputs)
        
        # 2. Aplicar política
        policy = DecisionPolicy()
        policy_result = policy.evaluate(
            int(confidence_score),
            "categorizar_lancamento"
        )
        
        # 3. Verificar resultado
        assert confidence_score >= 90
        assert policy_result.action in [
            DecisionAction.EXECUTE,
            DecisionAction.EXECUTE_WITH_AUDIT
        ]
        assert policy_result.requires_human_review == False
    
    def test_full_flow_low_confidence(self):
        """Testa fluxo completo com baixa confiança"""
        # 1. Calcular confiança
        calculator = ConfidenceCalculator()
        inputs = calculator.create_from_simple_scores(
            rule_score=45.0,
            pattern_score=40.0,
            history_score=50.0
        )
        confidence_score = calculator.calculate(inputs)
        
        # 2. Aplicar política
        policy = DecisionPolicy()
        policy_result = policy.evaluate(
            int(confidence_score),
            "categorizar_lancamento"
        )
        
        # 3. Verificar resultado
        assert confidence_score < 60
        assert policy_result.action in [
            DecisionAction.SUGGEST_ONLY,
            DecisionAction.IGNORE
        ]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
