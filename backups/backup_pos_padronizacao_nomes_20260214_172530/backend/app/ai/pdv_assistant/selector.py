"""
PDVInsightSelector - Seletor de Insights Relevantes para PDV

Responsável por:
- Filtrar insights que fazem sentido no contexto do PDV
- Priorizar insights mais relevantes
- Limitar quantidade de sugestões
- Evitar sobrecarga de informação para o operador
"""

from typing import List, Optional
from datetime import datetime
import logging

from app.insights.models import Insight, TipoInsight, SeveridadeInsight
from app.ai.pdv_assistant.models import PDVContext


logger = logging.getLogger(__name__)


class PDVInsightSelector:
    """
    Seleciona quais insights são relevantes no contexto do PDV.
    
    Regras:
    - Máximo de N sugestões por vez (default: 3)
    - Prioriza por severidade e relevância
    - Filtra insights que não fazem sentido no PDV
    - Considera o contexto da venda em andamento
    """
    
    # Tipos de insights relevantes para o PDV
    TIPOS_RELEVANTES_PDV = [
        TipoInsight.CLIENTE_RECORRENTE_ATRASADO,
        TipoInsight.CLIENTE_INATIVO,
        TipoInsight.PRODUTOS_COMPRADOS_JUNTOS,
        TipoInsight.KIT_MAIS_VANTAJOSO,
        TipoInsight.CLIENTE_VIP,
        TipoInsight.CLIENTE_EM_RISCO_CHURN,
        TipoInsight.PRODUTO_TOP_VENDAS,
    ]
    
    def __init__(self, max_sugestoes: int = 3):
        """
        Inicializa o seletor.
        
        Args:
            max_sugestoes: Número máximo de sugestões a retornar
        """
        self.max_sugestoes = max_sugestoes
    
    def selecionar_insights_para_pdv(
        self,
        pdv_context: PDVContext,
        insights_disponiveis: List[Insight]
    ) -> List[Insight]:
        """
        Seleciona insights relevantes para o contexto do PDV.
        
        Args:
            pdv_context: Contexto da venda em andamento
            insights_disponiveis: Todos os insights disponíveis
            
        Returns:
            Lista de insights selecionados (máximo max_sugestoes)
        """
        logger.info(
            f"[PDVInsightSelector] Selecionando insights para PDV "
            f"(tenant={pdv_context.tenant_id}, "
            f"itens={pdv_context.quantidade_itens})"
        )
        
        # 1. Filtrar por tenant
        insights_tenant = [
            i for i in insights_disponiveis
            if i.tenant_id == pdv_context.tenant_id
        ]
        
        # 2. Filtrar apenas tipos relevantes para PDV
        insights_relevantes = [
            i for i in insights_tenant
            if i.tipo in self.TIPOS_RELEVANTES_PDV
        ]
        
        # 3. Filtrar por contexto específico
        insights_contextuais = self._filtrar_por_contexto(
            pdv_context,
            insights_relevantes
        )
        
        # 4. Priorizar insights
        insights_priorizados = self._priorizar_insights(
            pdv_context,
            insights_contextuais
        )
        
        # 5. Limitar quantidade
        insights_selecionados = insights_priorizados[:self.max_sugestoes]
        
        logger.info(
            f"[PDVInsightSelector] Selecionados {len(insights_selecionados)} "
            f"de {len(insights_disponiveis)} insights disponíveis"
        )
        
        return insights_selecionados
    
    def _filtrar_por_contexto(
        self,
        pdv_context: PDVContext,
        insights: List[Insight]
    ) -> List[Insight]:
        """
        Filtra insights baseado no contexto específico da venda.
        
        Exemplos:
        - Se não há cliente identificado, remove insights de cliente
        - Se há produtos específicos, prioriza cross-sell relacionado
        """
        filtrados = []
        
        for insight in insights:
            # Insights de cliente requerem cliente identificado
            if insight.tipo in [
                TipoInsight.CLIENTE_RECORRENTE_ATRASADO,
                TipoInsight.CLIENTE_INATIVO,
                TipoInsight.CLIENTE_VIP,
                TipoInsight.CLIENTE_EM_RISCO_CHURN,
            ]:
                if not pdv_context.tem_cliente_identificado:
                    logger.debug(
                        f"[PDVInsightSelector] Ignorando insight {insight.tipo} "
                        f"- cliente não identificado"
                    )
                    continue
                
                # Verificar se o insight é sobre o cliente atual
                cliente_id_insight = insight.dados_contexto.get("cliente_id")
                if cliente_id_insight and cliente_id_insight != pdv_context.cliente_id:
                    logger.debug(
                        f"[PDVInsightSelector] Ignorando insight - "
                        f"cliente diferente"
                    )
                    continue
            
            # Insights de produtos juntos requerem produtos na venda
            if insight.tipo == TipoInsight.PRODUTOS_COMPRADOS_JUNTOS:
                if pdv_context.quantidade_itens == 0:
                    logger.debug(
                        f"[PDVInsightSelector] Ignorando insight de produtos juntos "
                        f"- venda vazia"
                    )
                    continue
                
                # Verificar se algum produto do insight está na venda
                produtos_insight = insight.dados_contexto.get("produto_ids", [])
                produtos_venda = pdv_context.produto_ids
                
                if not any(p in produtos_venda for p in produtos_insight):
                    logger.debug(
                        f"[PDVInsightSelector] Ignorando insight de produtos juntos "
                        f"- produtos não relacionados"
                    )
                    continue
            
            # Insights de kit requerem produtos relacionados na venda
            if insight.tipo == TipoInsight.KIT_MAIS_VANTAJOSO:
                if pdv_context.quantidade_itens == 0:
                    continue
                
                # Verificar se os produtos da venda fazem parte do kit
                produtos_kit = insight.dados_contexto.get("produto_ids", [])
                produtos_venda = pdv_context.produto_ids
                
                # Pelo menos um produto do kit deve estar na venda
                if not any(p in produtos_venda for p in produtos_kit):
                    continue
            
            filtrados.append(insight)
        
        return filtrados
    
    def _priorizar_insights(
        self,
        pdv_context: PDVContext,
        insights: List[Insight]
    ) -> List[Insight]:
        """
        Prioriza insights por relevância no contexto do PDV.
        
        Critérios:
        1. Severidade (ALTA > MEDIA > BAIXA)
        2. Tipo (alguns tipos são mais urgentes)
        3. Timestamp (mais recentes primeiro)
        """
        # Mapeamento de prioridade por tipo
        prioridade_tipo = {
            TipoInsight.CLIENTE_VIP: 10,
            TipoInsight.KIT_MAIS_VANTAJOSO: 9,
            TipoInsight.PRODUTOS_COMPRADOS_JUNTOS: 8,
            TipoInsight.CLIENTE_RECORRENTE_ATRASADO: 7,
            TipoInsight.CLIENTE_EM_RISCO_CHURN: 6,
            TipoInsight.CLIENTE_INATIVO: 5,
            TipoInsight.PRODUTO_TOP_VENDAS: 4,
        }
        
        # Mapeamento de prioridade por severidade
        prioridade_severidade = {
            SeveridadeInsight.ALTA: 100,
            SeveridadeInsight.MEDIA: 50,
            SeveridadeInsight.BAIXA: 10,
        }
        
        def calcular_score(insight: Insight) -> float:
            """Calcula score de prioridade"""
            score = 0.0
            
            # Peso da severidade
            score += prioridade_severidade.get(insight.severidade, 0)
            
            # Peso do tipo
            score += prioridade_tipo.get(insight.tipo, 0)
            
            # Penalidade por idade (insights mais recentes têm prioridade)
            idade_dias = (datetime.now() - insight.created_at).days
            score -= idade_dias * 0.1
            
            return score
        
        # Ordenar por score (maior para menor)
        insights_ordenados = sorted(
            insights,
            key=calcular_score,
            reverse=True
        )
        
        return insights_ordenados
