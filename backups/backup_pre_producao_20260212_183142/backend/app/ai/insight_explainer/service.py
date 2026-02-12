"""
InsightExplanationService - Serviço de Explicação de Insights

Orquestra a explicação de insights usando o AI Engine (Passo 1).

Fluxo:
1. Recebe Insight (Sprint 5)
2. Valida insight
3. Converte para AIContext (via InsightAIAdapter)
4. Aplica prompt especializado (via InsightPromptLibrary)
5. Envia para AIEngine
6. Formata resposta estruturada
7. Retorna explicação auditável

Responsabilidades:
- Orquestração do fluxo completo
- Validações de entrada
- Logging e auditoria
- Formatação de saída
- Multi-tenancy obrigatório
"""

from typing import Dict, Any, Optional
from datetime import datetime
import logging

from app.insights.models import Insight
from app.ai.engine import AIEngine, AIEngineFactory
from app.ai.contracts import AIResponse, AIContext
from app.ai.insight_explainer.adapter import InsightAIAdapter
from app.ai.insight_explainer.prompts import InsightPromptLibrary
from app.ai.prompt_builder import AIPromptBuilder


logger = logging.getLogger(__name__)


class InsightExplanation:
    """
    Estrutura de dados para explicação de insight.
    
    Representa a explicação gerada pela IA de forma estruturada e auditável.
    """
    
    def __init__(
        self,
        insight_id: str,
        tipo_insight: str,
        titulo: str,
        explicacao: str,
        sugestao: str,
        confianca: float,
        fonte_dados: list,
        tenant_id: int,
        timestamp: datetime,
        metadata: Dict[str, Any]
    ):
        self.insight_id = insight_id
        self.tipo_insight = tipo_insight
        self.titulo = titulo
        self.explicacao = explicacao
        self.sugestao = sugestao
        self.confianca = confianca
        self.fonte_dados = fonte_dados
        self.tenant_id = tenant_id
        self.timestamp = timestamp
        self.metadata = metadata
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return {
            "insight_id": self.insight_id,
            "tipo_insight": self.tipo_insight,
            "titulo": self.titulo,
            "explicacao": self.explicacao,
            "sugestao": self.sugestao,
            "confianca": self.confianca,
            "fonte_dados": self.fonte_dados,
            "tenant_id": self.tenant_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "metadata": self.metadata
        }


