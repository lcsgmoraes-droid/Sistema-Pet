"""
LearningService - Processa feedback humano e atualiza padrões
"""

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime
from ..models.decision_log import DecisionLog, FeedbackLog, LearningPatternModel
from ..domain.events import DecisionReviewedEvent
import logging

logger = logging.getLogger(__name__)


class LearningService:
    """
    Serviço de aprendizado contínuo com suporte a Human-in-the-Loop.

    Responsabilidades:
    - Processar feedback humano (método legado)
    - Processar DecisionReviewedEvent (novo)
    - Atualizar padrões existentes
    - Criar novos padrões
    - Deprecar padrões ruins
    - Atualizar métricas (delegado ao MetricsService)
    """

    def __init__(self, db: Session, metrics_service=None):
        self.db = db
        self.metrics_service = metrics_service  # Injetado para atualizar métricas

    async def process_feedback(
        self,
        user_id: int,
        decision_id: str,  # request_id da decisão
        feedback_type: str,
        human_decision: Optional[Dict[str, Any]] = None,
        reason: Optional[str] = None,
    ):
        """
        Processa feedback humano sobre uma decisão da IA.

        Args:
            user_id: Tenant ID
            decision_id: request_id da decisão original
            feedback_type: 'aprovado', 'rejeitado', 'corrigido'
            human_decision: Decisão final do humano (se diferente da IA)
            reason: Motivo do feedback (opcional)

        Fluxo:
        1. Buscar decisão original
        2. Registrar feedback
        3. Atualizar ou criar padrão de aprendizado
        4. Marcar decisão como revisada
        """
        logger.info(f"📝 Processando feedback: {feedback_type} | User: {user_id}")

        # 1. Buscar decisão original
        decision_log = (
            self.db.query(DecisionLog)
            .filter(
                DecisionLog.request_id == decision_id, DecisionLog.user_id == user_id
            )
            .first()
        )

        if not decision_log:
            logger.error(f"  ❌ Decisão não encontrada: {decision_id}")
            raise ValueError(f"Decisão {decision_id} não encontrada")

        # 2. Registrar feedback
        feedback_log = FeedbackLog(
            decision_id=decision_log.id,
            request_id=decision_id,
            user_id=user_id,
            feedback_type=feedback_type,
            ai_decision=decision_log.output_data.get("decision", {}),
            human_decision=human_decision,
            reason=reason,
            applied_at=datetime.utcnow(),
        )
        self.db.add(feedback_log)

        # 3. Atualizar decisão como revisada
        decision_log.was_reviewed = True
        decision_log.reviewed_at = datetime.utcnow()

        if feedback_type in ["aprovado", "corrigido"]:
            decision_log.was_applied = True
            decision_log.applied_at = datetime.utcnow()

        # 4. Aprender com feedback
        await self._learn_from_feedback(
            user_id=user_id,
            decision_log=decision_log,
            feedback_type=feedback_type,
            human_decision=human_decision,
        )

        self.db.commit()
        logger.info("  ✅ Feedback processado e padrões atualizados")

    async def _learn_from_feedback(
        self,
        user_id: int,
        decision_log: DecisionLog,
        feedback_type: str,
        human_decision: Optional[Dict],
    ):
        """Atualiza ou cria padrões de aprendizado"""

        # Extrair dados relevantes
        decision_type = decision_log.decision_type
        input_data = decision_log.input_data.get("primary_data", {})

        # Determinar output correto (IA ou humano)
        if feedback_type == "aprovado":
            correct_output = decision_log.output_data.get("decision", {})
            is_success = True
        elif feedback_type == "corrigido" and human_decision:
            correct_output = human_decision
            is_success = False
        else:
            # Rejeição completa - não aprender
            return

        # Criar assinatura de entrada
        input_signature = self._create_input_signature(decision_type, input_data)

        # Buscar padrão existente
        pattern_type = self._get_pattern_type(decision_type)
        existing_pattern = self._find_similar_pattern(
            user_id=user_id, pattern_type=pattern_type, input_signature=input_signature
        )

        if existing_pattern:
            # Atualizar padrão existente
            self._update_pattern(existing_pattern, correct_output, is_success)
        else:
            # Criar novo padrão
            self._create_pattern(
                user_id=user_id,
                pattern_type=pattern_type,
                input_signature=input_signature,
                output_preference=correct_output,
            )

    def _create_input_signature(self, decision_type: str, input_data: Dict) -> Dict:
        """Cria assinatura de entrada para matching futuro"""

        if decision_type == "categorizar_lancamento":
            # Para extratos: usar keywords da descrição
            descricao = input_data.get("descricao", "").upper()
            keywords = self._extract_keywords(descricao)

            return {
                "keywords": keywords[:5],  # Top 5
                "tipo": input_data.get("tipo"),
                "valor_range": self._get_valor_range(input_data.get("valor", 0.0)),
            }

        # Adicionar mais tipos conforme necessário
        return input_data

    def _extract_keywords(self, texto: str) -> list:
        """Extrai palavras-chave relevantes"""
        import re

        stopwords = {"DE", "DA", "DO", "E", "A", "O", "PARA", "COM"}
        palavras = re.findall(r"\b\w+\b", texto)

        return [p for p in palavras if len(p) > 3 and p not in stopwords][:5]

    def _get_valor_range(self, valor: float) -> str:
        """Categoriza valor em faixas"""
        abs_valor = abs(valor)

        if abs_valor < 50:
            return "muito_baixo"
        elif abs_valor < 200:
            return "baixo"
        elif abs_valor < 500:
            return "medio"
        elif abs_valor < 1000:
            return "alto"
        else:
            return "muito_alto"

    def _get_pattern_type(self, decision_type: str) -> str:
        """Mapeia tipo de decisão para tipo de padrão"""
        mapping = {
            "categorizar_lancamento": "categoria_por_descricao",
            "sugerir_produto": "produto_por_contexto",
        }
        return mapping.get(decision_type, decision_type)

    def _find_similar_pattern(
        self, user_id: int, pattern_type: str, input_signature: Dict
    ) -> Optional[LearningPatternModel]:
        """Busca padrão similar existente"""

        # Buscar padrões do mesmo tipo
        patterns = (
            self.db.query(LearningPatternModel)
            .filter(
                LearningPatternModel.user_id == user_id,
                LearningPatternModel.pattern_type == pattern_type,
                LearningPatternModel.is_active.is_(True),
            )
            .all()
        )

        # Calcular similaridade
        for pattern in patterns:
            similarity = self._calculate_signature_similarity(
                input_signature, pattern.input_signature
            )
            if similarity > 0.7:  # 70% similar
                return pattern

        return None

    def _calculate_signature_similarity(self, sig1: Dict, sig2: Dict) -> float:
        """Calcula similaridade entre assinaturas (0.0-1.0)"""

        # Comparar keywords (Jaccard)
        keywords1 = set(sig1.get("keywords", []))
        keywords2 = set(sig2.get("keywords", []))

        if not keywords1 or not keywords2:
            return 0.0

        intersecao = keywords1.intersection(keywords2)
        uniao = keywords1.union(keywords2)

        jaccard = len(intersecao) / len(uniao) if uniao else 0.0

        # Comparar tipo
        tipo_match = 1.0 if sig1.get("tipo") == sig2.get("tipo") else 0.0

        # Média ponderada
        return (jaccard * 0.7) + (tipo_match * 0.3)

    def _update_pattern(
        self, pattern: LearningPatternModel, correct_output: Dict, is_success: bool
    ):
        """Atualiza padrão existente"""

        pattern.occurrences += 1
        pattern.last_used_at = datetime.utcnow()

        if is_success:
            # Acertou - aumentar confiança
            pattern.confidence_boost = min(pattern.confidence_boost + 2.0, 30.0)
            pattern.success_rate = (
                pattern.success_rate * (pattern.occurrences - 1) + 100.0
            ) / pattern.occurrences
        else:
            # Errou - atualizar output e reduzir confiança
            pattern.output_preference = correct_output
            pattern.confidence_boost = max(pattern.confidence_boost - 5.0, 5.0)
            pattern.success_rate = (
                pattern.success_rate * (pattern.occurrences - 1) + 0.0
            ) / pattern.occurrences

        # Desativar se performance ruim
        if pattern.success_rate < 50.0 and pattern.occurrences > 5:
            pattern.is_active = False
            logger.warning(f"  ⚠️  Padrão #{pattern.id} desativado (performance ruim)")

    def _create_pattern(
        self,
        user_id: int,
        pattern_type: str,
        input_signature: Dict,
        output_preference: Dict,
    ):
        """Cria novo padrão"""

        pattern = LearningPatternModel(
            user_id=user_id,
            pattern_type=pattern_type,
            input_signature=input_signature,
            output_preference=output_preference,
            confidence_boost=10.0,
            occurrences=1,
            success_rate=100.0,
            is_active=True,
        )
        self.db.add(pattern)
        logger.info(f"  ✨ Novo padrão criado: {pattern_type}")

    # ==================== HUMAN-IN-THE-LOOP ====================

    async def process_review_event(self, event: DecisionReviewedEvent):
        """
        Processa DecisionReviewedEvent do Human-in-the-Loop framework.

        Este é o handler principal do evento de revisão humana.

        Args:
            event: DecisionReviewedEvent publicado pelo ReviewService

        Fluxo:
        1. Buscar decisão original no log
        2. Registrar feedback no FeedbackLog (auditoria)
        3. Ajustar padrões baseado no tipo de ação:
           - APPROVED: Aumenta confiança (IA acertou)
           - CORRECTED: Atualiza padrão com decisão correta
           - REJECTED: Reduz confiança ou desativa padrão
        """
        logger.info(
            f"🎓 Processando DecisionReviewedEvent | "
            f"Decisão: {event.decision_id} | "
            f"Ação: {event.action_taken}"
        )

        # 1. Buscar decisão original
        decision_log = (
            self.db.query(DecisionLog)
            .filter(DecisionLog.id == event.decision_log_id)
            .first()
        )

        if not decision_log:
            logger.error(f"  ❌ DecisionLog #{event.decision_log_id} não encontrado")
            return

        # 2. Registrar feedback no FeedbackLog (auditoria)
        feedback_log = FeedbackLog(
            decision_id=decision_log.id,
            request_id=event.decision_id,
            user_id=event.tenant_id,
            feedback_type=event.action_taken,
            ai_decision=event.original_decision,
            human_decision=event.corrected_data,
            reason=event.comment,
            applied_at=event.timestamp,
        )
        self.db.add(feedback_log)

        # 3. Aprender baseado no tipo de ação
        if event.action_taken == "approved":
            await self._learn_from_approval(event, decision_log)

        elif event.action_taken == "corrected":
            await self._learn_from_correction(event, decision_log)

        elif event.action_taken == "rejected":
            await self._learn_from_rejection(event, decision_log)

        # 4. Atualizar métricas (delegado ao MetricsService)
        if self.metrics_service:
            self.metrics_service.update_metrics_from_event(event)

        self.db.commit()
        logger.info(f"  ✅ Aprendizado concluído para {event.decision_id}")

    async def _learn_from_approval(
        self, event: DecisionReviewedEvent, decision_log: DecisionLog
    ):
        """
        IA acertou - aumenta confiança do padrão usado.

        Estratégia:
        - Aumenta confidence_boost do padrão
        - Incrementa success_rate
        - Reforça o padrão para uso futuro
        """
        logger.info("  ✅ Aprovado - IA acertou")

        input_data = decision_log.input_data.get("primary_data", {})
        input_signature = self._create_input_signature(
            decision_log.decision_type, input_data
        )

        pattern_type = self._get_pattern_type(decision_log.decision_type)
        pattern = self._find_similar_pattern(
            user_id=event.tenant_id,
            pattern_type=pattern_type,
            input_signature=input_signature,
        )

        if pattern:
            # Reforçar padrão existente
            pattern.occurrences += 1
            pattern.last_used_at = datetime.utcnow()
            pattern.confidence_boost = min(pattern.confidence_boost + 3.0, 30.0)
            pattern.success_rate = (
                pattern.success_rate * (pattern.occurrences - 1) + 100.0
            ) / pattern.occurrences
            logger.info(
                f"  📈 Padrão #{pattern.id} reforçado | "
                f"Boost: {pattern.confidence_boost:.1f} | "
                f"Success: {pattern.success_rate:.1f}%"
            )
        else:
            # Criar novo padrão positivo
            self._create_pattern(
                user_id=event.tenant_id,
                pattern_type=pattern_type,
                input_signature=input_signature,
                output_preference=event.original_decision,
            )

    async def _learn_from_correction(
        self, event: DecisionReviewedEvent, decision_log: DecisionLog
    ):
        """
        IA errou - atualiza padrão com decisão correta.

        Estratégia:
        - Atualiza output_preference com decisão correta
        - Reduz confidence_boost (penalidade)
        - Ajusta success_rate
        - Se padrão não existe, cria com decisão correta
        """
        logger.info("  🔧 Corrigido - IA errou")

        input_data = decision_log.input_data.get("primary_data", {})
        input_signature = self._create_input_signature(
            decision_log.decision_type, input_data
        )

        pattern_type = self._get_pattern_type(decision_log.decision_type)
        pattern = self._find_similar_pattern(
            user_id=event.tenant_id,
            pattern_type=pattern_type,
            input_signature=input_signature,
        )

        if pattern:
            # Atualizar padrão existente com correção
            pattern.occurrences += 1
            pattern.last_used_at = datetime.utcnow()
            pattern.output_preference = event.corrected_data
            pattern.confidence_boost = max(pattern.confidence_boost - 5.0, 5.0)
            pattern.success_rate = (
                pattern.success_rate * (pattern.occurrences - 1) + 0.0
            ) / pattern.occurrences

            # Desativar se performance ruim persistente
            if pattern.success_rate < 50.0 and pattern.occurrences > 5:
                pattern.is_active = False
                logger.warning(
                    f"  ⚠️  Padrão #{pattern.id} desativado (success_rate: {pattern.success_rate:.1f}%)"
                )
            else:
                logger.info(
                    f"  🔄 Padrão #{pattern.id} corrigido | "
                    f"Boost: {pattern.confidence_boost:.1f} | "
                    f"Success: {pattern.success_rate:.1f}%"
                )
        else:
            # Criar novo padrão com decisão correta
            self._create_pattern(
                user_id=event.tenant_id,
                pattern_type=pattern_type,
                input_signature=input_signature,
                output_preference=event.corrected_data,
            )

    async def _learn_from_rejection(
        self, event: DecisionReviewedEvent, decision_log: DecisionLog
    ):
        """
        Decisão completamente rejeitada - penaliza padrão.

        Estratégia:
        - Reduz fortemente confidence_boost
        - Marca como low confidence
        - Não atualiza output (não sabemos o correto)
        - Se rejeições recorrentes, desativa padrão
        """
        logger.info("  ❌ Rejeitado - decisão inadequada")

        input_data = decision_log.input_data.get("primary_data", {})
        input_signature = self._create_input_signature(
            decision_log.decision_type, input_data
        )

        pattern_type = self._get_pattern_type(decision_log.decision_type)
        pattern = self._find_similar_pattern(
            user_id=event.tenant_id,
            pattern_type=pattern_type,
            input_signature=input_signature,
        )

        if pattern:
            # Penalizar fortemente
            pattern.occurrences += 1
            pattern.confidence_boost = max(pattern.confidence_boost - 10.0, 0.0)
            pattern.success_rate = (
                pattern.success_rate * (pattern.occurrences - 1) + 0.0
            ) / pattern.occurrences

            # Desativar se muito ruim
            if pattern.success_rate < 40.0 or pattern.confidence_boost < 5.0:
                pattern.is_active = False
                logger.warning(
                    f"  🚫 Padrão #{pattern.id} desativado (rejeições recorrentes)"
                )
            else:
                logger.info(
                    f"  📉 Padrão #{pattern.id} penalizado | "
                    f"Boost: {pattern.confidence_boost:.1f} | "
                    f"Success: {pattern.success_rate:.1f}%"
                )
