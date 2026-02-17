"""
InsightAIAdapter - Adaptador de Insights para AI Engine

Converte Insights do Sprint 5 em AIContext para processamento pelo AI Engine.

Responsabilidades:
- Extrair dados relevantes do Insight
- Formatar contexto estruturado
- Definir objetivo claro para a IA
- Preservar multi-tenancy
"""

from typing import Dict, Any
from app.insights.models import Insight, TipoInsight
from app.ai.contracts import AIContext


class InsightAIAdapter:
    """
    Adaptador que converte Insights em AIContext para o AI Engine.
    
    O AIContext é a estrutura que o AI Engine espera receber para
    gerar explicações contextualizadas.
    """
    
    @staticmethod
    def insight_to_ai_context(
        insight: Insight,
        objetivo: str = None
    ) -> AIContext:
        """
        Converte um Insight em AIContext.
        
        Args:
            insight: Insight do Sprint 5
            objetivo: Objetivo específico (se None, usa padrão baseado no tipo)
            
        Returns:
            AIContext pronto para o AI Engine
        """
        # Objetivo padrão baseado no tipo
        if objetivo is None:
            objetivo = InsightAIAdapter._get_default_objective(insight.tipo)
        
        # Extrai dados estruturados do insight
        dados_estruturados = InsightAIAdapter._extract_structured_data(insight)
        
        # Cria AIContext
        return AIContext(
            tenant_id=insight.user_id,
            objetivo=objetivo,
            dados_estruturados=dados_estruturados,
            metadados={
                "insight_id": insight.id,
                "insight_tipo": insight.tipo.value,
                "insight_severidade": insight.severidade.value,
                "insight_entidade": insight.entidade.value,
                "timestamp": insight.timestamp.isoformat() if insight.timestamp else None
            }
        )
    
    @staticmethod
    def _get_default_objective(tipo: TipoInsight) -> str:
        """
        Define objetivo padrão baseado no tipo de insight.
        
        Args:
            tipo: Tipo do insight
            
        Returns:
            Objetivo padrão para a IA
        """
        objetivos = {
            TipoInsight.CLIENTE_RECORRENTE_ATRASADO: (
                "Explique este insight sobre cliente atrasado e sugira a melhor "
                "abordagem para reengajar o cliente sem ser invasivo."
            ),
            TipoInsight.CLIENTE_INATIVO: (
                "Explique por que este cliente está inativo e sugira estratégias "
                "para reconquistar o cliente de forma personalizada."
            ),
            TipoInsight.PRODUTOS_COMPRADOS_JUNTOS: (
                "Explique esta oportunidade de cross-sell e sugira como apresentar "
                "esta recomendação ao cliente de forma natural."
            ),
            TipoInsight.KIT_MAIS_VANTAJOSO: (
                "Explique por que este kit é mais vantajoso e como comunicar "
                "o benefício financeiro ao cliente de forma clara."
            ),
            TipoInsight.PRODUTO_TOP_VENDAS: (
                "Explique por que este produto está em alta e sugira estratégias "
                "para maximizar as vendas."
            ),
            TipoInsight.CLIENTE_VIP: (
                "Explique por que este cliente é VIP e sugira como oferecer "
                "um tratamento diferenciado."
            ),
            TipoInsight.CLIENTE_EM_RISCO_CHURN: (
                "Explique por que este cliente está em risco de churn e sugira "
                "ações preventivas urgentes."
            ),
        }
        
        return objetivos.get(
            tipo,
            "Explique este insight e sugira ações relevantes baseadas nos dados."
        )
    
    @staticmethod
    def _extract_structured_data(insight: Insight) -> Dict[str, Any]:
        """
        Extrai dados estruturados do Insight para o AIContext.
        
        Args:
            insight: Insight do Sprint 5
            
        Returns:
            Dicionário com dados estruturados
        """
        # Base: dados do insight
        dados = {
            "tipo_insight": insight.tipo.value,
            "titulo": insight.titulo,
            "descricao": insight.descricao,
            "severidade": insight.severidade.value,
            "entidade": insight.entidade.value,
            "entidade_id": insight.entidade_id,
        }
        
        # Adiciona contexto específico
        if insight.dados_contexto:
            dados["dados_contexto"] = insight.dados_contexto
        
        # Adiciona métricas
        if insight.metricas:
            dados["metricas"] = insight.metricas
        
        # Adiciona ação sugerida (se houver)
        if insight.acao_sugerida:
            dados["acao_sugerida_original"] = insight.acao_sugerida
        
        return dados
    
    @staticmethod
    def extract_insight_summary(insight: Insight) -> Dict[str, Any]:
        """
        Extrai resumo do insight para logging/auditoria.
        
        Args:
            insight: Insight do Sprint 5
            
        Returns:
            Resumo estruturado do insight
        """
        return {
            "id": insight.id,
            "tipo": insight.tipo.value,
            "titulo": insight.titulo,
            "severidade": insight.severidade.value,
            "entidade": f"{insight.entidade.value}#{insight.entidade_id}",
            "user_id": insight.user_id,
            "timestamp": insight.timestamp.isoformat() if insight.timestamp else None
        }
    
    @staticmethod
    def validate_insight_for_explanation(insight: Insight) -> tuple[bool, str]:
        """
        Valida se um insight está pronto para explicação.
        
        Args:
            insight: Insight a validar
            
        Returns:
            (válido, mensagem de erro)
        """
        # Validação de user_id (multi-tenant)
        if not insight.user_id:
            return False, "Insight sem user_id (multi-tenant obrigatório)"
        
        # Validação de dados mínimos
        if not insight.titulo:
            return False, "Insight sem título"
        
        if not insight.descricao:
            return False, "Insight sem descrição"
        
        # Tudo OK
        return True, ""