class InsightExplanationService:
    """
    Serviço principal de explicação de insights.
    
    Usa o AI Engine (Passo 1) para transformar insights técnicos
    em explicações compreensíveis para humanos.
    """
    
    def __init__(
        self,
        ai_engine: Optional[AIEngine] = None,
        use_mock: bool = True
    ):
        """
        Inicializa o serviço.
        
        Args:
            ai_engine: Motor de IA customizado (opcional)
            use_mock: Se True, usa mock; se False, usa OpenAI (futuro)
        """
        if ai_engine is None:
            self.ai_engine = AIEngineFactory.create_mock_engine()
        else:
            self.ai_engine = ai_engine
        
        self.adapter = InsightAIAdapter()
        self.prompt_library = InsightPromptLibrary()
        self.use_mock = use_mock
    
    async def explicar_insight(
        self,
        insight: Insight,
        tenant_id: Optional[int] = None
    ) -> InsightExplanation:
        """
        Gera explicação compreensível de um insight.
        
        Args:
            insight: Insight do Sprint 5
            tenant_id: ID do tenant (usa do insight se None)
            
        Returns:
            InsightExplanation estruturada
            
        Raises:
            ValueError: Se insight inválido
        """
        # Validação
        valido, erro = self.adapter.validate_insight_for_explanation(insight)
        if not valido:
            logger.error(f"[InsightExplanationService] Insight inválido: {erro}")
            raise ValueError(f"Insight inválido: {erro}")
        
        # Tenant ID
        tenant_id = tenant_id or insight.user_id
        
        logger.info(
            f"[InsightExplanationService] Explicando insight "
            f"{insight.id} (tipo={insight.tipo.value}, tenant={tenant_id})"
        )
        
        # 1. Converter Insight para AIContext
        ai_context = self.adapter.insight_to_ai_context(insight)
        
        # 2. Obter prompt especializado
        prompt_especializado = self.prompt_library.get_prompt_for_tipo(
            tipo=insight.tipo,
            dados_insight=ai_context.dados_estruturados
        )
        
        # 3. Substituir placeholders
        prompt_final = prompt_especializado.replace("{{contexto}}", "")
        prompt_final = prompt_final.replace("{{objetivo}}", ai_context.objetivo)
        
        # 4. Gerar resposta
        if self.use_mock:
            # Em modo mock, gerar resposta simulada diretamente
            from app.ai.contracts import AIResponse
            
            # Gerar resposta específica baseada no tipo de insight
            explicacao_mock, sugestao_mock = self._generate_mock_response(
                insight, ai_context
            )
            
            ai_response = AIResponse(
                resposta=f"{explicacao_mock}\n\nSugestão: {sugestao_mock}",
                explicacao=(
                    f"Análise realizada considerando:\n"
                    f"- Tipo de insight: {insight.tipo.value}\n"
                    f"- Severidade: {insight.severidade}\n"
                    f"- Dados contextuais disponíveis\n"
                    f"- Padrões históricos identificados"
                ),
                fonte_dados=[
                    "Insight Engine (Sprint 5)",
                    f"Insight ID: {insight.id}",
                    "Read Models Cliente/Vendas"
                ],
                confianca=0.85,
                timestamp=datetime.now(),
                tenant_id=tenant_id,
                metadata={
                    "modo": "mock",
                    "tipo_insight": insight.tipo.value,
                    "prompt_usado": "especializado",
                    "insight_id": insight.id
                }
            )
        else:
            # Em produção, usar AI Engine real
            # (a ser implementado com OpenAI)
            ai_response = await self.ai_engine.generate_response(
                context=ai_context.dados_estruturados,
                objetivo=prompt_final,
                tenant_id=tenant_id
            )
        
        # 5. Formatar explicação estruturada
        explicacao = self._format_explanation(
            insight=insight,
            ai_response=ai_response,
            tenant_id=tenant_id
        )
        
        logger.info(
            f"[InsightExplanationService] Explicação gerada com "
            f"confiança {explicacao.confianca * 100:.1f}%"
        )
        
        return explicacao
    
    def _generate_mock_response(
        self,
        insight: Insight,
        ai_context: AIContext
    ) -> tuple[str, str]:
        """
        Gera resposta mock específica baseada no tipo de insight.
        
        Args:
            insight: Insight original
            ai_context: Contexto da IA
            
        Returns:
            (explicacao, sugestao)
        """
        from app.insights.models import TipoInsight
        
        dados = ai_context.dados_estruturados
        
        if insight.tipo == TipoInsight.CLIENTE_RECORRENTE_ATRASADO:
            cliente_nome = dados.get('cliente_nome', 'Cliente')
            dias_atraso = dados.get('dias_atraso', 'X')
            produto_habitual = dados.get('produto_habitual', 'produto')
            
            explicacao = (
                f"O cliente {cliente_nome} tem um padrão de compra muito "
                f"consistente e está {dias_atraso} dias atrasado na próxima "
                f"compra esperada de {produto_habitual}. Isso é incomum e "
                f"pode indicar que o cliente migrou para um concorrente ou "
                f"está enfrentando alguma dificuldade financeira temporária."
            )
            
            sugestao = (
                f"Entre em contato via WhatsApp em tom amigável, perguntando "
                f"como está o pet dele e oferecendo ajuda. Considere uma "
                f"promoção especial de 'volta' caso ele mencione preço como "
                f"motivo do afastamento."
            )
            
        elif insight.tipo == TipoInsight.CLIENTE_INATIVO:
            cliente_nome = dados.get('cliente_nome', 'Cliente')
            dias_inativo = dados.get('dias_desde_ultima_compra', 'X')
            
            explicacao = (
                f"O cliente {cliente_nome} não compra há {dias_inativo} dias, "
                f"ultrapassando significativamente o padrão normal de retorno. "
                f"Clientes inativos por mais de 90 dias têm apenas 15% de "
                f"chance de retorno espontâneo."
            )
            
            sugestao = (
                f"Crie uma campanha de reconquista personalizada com desconto "
                f"especial 'para clientes antigos'. Use múltiplos canais "
                f"(WhatsApp + email) e destaque novidades no estoque desde a "
                f"última visita."
            )
            
        elif insight.tipo == TipoInsight.PRODUTOS_COMPRADOS_JUNTOS:
            produto1 = dados.get('produto1', 'Produto A')
            produto2 = dados.get('produto2', 'Produto B')
            percentual = dados.get('percentual_juntos', 'X')
            
            explicacao = (
                f"Identificamos que {percentual}% dos clientes que compram "
                f"{produto1} também compram {produto2}. Esta é uma forte "
                f"correlação que indica uma necessidade complementar natural."
            )
            
            sugestao = (
                f"Configure o PDV para sugerir automaticamente {produto2} "
                f"quando {produto1} for adicionado ao carrinho. Treine a "
                f"equipe para fazer essa oferta casada de forma natural."
            )
            
        elif insight.tipo == TipoInsight.KIT_MAIS_VANTAJOSO:
            economia = dados.get('economia_reais', 'X')
            produtos_kit = dados.get('produtos', 'produtos do kit')
            
            explicacao = (
                f"O cliente está comprando {produtos_kit} separadamente, "
                f"pagando R$ {economia} a mais do que pagaria no kit. "
                f"Ele provavelmente não sabe que existe essa opção mais econômica."
            )
            
            sugestao = (
                f"Na próxima compra, mostre a comparação de preços lado a lado "
                f"no PDV. Use linguagem: 'Olha, você pode economizar R$ {economia} "
                f"comprando o kit em vez dos itens separados!'"
            )
            
        elif insight.tipo == TipoInsight.CLIENTE_VIP:
            cliente_nome = dados.get('cliente_nome', 'Cliente')
            ltv = dados.get('lifetime_value', 'X')
            
            explicacao = (
                f"O cliente {cliente_nome} tem um LTV de R$ {ltv}, colocando-o "
                f"no top 5% da base. Clientes VIP merecem tratamento "
                f"diferenciado para garantir sua fidelidade de longo prazo."
            )
            
            sugestao = (
                f"Ofereça benefícios exclusivos: desconto permanente de 10%, "
                f"prioridade em novos produtos, brindes surpresa ocasionais. "
                f"Mantenha relacionamento próximo e personalizado."
            )
            
        elif insight.tipo == TipoInsight.CLIENTE_EM_RISCO_CHURN:
            cliente_nome = dados.get('cliente_nome', 'Cliente')
            sinais = dados.get('sinais_risco', 'comportamento atípico')
            
            explicacao = (
                f"O cliente {cliente_nome} está mostrando {sinais} que "
                f"historicamente precedem o abandono. A janela de retenção "
                f"é de apenas 15 dias antes do churn se tornar irreversível."
            )
            
            sugestao = (
                f"Ação urgente: contato imediato da gerência, oferta especial "
                f"de retenção, pesquisa de satisfação para entender problemas. "
                f"Prioridade máxima nas próximas 48 horas."
            )
            
        elif insight.tipo == TipoInsight.PRODUTO_TOP_VENDAS:
            produto = dados.get('produto_nome', 'Produto')
            crescimento = dados.get('crescimento_percentual', 'X')
            
            explicacao = (
                f"O produto {produto} teve crescimento de {crescimento}% nas "
                f"vendas e está se tornando um best-seller. Isso indica forte "
                f"demanda e alta satisfação dos clientes."
            )
            
            sugestao = (
                f"Garanta estoque adequado, negocie melhores condições com "
                f"fornecedor devido ao volume, considere criar kits com este "
                f"produto como âncora. Use-o como destaque em campanhas."
            )
            
        else:
            # Genérico para tipos não mapeados
            explicacao = (
                f"Este insight identificou um padrão relevante que merece "
                f"atenção. Baseado nos dados históricos e comportamento "
                f"observado, há uma oportunidade de ação."
            )
            
            sugestao = (
                f"Analise os dados em detalhes e defina uma ação específica "
                f"baseada no contexto do seu negócio e prioridades atuais."
            )
        
        return explicacao, sugestao
    
    def _format_explanation(
        self,
        insight: Insight,
        ai_response: AIResponse,
        tenant_id: int
    ) -> InsightExplanation:
        """
        Formata a resposta da IA em InsightExplanation estruturado.
        
        Args:
            insight: Insight original
            ai_response: Resposta do AI Engine
            tenant_id: ID do tenant
            
        Returns:
            InsightExplanation formatado
        """
        # Extrair explicação e sugestão da resposta da IA
        # No mock, a resposta vem em um bloco. Em produção, pode vir estruturada.
        explicacao_texto, sugestao_texto = self._parse_ai_response(
            ai_response.resposta
        )
        
        return InsightExplanation(
            insight_id=insight.id,
            tipo_insight=insight.tipo.value,
            titulo=insight.titulo,
            explicacao=explicacao_texto,
            sugestao=sugestao_texto,
            confianca=ai_response.confianca,
            fonte_dados=ai_response.fonte_dados,
            tenant_id=tenant_id,
            timestamp=ai_response.timestamp,
            metadata={
                "insight_severidade": insight.severidade.value,
                "insight_entidade": insight.entidade.value,
                "insight_entidade_id": insight.entidade_id,
                "ai_explicacao_original": ai_response.explicacao,
                "ai_metadata": ai_response.metadata,
                "modo": "mock" if self.use_mock else "production"
            }
        )
    
    def _parse_ai_response(self, resposta: str) -> tuple[str, str]:
        """
        Separa explicação de sugestão na resposta da IA.
        
        Args:
            resposta: Resposta completa da IA
            
        Returns:
            (explicacao, sugestao)
        """
        # Tenta identificar seções na resposta
        # Padrões comuns: "Sugestão:", "Recomendação:", etc.
        
        marcadores_sugestao = [
            "Sugestão:",
            "Recomendação:",
            "Ação sugerida:",
            "O que fazer:",
            "Próximos passos:"
        ]
        
        explicacao = resposta
        sugestao = ""
        
        for marcador in marcadores_sugestao:
            if marcador in resposta:
                partes = resposta.split(marcador, 1)
                explicacao = partes[0].strip()
                sugestao = partes[1].strip()
                break
        
        # Se não encontrou marcador, tenta quebrar em 2/3 e 1/3
        if not sugestao:
            linhas = resposta.split(". ")
            ponto_corte = int(len(linhas) * 0.66)
            explicacao = ". ".join(linhas[:ponto_corte]) + "."
            sugestao = ". ".join(linhas[ponto_corte:])
        
        return explicacao, sugestao
    
    async def explicar_multiplos_insights(
        self,
        insights: list[Insight],
        tenant_id: Optional[int] = None
    ) -> list[InsightExplanation]:
        """
        Explica múltiplos insights em lote.
        
        Args:
            insights: Lista de insights
            tenant_id: ID do tenant (usa do primeiro insight se None)
            
        Returns:
            Lista de explicações
        """
        if not insights:
            return []
        
        tenant_id = tenant_id or insights[0].user_id
        
        logger.info(
            f"[InsightExplanationService] Explicando {len(insights)} insights "
            f"(tenant={tenant_id})"
        )
        
        explicacoes = []
        
        for insight in insights:
            try:
                explicacao = await self.explicar_insight(insight, tenant_id)
                explicacoes.append(explicacao)
            except Exception as e:
                logger.error(
                    f"[InsightExplanationService] Erro ao explicar "
                    f"insight {insight.id}: {e}"
                )
                # Continua com os próximos
                continue
        
        logger.info(
            f"[InsightExplanationService] {len(explicacoes)}/{len(insights)} "
            f"explicações geradas com sucesso"
        )
        
        return explicacoes
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Retorna estatísticas do serviço.
        
        Returns:
            Dict com estatísticas
        """
        return {
            "modo": "mock" if self.use_mock else "production",
            "ai_engine": type(self.ai_engine).__name__,
            "prompt_library": type(self.prompt_library).__name__,
        }


class InsightExplanationServiceFactory:
    """
    Factory para criação de InsightExplanationService.
    
    Facilita testes e permite trocar implementações.
    """
    
    @staticmethod
    def create_mock_service() -> InsightExplanationService:
        """
        Cria serviço com AI Engine mock.
        
        Returns:
            InsightExplanationService em modo mock
        """
        return InsightExplanationService(use_mock=True)
    
    @staticmethod
    def create_production_service() -> InsightExplanationService:
        """
        Cria serviço para produção (futuro OpenAI).
        
        Returns:
            InsightExplanationService configurado
        """
        # TODO: Quando integrar OpenAI, criar aqui
        logger.warning(
            "[InsightExplanationServiceFactory] Produção ainda usa mock. "
            "Integração com OpenAI pendente."
        )
        return InsightExplanationService(use_mock=True)
