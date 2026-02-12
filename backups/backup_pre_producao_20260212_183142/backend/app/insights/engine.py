"""
Insight Engine - Motor de Geração de Insights
==============================================

Engine central que coordena a geração de insights automáticos.

Responsabilidades:
- Instanciar Read Models
- Executar regras de insights
- Consolidar resultados
- Filtrar/ordenar insights
- Fornecer API simples para consumo

Características:
- NÃO persiste insights (podem ser persistidos externamente)
- NÃO usa IA (regras determinísticas)
- Multi-tenant (user_id obrigatório)
- Extensível (fácil adicionar novas regras)

Uso:
```python
from app.insights import InsightEngine

engine = InsightEngine()

# Gerar todos os insights para um tenant
insights = engine.gerar_insights(user_id=1)

# Gerar insights específicos
insights_clientes = engine.gerar_insights_clientes(user_id=1)
insights_produtos = engine.gerar_insights_produtos(user_id=1, produto_id=123)
```
"""

from typing import List, Optional, Dict, Any
import logging

from app.read_models import (
    ProdutosMaisVendidosReadModel,
    KitsMaisVendidosReadModel,
    ProdutosCompradosJuntosReadModel,
    ClientesRecorrentesReadModel
)

from .models import Insight, SeveridadeInsight, TipoInsight
from .rules import (
    regra_cliente_recorrente_atrasado,
    regra_cliente_inativo,
    regra_produtos_comprados_juntos,
    regra_kit_mais_vantajoso
)

logger = logging.getLogger(__name__)


