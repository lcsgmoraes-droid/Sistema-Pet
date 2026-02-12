"""
"""ExtratoAnalyzer - Categorização de extratos com Framework Global de Confiança
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from ..services.decision_service import DecisionService
from ..services.decision_policy import DecisionPolicy
from ..domain.context import DecisionContext, DecisionType


class ExtratoAnalyzer:
    """
    Fachada de alto nível para categorização de extratos bancários.
    
    FRAMEWORK GLOBAL DE CONFIANÇA APLICADO:
    - ≥ 90%: Executar automaticamente (VERY_HIGH)
    - 80-89%: Executar + log de auditoria (HIGH)
    - 60-79%: Exigir revisão humana (MEDIUM)
    - 40-59%: Apenas sugerir (LOW)
    - < 40%: Ignorar ou pedir mais dados (VERY_LOW)
    
    Substitui: app.ia.extrato_ia.MotorCategorizacaoIA
    
    Vantagens sobre o sistema anterior:
    - Decisões explicáveis (reasons + evidence + explanation)
    - Score de confiança padronizado (0-100)
    - Política global de execução
    - Logs automáticos de auditoria
    - Feedback loop integrado
    - Padrões aprendidos automaticamente
    """
    
    def __init__(self, decision_service: DecisionService, db: Session):
        self.decision_service = decision_service
        self.db = db
    
    async def categorizar_lancamento(
        self,
        user_id: int,
        descricao: str,
        valor: float,
        data: str,
        tipo: Optional[str] = None,
        historico_recente: Optional[List[Dict]] = None,
        categorias_disponiveis: Optional[List[Dict]] = None
    ):
        """
        Categoriza um lançamento bancário usando AI Core.
        
        FRAMEWORK DE CONFIANÇA:
        - A IA retorna: decisão + confidence_score (0-100) + explanation + evidence
        - DecisionPolicy decide: EXECUTE | REQUIRE_REVIEW | SUGGEST | IGNORE
        - Sistema executa baseado na política (não a IA)
        
        Args:
            user_id: ID do tenant
            descricao: Descrição do lançamento (ex: "PIX ENVIADO ENERGISA")
            valor: Valor (negativo = saída, positivo = entrada)
            data: Data da transação (ISO format)
            tipo: 'entrada' ou 'saida' (opcional, inferido do valor)
            historico_recente: Lançamentos recentes similares (opcional)
            categorias_disponiveis: Categorias disponíveis para escolher (opcional)
        
        Returns:
            DecisionResult com:
            - decision: {"categoria_id": int, "categoria_nome": str, "beneficiario": str}
            - confidence_score: 0-100
            - confidence_level: VERY_LOW | LOW | MEDIUM | HIGH | VERY_HIGH
            - explanation: texto claro do por que da decisão
            - reasons: ["Motivo 1", "Motivo 2"]
            - evidence: [Evidence(...)]
            - requires_human_review: bool
            - debug_info.policy: informações da política aplicada
        
        Exemplo de uso:
            analyzer = ExtratoAnalyzer(decision_service, db)
            result = await analyzer.categorizar_lancamento(
                user_id=123,
                descricao="PIX ENVIADO ENERGISA DISTRIBUIDORA",
                valor=-150.45,
                data="2026-01-23"
            )
            
            # Verificar política
            if result.requires_human_review:
                # Enviar para fila de revisão humana
                await enqueue_for_review(result)
            elif result.confidence_score >= 80:
                # Aplicar automaticamente
                await aplicar_categoria(lancamento_id, result.decision)
            else:
                # Apenas sugerir
                await mostrar_sugestao(result)
        """
        
        # Inferir tipo se não fornecido
        if not tipo:
            tipo = "saida" if valor < 0 else "entrada"
        
        # Montar contexto para a IA
        context = DecisionContext(
            user_id=user_id,
            decision_type=DecisionType.CATEGORIZAR_LANCAMENTO,
            primary_data={
                "descricao": descricao,
                "valor": valor,
                "data": data,
                "tipo": tipo
            },
            additional_data={
                "historico_ultimos_30d": historico_recente or [],
                "categorias_disponiveis": categorias_disponiveis or []
            },
            constraints={
                "min_confidence": 80.0  # Aplicar automaticamente só se >= 80%
            },
            source="extrato_service"
        )
        
        # Delegar para decision service
        result = await self.decision_service.decide(context)
        
        # Se IA retornou categoria por nome mas não ID, buscar no DB
        if result.decision.get("categoria_nome") and not result.decision.get("categoria_id"):
            categoria_id = self._buscar_categoria_id(
                user_id=user_id,
                categoria_nome=result.decision["categoria_nome"]
            )
            result.decision["categoria_id"] = categoria_id
        
        return result
    
    def _buscar_categoria_id(self, user_id: int, categoria_nome: str) -> Optional[int]:
        """
        Busca ID da categoria pelo nome.
        
        NOTA: Mantém compatibilidade com sistema existente que usa
        CategoriaFinanceira de financeiro_models.py
        """
        from app.financeiro_models import CategoriaFinanceira
        
        categoria = self.db.query(CategoriaFinanceira).filter(
            CategoriaFinanceira.user_id == user_id,
            CategoriaFinanceira.nome.ilike(f"%{categoria_nome}%")
        ).first()
        
        if categoria:
            return categoria.id
        
        # Criar categoria automaticamente se não existir
        nova_categoria = CategoriaFinanceira(
            user_id=user_id,
            nome=categoria_nome,
            tipo="despesa",  # Default, pode ajustar
            cor="#6C757D"  # Cinza neutro
        )
        self.db.add(nova_categoria)
        self.db.flush()
        
        return nova_categoria.id
    
    async def aplicar_categoria_automatica(
        self,
        lancamento_id: int,
        user_id: int,
        result: Any  # DecisionResult
    ) -> bool:
        """
        Aplica categoria automaticamente se política permitir.
        
        POLÍTICA GLOBAL:
        - confidence_score >= 80: pode executar automaticamente
        - confidence_score 60-79: exige revisão humana
        - confidence_score < 60: apenas sugestão
        
        Returns:
            True se aplicou automaticamente, False se enviou para revisão
        """
        # Verificar se policy permite execução automática
        can_execute = DecisionPolicy.can_execute_automatically(result.confidence_score)
        
        if can_execute and not result.requires_human_review:
            # Buscar lançamento importado
            from app.ia.aba7_extrato_models import LancamentoImportado
            
            lancamento = self.db.query(LancamentoImportado).filter(
                LancamentoImportado.id == lancamento_id,
                LancamentoImportado.usuario_id == user_id
            ).first()
            
            if not lancamento:
                return False
            
            # Aplicar categoria
            lancamento.categoria_financeira_id = result.decision.get("categoria_id")
            lancamento.confianca_ia = result.confidence_score / 100.0  # Converter para 0-1
            lancamento.status_validacao = "aprovado_automaticamente"
            lancamento.confirmado_usuario = True
            
            # Adicionar metadados de auditoria
            if hasattr(lancamento, 'metadata_ia'):
                lancamento.metadata_ia = {
                    "confidence_score": result.confidence_score,
                    "confidence_level": result.confidence_level.value,
                    "explanation": result.explanation,
                    "applied_automatically": True,
                    "timestamp": result.timestamp.isoformat()
                }
            
            self.db.commit()
            return True
        else:
            # Enviar para revisão humana
            # TODO: Implementar fila de revisão
            return False
