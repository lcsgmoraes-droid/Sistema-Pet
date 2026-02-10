"""
DecisionService - Orquestrador de decisões com Framework Global de Confiança
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from ..domain.context import DecisionContext
from ..domain.decision import DecisionResult
from ..domain.types import ConfidenceLevel
from ..engines.base import DecisionEngine
from ..models.decision_log import DecisionLog, LearningPatternModel
from ..utils.confidence_calculator import ConfidenceCalculator
from .decision_policy import DecisionPolicy, PolicyDecision
from .review_service import ReviewService
import logging
import json

logger = logging.getLogger(__name__)


class DecisionService:
    """
    Orquestrador de decisões com Framework Global de Confiança + Human-in-the-Loop.
    
    Responsabilidades:
    - Escolher o motor adequado
    - Consultar padrões aprendidos
    - Calcular confiança agregada (ConfidenceCalculator)
    - Aplicar política de decisão (DecisionPolicy)
    - Logar todas as decisões
    - Enviar decisões MEDIUM/LOW para Review Queue
    - NUNCA executar ações diretamente
    
    Fluxo completo:
    1. Engine gera decisão inicial
    2. Calculator calcula confiança agregada
    3. Policy decide ação (EXECUTE, REVIEW, SUGGEST, IGNORE)
    4. Se REVIEW necessário --> adiciona à Review Queue
    5. Decisão é logada
    6. Sistema decide o que fazer (não o AI CORE)
    """
    
    def __init__(
        self,
        db: Session,
        engines: List[DecisionEngine],
        confidence_calculator: Optional[ConfidenceCalculator] = None,
        decision_policy: Optional[DecisionPolicy] = None,
        review_service: Optional[ReviewService] = None
    ):
        self.db = db
        self.engines = engines
        self.confidence_calculator = confidence_calculator or ConfidenceCalculator()
        self.decision_policy = decision_policy or DecisionPolicy()
        self.review_service = review_service or ReviewService(db)
    
    async def decide(self, context: DecisionContext) -> DecisionResult:
        """
        Toma uma decisão inteligente.
        
        Fluxo:
        1. Carregar padrões do usuário
        2. Tentar engine rápido (regras) primeiro
        3. Se confiança baixa, escalar para próximo engine
        4. Logar decisão
        5. Retornar resultado
        """
        logger.info(f"🧠 AI Decision Request: {context.decision_type} | User: {context.user_id}")
        
        # 1. Carregar padrões aprendidos
        user_patterns = self._load_user_patterns(
            user_id=context.user_id,
            pattern_type=self._get_pattern_type(context.decision_type.value)
        )
        
        # 2. Tentar engines em ordem de performance (rápido --> lento)
        sorted_engines = sorted(self.engines, key=lambda e: e.tier)
        
        result = None
        for engine in sorted_engines:
            if not engine.can_handle(context.decision_type.value):
                continue
            
            try:
                logger.info(f"  --> Tentando {engine.name} (tier {engine.tier})...")
                result = await engine.decide(context, user_patterns)
                
                # Se confiança alta suficiente, para aqui
                threshold = context.constraints.get("min_confidence", 80.0) if context.constraints else 80.0
                
                if result.confidence >= threshold:
                    logger.info(f"  ✅ {engine.name} retornou confiança {result.confidence:.1f}% - ACEITO")
                    break
                else:
                    logger.info(f"  ⚠️  {engine.name} retornou confiança {result.confidence:.1f}% - escalando...")
            
            except Exception as e:
                logger.error(f"  ❌ Erro no {engine.name}: {e}", exc_info=True)
                continue
        
        # Se nenhum engine funcionou
        if not result:
            result = self._create_fallback_result(context)
        
        # 3. Aplicar política de decisão (FRAMEWORK GLOBAL)
        policy_decision = self.decision_policy.evaluate(
            confidence_score=result.confidence_score,
            decision_type=result.decision_type,
            context=context.dict() if context else None
        )
        
        # Atualizar resultado com decisão de política
        result.requires_human_review = policy_decision.requires_human_review
        
        # Adicionar informações de política ao debug
        if result.debug_info is None:
            result.debug_info = {}
        result.debug_info["policy"] = {
            "action": policy_decision.action.value,
            "audit_level": policy_decision.audit_level,
            "explanation": policy_decision.explanation,
            "suggested_next_steps": policy_decision.suggested_next_steps
        }
        
        # 4. Logar decisão
        decision_log_id = self._log_decision(context, result, policy_decision)
        
        # 5. Se exigir revisão humana, adicionar à Review Queue
        if result.requires_human_review and decision_log_id:
            self._add_to_review_queue(
                result=result,
                context=context,
                decision_log_id=decision_log_id
            )
        
        logger.info(
            f"  🎯 Decisão final: {result.engine_used} | "
            f"Confiança: {result.confidence_score}% ({result.confidence_level.value}) | "
            f"Ação: {policy_decision.action.value} | "
            f"Revisão necessária: {result.requires_human_review}"
        )
        
        return result
    
    def _load_user_patterns(self, user_id: int, pattern_type: str) -> List[Dict]:
        """Carrega padrões aprendidos do usuário"""
        patterns = self.db.query(LearningPatternModel).filter(
            LearningPatternModel.user_id == user_id,
            LearningPatternModel.pattern_type == pattern_type,
            LearningPatternModel.success_rate >= 70.0,  # Apenas padrões confiáveis
            LearningPatternModel.is_active == True
        ).order_by(
            LearningPatternModel.occurrences.desc()
        ).limit(10).all()
        
        # Converter para dicts
        return [
            {
                "id": p.id,
                "input_signature": p.input_signature,
                "output_preference": p.output_preference,
                "confidence_boost": p.confidence_boost,
                "occurrences": p.occurrences,
                "success_rate": p.success_rate
            }
            for p in patterns
        ]
    
    def _get_pattern_type(self, decision_type: str) -> str:
        """Mapeia tipo de decisão para tipo de padrão"""
        mapping = {
            "categorizar_lancamento": "categoria_por_descricao",
            "sugerir_produto": "produto_por_contexto",
            "calcular_frete": "frete_por_regiao",
            "detectar_intencao": "intencao_por_mensagem"
        }
        return mapping.get(decision_type, decision_type)
    
    def _log_decision(
        self,
        context: DecisionContext,
        result: DecisionResult,
        policy_decision: Optional[PolicyDecision] = None
    ) -> Optional[int]:
        """
        Persiste decisão no banco com informações de política.
        
        Returns:
            ID do DecisionLog criado (para referência na Review Queue)
        """
        try:
            # Preparar output_data com informações de política
            output_data = result.dict()
            if policy_decision:
                output_data["policy_decision"] = {
                    "action": policy_decision.action.value,
                    "audit_level": policy_decision.audit_level,
                    "explanation": policy_decision.explanation
                }
            
            log = DecisionLog(
                request_id=result.request_id,
                user_id=context.user_id,
                decision_type=context.decision_type.value,
                input_data=context.dict(),
                output_data=output_data,
                confidence=result.confidence_score,
                engine_used=result.engine_used,
                processing_time_ms=result.processing_time_ms,
                requires_human_review=result.requires_human_review
            )
            self.db.add(log)
            self.db.commit()
            self.db.refresh(log)
            logger.info(f"  📝 Decisão logada: ID={log.id}")
            return log.id
        except Exception as e:
            logger.error(f"  ❌ Erro ao logar decisão: {e}")
            self.db.rollback()
            return None
    
    def _add_to_review_queue(
        self,
        result: DecisionResult,
        context: DecisionContext,
        decision_log_id: int
    ):
        """
        Adiciona decisão à fila de revisão humana.
        
        Chamado automaticamente quando requires_human_review=True.
        """
        try:
            # Criar resumo legível para o revisor
            decision_summary = self._create_decision_summary(result, context)
            
            self.review_service.add_to_queue(
                request_id=result.request_id,
                decision_log_id=decision_log_id,
                tenant_id=context.user_id,
                decision_type=result.decision_type,
                decision_summary=decision_summary,
                confidence_score=result.confidence_score,
                confidence_level=result.confidence_level.value,
                context_data={
                    "user_input": context.user_input,
                    "metadata": context.metadata,
                    "decision_reasons": result.reasons
                },
                ai_decision=result.decision,
                ai_explanation=result.explanation
            )
            logger.info(f"  📋 Decisão adicionada à Review Queue: {result.request_id}")
        except Exception as e:
            logger.error(f"  ❌ Erro ao adicionar à Review Queue: {e}", exc_info=True)
    
    def _create_decision_summary(
        self,
        result: DecisionResult,
        context: DecisionContext
    ) -> str:
        """
        Cria resumo legível da decisão para o revisor.
        
        Formato: "Tipo: valor --> sugestão"
        """
        decision_type = result.decision_type.replace("_", " ").title()
        
        # Tentar extrair valor principal da decisão
        main_value = "indefinido"
        if isinstance(result.decision, dict):
            # Tentar encontrar campo 'nome', 'descricao', 'id', etc
            for key in ["nome", "categoria_nome", "descricao", "valor", "resultado"]:
                if key in result.decision:
                    main_value = str(result.decision[key])
                    break
        
        return f"{decision_type}: {main_value} (confiança: {result.confidence_score}%)"
    
    def _create_fallback_result(self, context: DecisionContext) -> DecisionResult:
        """Cria resultado de fallback quando tudo falha"""
        return DecisionResult(
            request_id=context.request_id,
            decision_type=context.decision_type.value,
            decision={"error": "Nenhum motor disponível pôde processar"},
            confidence_score=0,
            confidence_level=ConfidenceLevel.VERY_LOW,
            explanation="Sistema temporariamente indisponível ou sem engines compatíveis",
            reasons=["Nenhum motor conseguiu processar a requisição"],
            evidence=[],
            alternatives=[],
            engine_used="fallback",
            processing_time_ms=0.0,
            requires_human_review=True,
            suggested_actions=["tentar_novamente", "contatar_suporte"]
        )
