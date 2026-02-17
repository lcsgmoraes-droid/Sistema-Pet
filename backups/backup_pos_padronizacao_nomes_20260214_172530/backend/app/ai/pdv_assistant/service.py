"""
PDVAIService - Serviço Principal de IA para PDV

Orquestra todo o fluxo de geração de sugestões contextuais
para o operador do PDV.

FLUXO:
1. Recebe PDVContext (venda em andamento)
2. Consulta Read Models relevantes
3. Consulta Insights existentes
4. Seleciona insights relevantes (via PDVInsightSelector)
5. Usa AI Engine para gerar sugestões
6. Formata sugestões para exibição
7. Retorna lista de sugestões acionáveis

RESPONSABILIDADES:
- Orquestração do fluxo completo
- Validações de entrada
- Logging e auditoria
- Multi-tenancy obrigatório
- Limitação de sugestões
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import logging

from sqlalchemy.orm import Session

from app.ai.pdv_assistant.models import (
    PDVContext,
    PDVSugestao,
    TipoPDVSugestao,
    PrioridadeSugestao,
)
from app.ai.pdv_assistant.selector import PDVInsightSelector
from app.ai.pdv_assistant.prompts import PDVPromptLibrary
from app.ai.engine import AIEngine, AIEngineFactory
from app.ai.prompt_builder import AIPromptBuilder
from app.insights.models import Insight
from app.insights.engine import InsightEngine


logger = logging.getLogger(__name__)


class PDVAIService:
    """
    Serviço principal de IA contextual para PDV.
    
    Gera sugestões inteligentes baseadas no contexto da venda
    em andamento, consumindo Insights e Read Models.
    """
    
    def __init__(
        self,
        db: Session,
        ai_engine: Optional[AIEngine] = None,
        insight_selector: Optional[PDVInsightSelector] = None,
        use_mock: bool = True
    ):
        """
        Inicializa o serviço.
        
        Args:
            db: Sessão do banco de dados
            ai_engine: Motor de IA (opcional, usa factory se não fornecido)
            insight_selector: Seletor de insights (opcional)
            use_mock: Se True, usa mock do AI Engine
        """
        self.db = db
        self.ai_engine = ai_engine or AIEngineFactory.create_engine(use_mock=use_mock)
        self.insight_selector = insight_selector or PDVInsightSelector(max_sugestoes=3)
        self.insight_engine = InsightEngine()
        self.prompt_library = PDVPromptLibrary()
    
    async def sugerir_para_pdv(
        self,
        pdv_context: PDVContext
    ) -> List[PDVSugestao]:
        """
        Método principal: gera sugestões contextuais para o PDV.
        
        Args:
            pdv_context: Contexto completo da venda em andamento
            
        Returns:
            Lista de sugestões ordenadas por prioridade
        """
        logger.info(
            f"[PDVAIService] Gerando sugestões para PDV "
            f"(tenant={pdv_context.tenant_id}, "
            f"vendedor={pdv_context.vendedor_nome}, "
            f"itens={pdv_context.quantidade_itens})"
        )
        
        try:
            # 1. Validar contexto
            self._validar_contexto(pdv_context)
            
            # 2. Buscar insights disponíveis
            insights_disponiveis = self._buscar_insights(pdv_context)
            
            logger.info(
                f"[PDVAIService] Encontrados {len(insights_disponiveis)} insights "
                f"disponíveis"
            )
            
            # 3. Selecionar insights relevantes
            insights_selecionados = self.insight_selector.selecionar_insights_para_pdv(
                pdv_context,
                insights_disponiveis
            )
            
            logger.info(
                f"[PDVAIService] Selecionados {len(insights_selecionados)} insights "
                f"relevantes"
            )
            
            # 4. Gerar sugestões
            sugestoes = await self._gerar_sugestoes(
                pdv_context,
                insights_selecionados
            )
            
            # 5. Ordenar por prioridade
            sugestoes_ordenadas = self._ordenar_sugestoes(sugestoes)
            
            logger.info(
                f"[PDVAIService] Geradas {len(sugestoes_ordenadas)} sugestões"
            )
            
            return sugestoes_ordenadas
            
        except Exception as e:
            logger.error(
                f"[PDVAIService] Erro ao gerar sugestões: {str(e)}",
                exc_info=True
            )
            # Retorna lista vazia em caso de erro
            return []
    
    def _validar_contexto(self, pdv_context: PDVContext) -> None:
        """
        Valida o contexto do PDV.
        
        Raises:
            ValueError: Se o contexto for inválido
        """
        if pdv_context.tenant_id <= 0:
            raise ValueError("tenant_id inválido")
        
        if pdv_context.vendedor_id <= 0:
            raise ValueError("vendedor_id inválido")
        
        if pdv_context.total_parcial < 0:
            raise ValueError("total_parcial não pode ser negativo")
    
    def _buscar_insights(self, pdv_context: PDVContext) -> List[Insight]:
        """
        Busca insights disponíveis para o tenant.
        
        Args:
            pdv_context: Contexto do PDV
            
        Returns:
            Lista de insights disponíveis
        """
        try:
            # Buscar insights dos últimos 30 dias
            data_limite = datetime.now() - timedelta(days=30)
            
            insights = (
                self.db.query(Insight)
                .filter(
                    Insight.tenant_id == pdv_context.tenant_id,
                    Insight.created_at >= data_limite
                )
                .all()
            )
            
            return insights
            
        except Exception as e:
            logger.error(
                f"[PDVAIService] Erro ao buscar insights: {str(e)}",
                exc_info=True
            )
            return []
    
    async def _gerar_sugestoes(
        self,
        pdv_context: PDVContext,
        insights_selecionados: List[Insight]
    ) -> List[PDVSugestao]:
        """
        Gera sugestões baseadas nos insights selecionados.
        
        Args:
            pdv_context: Contexto do PDV
            insights_selecionados: Insights relevantes
            
        Returns:
            Lista de sugestões geradas
        """
        sugestoes = []
        
        for insight in insights_selecionados:
            try:
                sugestao = await self._converter_insight_em_sugestao(
                    pdv_context,
                    insight
                )
                
                if sugestao:
                    sugestoes.append(sugestao)
                    
            except Exception as e:
                logger.error(
                    f"[PDVAIService] Erro ao converter insight {insight.id}: {str(e)}",
                    exc_info=True
                )
                continue
        
        return sugestoes
    
    async def _converter_insight_em_sugestao(
        self,
        pdv_context: PDVContext,
        insight: Insight
    ) -> Optional[PDVSugestao]:
        """
        Converte um insight em uma sugestão PDV usando a IA.
        
        Args:
            pdv_context: Contexto do PDV
            insight: Insight a ser convertido
            
        Returns:
            Sugestão gerada ou None se não for possível gerar
        """
        from app.insights.models import TipoInsight
        
        # Mapear tipo de insight para tipo de sugestão PDV
        tipo_sugestao = self._mapear_tipo_insight(insight.tipo)
        
        # Determinar prioridade baseada na severidade do insight
        from app.insights.models import SeveridadeInsight
        prioridade = PrioridadeSugestao.MEDIA
        if insight.severidade == SeveridadeInsight.ALTA:
            prioridade = PrioridadeSugestao.ALTA
        elif insight.severidade == SeveridadeInsight.BAIXA:
            prioridade = PrioridadeSugestao.BAIXA
        
        # Por enquanto, criar sugestões simples baseadas no insight
        # (Futuramente, pode usar AI Engine para gerar texto mais sofisticado)
        mensagem = self._gerar_mensagem_sugestao(pdv_context, insight)
        
        if not mensagem:
            return None
        
        return PDVSugestao(
            tipo=tipo_sugestao,
            titulo=insight.titulo[:50],  # Limitar tamanho
            mensagem=mensagem,
            prioridade=prioridade,
            dados_contexto=insight.dados_contexto,
            confianca=0.85,
            acionavel=True,
            acao_sugerida=self._gerar_acao_sugerida(insight),
            metadata={
                "insight_id": str(insight.id),
                "insight_tipo": insight.tipo.value,
                "severidade": insight.severidade.value,
            }
        )
    
    def _mapear_tipo_insight(self, tipo_insight) -> TipoPDVSugestao:
        """
        Mapeia tipo de insight para tipo de sugestão PDV.
        """
        from app.insights.models import TipoInsight
        
        mapeamento = {
            TipoInsight.PRODUTOS_COMPRADOS_JUNTOS: TipoPDVSugestao.CROSS_SELL,
            TipoInsight.KIT_MAIS_VANTAJOSO: TipoPDVSugestao.KIT_VANTAJOSO,
            TipoInsight.CLIENTE_RECORRENTE_ATRASADO: TipoPDVSugestao.CLIENTE_RECORRENTE,
            TipoInsight.CLIENTE_INATIVO: TipoPDVSugestao.CLIENTE_INATIVO,
            TipoInsight.CLIENTE_VIP: TipoPDVSugestao.CLIENTE_VIP,
            TipoInsight.CLIENTE_EM_RISCO_CHURN: TipoPDVSugestao.CLIENTE_INATIVO,
            TipoInsight.PRODUTO_TOP_VENDAS: TipoPDVSugestao.PRODUTO_POPULAR,
        }
        
        return mapeamento.get(tipo_insight, TipoPDVSugestao.OUTROS)
    
    def _gerar_mensagem_sugestao(
        self,
        pdv_context: PDVContext,
        insight: Insight
    ) -> Optional[str]:
        """
        Gera mensagem curta e clara para a sugestão.
        
        Args:
            pdv_context: Contexto do PDV
            insight: Insight original
            
        Returns:
            Mensagem formatada ou None
        """
        from app.insights.models import TipoInsight
        
        try:
            # Extrair dados relevantes do insight
            dados = insight.dados_contexto
            
            if insight.tipo == TipoInsight.PRODUTOS_COMPRADOS_JUNTOS:
                produtos = dados.get("produtos", [])
                if len(produtos) >= 2:
                    return f"{produtos[0]} costuma ser comprado junto com {produtos[1]}."
            
            elif insight.tipo == TipoInsight.KIT_MAIS_VANTAJOSO:
                economia = dados.get("economia_percentual", 0)
                nome_kit = dados.get("nome_kit", "Kit")
                return f"{nome_kit} sai {economia:.0f}% mais barato que os itens separados."
            
            elif insight.tipo == TipoInsight.CLIENTE_RECORRENTE_ATRASADO:
                dias_atraso = dados.get("dias_atraso", 0)
                return f"Cliente está {dias_atraso} dias atrasado no padrão de compra."
            
            elif insight.tipo == TipoInsight.CLIENTE_INATIVO:
                dias_sem_comprar = dados.get("dias_sem_comprar", 0)
                return f"Cliente está há {dias_sem_comprar} dias sem comprar."
            
            elif insight.tipo == TipoInsight.CLIENTE_VIP:
                total_compras = dados.get("total_compras", 0)
                return f"Cliente VIP - {total_compras} compras realizadas."
            
            elif insight.tipo == TipoInsight.PRODUTO_TOP_VENDAS:
                produto = dados.get("produto", "Este produto")
                return f"{produto} está entre os mais vendidos."
            
            # Fallback: usar descrição do insight (limitada)
            return insight.descricao[:150] if insight.descricao else None
            
        except Exception as e:
            logger.error(
                f"[PDVAIService] Erro ao gerar mensagem: {str(e)}",
                exc_info=True
            )
            return None
    
    def _gerar_acao_sugerida(self, insight: Insight) -> Optional[str]:
        """
        Gera uma ação sugerida baseada no insight.
        
        Args:
            insight: Insight original
            
        Returns:
            Ação sugerida ou None
        """
        from app.insights.models import TipoInsight
        
        acoes = {
            TipoInsight.PRODUTOS_COMPRADOS_JUNTOS: "Oferecer produto complementar",
            TipoInsight.KIT_MAIS_VANTAJOSO: "Sugerir kit ao cliente",
            TipoInsight.CLIENTE_RECORRENTE_ATRASADO: "Perguntar se precisa de algo",
            TipoInsight.CLIENTE_INATIVO: "Oferecer promoção especial",
            TipoInsight.CLIENTE_VIP: "Oferecer atendimento premium",
            TipoInsight.PRODUTO_TOP_VENDAS: "Destacar popularidade",
        }
        
        return acoes.get(insight.tipo)
    
    def _ordenar_sugestoes(
        self,
        sugestoes: List[PDVSugestao]
    ) -> List[PDVSugestao]:
        """
        Ordena sugestões por prioridade.
        
        Args:
            sugestoes: Lista de sugestões
            
        Returns:
            Lista ordenada (ALTA > MEDIA > BAIXA)
        """
        ordem_prioridade = {
            PrioridadeSugestao.ALTA: 3,
            PrioridadeSugestao.MEDIA: 2,
            PrioridadeSugestao.BAIXA: 1,
        }
        
        return sorted(
            sugestoes,
            key=lambda s: (
                ordem_prioridade.get(s.prioridade, 0),
                s.confianca
            ),
            reverse=True
        )