class InsightEngine:
    """
    Motor de geração de insights automáticos.
    
    Coordena a execução de regras de insights usando dados
    dos Read Models.
    
    Attributes:
        produtos_rm: Read Model de produtos
        kits_rm: Read Model de kits
        comprados_rm: Read Model de produtos comprados juntos
        clientes_rm: Read Model de clientes
    
    Exemplo:
    ```python
    engine = InsightEngine()
    
    # Gerar todos os insights
    todos = engine.gerar_insights(user_id=1)
    
    # Filtrar por severidade
    oportunidades = engine.filtrar_por_severidade(
        todos, 
        SeveridadeInsight.OPORTUNIDADE
    )
    ```
    """
    
    def __init__(self):
        """Inicializa o engine com os Read Models."""
        self.produtos_rm = ProdutosMaisVendidosReadModel()
        self.kits_rm = KitsMaisVendidosReadModel()
        self.comprados_rm = ProdutosCompradosJuntosReadModel()
        self.clientes_rm = ClientesRecorrentesReadModel()
        
        logger.info("💡 InsightEngine inicializado")
    
    # ========================================================================
    # MÉTODOS PRINCIPAIS - Geração de Insights
    # ========================================================================
    
    def gerar_insights(
        self,
        user_id: int,
        incluir_clientes: bool = True,
        incluir_produtos: bool = True,
        incluir_kits: bool = True
    ) -> List[Insight]:
        """
        Gera todos os insights disponíveis para um tenant.
        
        Executa todas as regras de insights e consolida resultados.
        
        Args:
            user_id: Tenant
            incluir_clientes: Gerar insights de clientes
            incluir_produtos: Gerar insights de produtos
            incluir_kits: Gerar insights de kits
            
        Returns:
            Lista consolidada de insights
        """
        logger.info(f"📊 Gerando insights para user_id={user_id}")
        
        todos_insights = []
        
        # Insights de clientes
        if incluir_clientes:
            insights_clientes = self.gerar_insights_clientes(user_id)
            todos_insights.extend(insights_clientes)
            logger.debug(f"  - {len(insights_clientes)} insights de clientes")
        
        # Insights de produtos (cross-sell)
        if incluir_produtos:
            insights_produtos = self.gerar_insights_produtos_geral(user_id)
            todos_insights.extend(insights_produtos)
            logger.debug(f"  - {len(insights_produtos)} insights de produtos")
        
        # Insights de kits
        if incluir_kits:
            insights_kits = self.gerar_insights_kits(user_id)
            todos_insights.extend(insights_kits)
            logger.debug(f"  - {len(insights_kits)} insights de kits")
        
        logger.info(f"✅ Total: {len(todos_insights)} insights gerados")
        
        return todos_insights
    
    def gerar_insights_clientes(self, user_id: int) -> List[Insight]:
        """
        Gera insights relacionados a clientes.
        
        Regras executadas:
        - Cliente recorrente atrasado
        - Cliente inativo (risco de churn)
        
        Args:
            user_id: Tenant
            
        Returns:
            Lista de insights de clientes
        """
        insights = []
        
        # Regra 1: Clientes atrasados
        try:
            insights_atrasados = regra_cliente_recorrente_atrasado(
                self.clientes_rm,
                user_id=user_id
            )
            insights.extend(insights_atrasados)
        except Exception as e:
            logger.error(f"Erro ao gerar insights de clientes atrasados: {e}")
        
        # Regra 2: Clientes inativos
        try:
            insights_inativos = regra_cliente_inativo(
                self.clientes_rm,
                user_id=user_id
            )
            insights.extend(insights_inativos)
        except Exception as e:
            logger.error(f"Erro ao gerar insights de clientes inativos: {e}")
        
        return insights
    
    def gerar_insights_produtos(
        self,
        user_id: int,
        produto_id: int,
        min_confianca: float = 50.0
    ) -> List[Insight]:
        """
        Gera insights de cross-sell para um produto específico.
        
        Args:
            user_id: Tenant
            produto_id: Produto de referência
            min_confianca: Confiança mínima para sugestões
            
        Returns:
            Lista de insights de cross-sell
        """
        try:
            insights = regra_produtos_comprados_juntos(
                self.comprados_rm,
                user_id=user_id,
                produto_id=produto_id,
                min_confianca=min_confianca
            )
            return insights
        except Exception as e:
            logger.error(f"Erro ao gerar insights de produtos: {e}")
            return []
    
    def gerar_insights_produtos_geral(
        self,
        user_id: int,
        limit_produtos: int = 5
    ) -> List[Insight]:
        """
        Gera insights de cross-sell para os top produtos.
        
        Útil para dashboard geral de insights.
        
        Args:
            user_id: Tenant
            limit_produtos: Quantos produtos analisar
            
        Returns:
            Lista de insights de cross-sell
        """
        insights = []
        
        # Buscar top produtos
        top_produtos = self.produtos_rm.top_produtos(
            limit=limit_produtos,
            user_id=user_id
        )
        
        # Gerar insights para cada produto
        for produto in top_produtos:
            produto_id = produto['produto_id']
            insights_produto = self.gerar_insights_produtos(
                user_id=user_id,
                produto_id=produto_id,
                min_confianca=60.0  # Mais restritivo para geral
            )
            insights.extend(insights_produto)
        
        return insights
    
    def gerar_insights_kits(self, user_id: int) -> List[Insight]:
        """
        Gera insights relacionados a kits.
        
        Regras executadas:
        - Kit mais vantajoso que itens separados
        
        Args:
            user_id: Tenant
            
        Returns:
            Lista de insights de kits
        """
        try:
            insights = regra_kit_mais_vantajoso(
                self.kits_rm,
                self.produtos_rm,
                user_id=user_id
            )
            return insights
        except Exception as e:
            logger.error(f"Erro ao gerar insights de kits: {e}")
            return []
    
    # ========================================================================
    # MÉTODOS AUXILIARES - Filtragem e Ordenação
    # ========================================================================
    
    def filtrar_por_severidade(
        self,
        insights: List[Insight],
        severidade: SeveridadeInsight
    ) -> List[Insight]:
        """
        Filtra insights por severidade.
        
        Args:
            insights: Lista de insights
            severidade: Severidade desejada
            
        Returns:
            Insights filtrados
        """
        return [i for i in insights if i.severidade == severidade]
    
    def filtrar_por_tipo(
        self,
        insights: List[Insight],
        tipo: TipoInsight
    ) -> List[Insight]:
        """
        Filtra insights por tipo.
        
        Args:
            insights: Lista de insights
            tipo: Tipo desejado
            
        Returns:
            Insights filtrados
        """
        return [i for i in insights if i.tipo == tipo]
    
    def ordenar_por_severidade(
        self,
        insights: List[Insight],
        ordem_prioridade: Optional[List[SeveridadeInsight]] = None
    ) -> List[Insight]:
        """
        Ordena insights por severidade (prioridade).
        
        Args:
            insights: Lista de insights
            ordem_prioridade: Ordem customizada (opcional)
            
        Returns:
            Insights ordenados
        """
        if ordem_prioridade is None:
            # Ordem padrão: ATENÇÃO > OPORTUNIDADE > INFO
            ordem_prioridade = [
                SeveridadeInsight.ATENCAO,
                SeveridadeInsight.OPORTUNIDADE,
                SeveridadeInsight.INFO
            ]
        
        def get_priority(insight: Insight) -> int:
            try:
                return ordem_prioridade.index(insight.severidade)
            except ValueError:
                return 999  # Último se não estiver na lista
        
        return sorted(insights, key=get_priority)
    
    def agrupar_por_entidade(
        self,
        insights: List[Insight]
    ) -> Dict[str, List[Insight]]:
        """
        Agrupa insights por tipo de entidade.
        
        Args:
            insights: Lista de insights
            
        Returns:
            Dict {entidade: [insights]}
        """
        grupos = {}
        
        for insight in insights:
            entidade = insight.entidade.value
            if entidade not in grupos:
                grupos[entidade] = []
            grupos[entidade].append(insight)
        
        return grupos
    
    def estatisticas(self, insights: List[Insight]) -> Dict[str, Any]:
        """
        Gera estatísticas sobre os insights.
        
        Args:
            insights: Lista de insights
            
        Returns:
            Dict com estatísticas
        """
        if not insights:
            return {
                'total': 0,
                'por_severidade': {},
                'por_tipo': {},
                'por_entidade': {}
            }
        
        stats = {
            'total': len(insights),
            'por_severidade': {},
            'por_tipo': {},
            'por_entidade': {}
        }
        
        # Contar por severidade
        for insight in insights:
            sev = insight.severidade.value
            stats['por_severidade'][sev] = stats['por_severidade'].get(sev, 0) + 1
        
        # Contar por tipo
        for insight in insights:
            tipo = insight.tipo.value
            stats['por_tipo'][tipo] = stats['por_tipo'].get(tipo, 0) + 1
        
        # Contar por entidade
        for insight in insights:
            ent = insight.entidade.value
            stats['por_entidade'][ent] = stats['por_entidade'].get(ent, 0) + 1
        
        return stats
    
    # ========================================================================
    # MÉTODOS UTILITÁRIOS - Exportação
    # ========================================================================
    
    def insights_para_dict(self, insights: List[Insight]) -> List[Dict[str, Any]]:
        """
        Converte lista de insights para lista de dicts.
        
        Args:
            insights: Lista de insights
            
        Returns:
            Lista de dicts
        """
        return [i.to_dict() for i in insights]
    
    def resumo_executivo(
        self,
        insights: List[Insight],
        top_n: int = 5
    ) -> Dict[str, Any]:
        """
        Gera resumo executivo dos insights.
        
        Útil para dashboards e relatórios.
        
        Args:
            insights: Lista de insights
            top_n: Quantos insights destacar
            
        Returns:
            Dict com resumo
        """
        stats = self.estatisticas(insights)
        ordenados = self.ordenar_por_severidade(insights)
        
        return {
            'total_insights': len(insights),
            'estatisticas': stats,
            'top_insights': [i.to_dict() for i in ordenados[:top_n]],
            'resumo_por_severidade': {
                'atencao': stats['por_severidade'].get('ATENCAO', 0),
                'oportunidade': stats['por_severidade'].get('OPORTUNIDADE', 0),
                'info': stats['por_severidade'].get('INFO', 0)
            }
        }
