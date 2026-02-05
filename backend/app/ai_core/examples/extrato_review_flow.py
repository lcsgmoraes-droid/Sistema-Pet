"""
EXEMPLO COMPLETO - Human-in-the-Loop no ExtratoAnalyzer

Demonstra o fluxo completo:
1. ExtratoAnalyzer categoriza lançamento (via DecisionService)
2. DecisionService detecta confiança MEDIUM → adiciona à Review Queue
3. Frontend busca decisões pendentes
4. Humano revisa e corrige
5. ReviewService publica DecisionReviewedEvent
6. LearningService aprende com a correção
7. Próximas categorizações similares usam o padrão corrigido
"""
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from datetime import datetime

from app.ai_core.services.decision_service import DecisionService
from app.ai_core.services.review_service import ReviewService
from app.ai_core.services.learning_service import LearningService
from app.ai_core.analyzers.extrato_analyzer import ExtratoAnalyzer
from app.ai_core.domain.context import DecisionContext
from app.ai_core.domain.types import DecisionType
from app.ai_core.domain.review import HumanReviewFeedback, DecisionReviewStatus
from app.utils.logger import logger


class ExtratoReviewFlowExample:
    """
    Exemplo de fluxo completo com Human-in-the-Loop.
    """
    
    def __init__(
        self,
        db: Session,
        decision_service: DecisionService,
        review_service: ReviewService,
        learning_service: LearningService
    ):
        self.db = db
        self.decision_service = decision_service
        self.review_service = review_service
        self.learning_service = learning_service
    
    async def categorizar_com_revisao(
        self,
        user_id: int,
        lancamento_id: int,
        descricao: str,
        valor: float,
        tipo: str
    ) -> Dict[str, Any]:
        """
        Fluxo completo de categorização com possível revisão humana.
        
        Returns:
            {
                "decision_result": DecisionResult,
                "requires_review": bool,
                "review_queue_id": int (se requires_review=True)
            }
        """
        
        # 1. Criar contexto de decisão
        context = DecisionContext(
            request_id=f"cat_{lancamento_id}_{datetime.utcnow().timestamp()}",
            user_id=user_id,
            decision_type=DecisionType.CATEGORIZAR_LANCAMENTO,
            primary_data={
                "lancamento_id": lancamento_id,
                "descricao": descricao,
                "valor": valor,
                "tipo": tipo
            },
            user_input=descricao,
            metadata={
                "origem": "extrato_bancario",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        # 2. IA decide (via DecisionService)
        # DecisionService automaticamente adiciona à Review Queue se MEDIUM/LOW
        decision_result = await self.decision_service.decide(context)
        
        # 3. Verificar se precisa de revisão
        response = {
            "decision_result": decision_result.dict(),
            "requires_review": decision_result.requires_human_review,
            "confidence_score": decision_result.confidence_score,
            "confidence_level": decision_result.confidence_level.value
        }
        
        if decision_result.requires_human_review:
            # Buscar entrada na Review Queue
            review_entry = self.review_service.get_review_by_request_id(
                decision_result.request_id
            )
            
            if review_entry:
                response["review_queue_id"] = review_entry.id
                response["review_priority"] = review_entry.priority.value
                response["message"] = (
                    f"Categorização sugerida com {decision_result.confidence_score}% "
                    f"de confiança. Aguardando revisão humana."
                )
        else:
            # Confiança alta - pode aplicar automaticamente
            response["message"] = (
                f"Categorização automática com {decision_result.confidence_score}% "
                f"de confiança. Aplicada automaticamente."
            )
        
        return response
    
    async def listar_categorizacoes_pendentes(
        self,
        user_id: int,
        limit: int = 20
    ):
        """
        Lista categorizações aguardando revisão humana.
        
        Endpoint para o frontend mostrar fila de revisão.
        """
        pending_reviews = self.review_service.get_pending_reviews(
            tenant_id=user_id,
            decision_type="categorizar_lancamento",
            limit=limit
        )
        
        return [
            {
                "id": review.id,
                "request_id": review.request_id,
                "summary": review.decision_summary,
                "confidence": review.confidence_score,
                "priority": review.priority.value,
                "ai_suggestion": review.ai_decision,
                "explanation": review.ai_explanation,
                "context": review.context_data,
                "created_at": review.created_at.isoformat()
            }
            for review in pending_reviews
        ]
    
    async def revisar_categorizacao(
        self,
        request_id: str,
        reviewer_id: int,
        action: str,  # "approve", "correct", "reject"
        corrected_categoria_id: Optional[int] = None,
        comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Processa revisão humana de uma categorização.
        
        Fluxo:
        1. Validar ação
        2. Criar feedback estruturado
        3. ReviewService processa e publica evento
        4. LearningService aprende (assíncrono)
        5. Se aprovado/corrigido, aplicar ao lançamento
        """
        
        # 1. Validar e mapear ação
        action_map = {
            "approve": DecisionReviewStatus.APPROVED,
            "correct": DecisionReviewStatus.CORRECTED,
            "reject": DecisionReviewStatus.REJECTED
        }
        
        if action not in action_map:
            raise ValueError(f"Ação inválida: {action}")
        
        status = action_map[action]
        
        # 2. Criar feedback
        corrected_decision = None
        if action == "correct" and corrected_categoria_id:
            corrected_decision = {
                "categoria_id": corrected_categoria_id
            }
        
        feedback = HumanReviewFeedback(
            request_id=request_id,
            reviewer_id=reviewer_id,
            action=status,
            corrected_decision=corrected_decision,
            comment=comment
        )
        
        # 3. Processar revisão (publica evento)
        event = self.review_service.submit_review(feedback)
        
        # 4. LearningService aprende (event handler)
        await self.learning_service.process_review_event(event)
        
        # 5. Aplicar decisão ao lançamento (se aprovado/corrigido)
        if action in ["approve", "correct"]:
            final_categoria_id = (
                corrected_categoria_id 
                if action == "correct" 
                else event.original_decision.get("categoria_id")
            )
            
            # TODO: Aplicar ao lançamento real
            # await self._aplicar_categoria(lancamento_id, final_categoria_id)
        
        return {
            "success": True,
            "action": action,
            "event_id": event.event_id,
            "message": f"Revisão processada: {action}"
        }


# ==================== EXEMPLO DE USO ====================

async def exemplo_fluxo_completo():
    """
    Exemplo de uso completo do Human-in-the-Loop.
    """
    from app.db import get_db
    
    db = next(get_db())
    
    # Instanciar serviços
    decision_service = DecisionService(db, engines=[])  # Engines já configurados
    review_service = ReviewService(db)
    learning_service = LearningService(db)
    
    flow = ExtratoReviewFlowExample(
        db=db,
        decision_service=decision_service,
        review_service=review_service,
        learning_service=learning_service
    )
    
    # ===== PASSO 1: Categorizar lançamento =====
    logger.info("\\n===== PASSO 1: Categorização Automática =====")
    result = await flow.categorizar_com_revisao(
        user_id=1,
        lancamento_id=12345,
        descricao="PAGTO ENERGISA 1234567",
        valor=-152.30,
        tipo="debito"
    )
    
    logger.info(f"Confiança: {result['confidence_score']}%")
    logger.info(f"Requer revisão: {result['requires_review']}")
    logger.info(f"Mensagem: {result['message']}")
    
    if result['requires_review']:
        # ===== PASSO 2: Listar pendentes =====
        logger.info("\\n===== PASSO 2: Decisões Pendentes =====")
        pendentes = await flow.listar_categorizacoes_pendentes(user_id=1)
        logger.info(f"Total pendentes: {len(pendentes)}")
        
        if pendentes:
            primeira = pendentes[0]
            logger.info(f"\\nPrimeira da fila:")
            logger.info(f"  ID: {primeira['id']}")
            logger.info(f"  Resumo: {primeira['summary']}")
            logger.info(f"  Sugestão IA: {primeira['ai_suggestion']}")
            logger.info(f"  Prioridade: {primeira['priority']}")
            
            # ===== PASSO 3: Revisar =====
            logger.info("\\n===== PASSO 3: Revisão Humana =====")
            review_result = await flow.revisar_categorizacao(
                request_id=primeira['request_id'],
                reviewer_id=10,  # ID do usuário revisor
                action="correct",
                corrected_categoria_id=18,  # Categoria correta
                comment="Era energia mas fornecedor de água"
            )
            
            logger.info(f"Revisão: {review_result['action']}")
            logger.info(f"Event ID: {review_result['event_id']}")
            logger.info(f"Mensagem: {review_result['message']}")
    
    logger.info("\\n===== Fluxo completo finalizado =====")


if __name__ == "__main__":
    import asyncio
    asyncio.run(exemplo_fluxo_completo())
