"""
Módulo de Insights Automáticos
===============================

Sistema de geração automática de insights baseado em eventos de domínio
e análise de dados via Read Models.

Características:
- Insights gerados por regras determinísticas (NÃO usa IA)
- Baseado em Read Models (eventos em memória)
- Multi-tenant (user_id obrigatório)
- Extensível (fácil adicionar novas regras)
- NÃO persiste dados (pode ser integrado externamente)

Componentes:
1. Models: Estruturas de dados (Insight, enums)
2. Rules: Regras de geração de insights
3. Engine: Coordenador central (InsightEngine)

Insights Disponíveis:
- CLIENTE_RECORRENTE_ATRASADO: Cliente regular atrasou compra esperada
- CLIENTE_INATIVO: Cliente em risco de churn
- PRODUTOS_COMPRADOS_JUNTOS: Oportunidade de cross-sell
- KIT_MAIS_VANTAJOSO: Kit oferece melhor valor que itens separados

Severidades:
- INFO: Informação geral, sem urgência
- ATENCAO: Requer atenção, possível problema
- OPORTUNIDADE: Chance de aumentar vendas/receita

Uso:
```python
from app.insights import InsightEngine, SeveridadeInsight

# Instanciar engine
engine = InsightEngine()

# Gerar todos os insights
insights = engine.gerar_insights(user_id=1)

# Filtrar por severidade
oportunidades = engine.filtrar_por_severidade(
    insights, 
    SeveridadeInsight.OPORTUNIDADE
)

# Estatísticas
stats = engine.estatisticas(insights)
logger.info(f"Total: {stats['total']} insights")

# Resumo executivo
resumo = engine.resumo_executivo(insights)
```

Integração com IA (Sprint 6):
```python
# Gerar insights automáticos
insights = engine.gerar_insights(user_id=1)

# Enviar para IA para enriquecimento
for insight in insights:
    prompt = f'''
    Insight: {insight.titulo}
    Descrição: {insight.descricao}
    Contexto: {insight.dados_contexto}
    
    Gere recomendações personalizadas e mensagens para o cliente.
    '''
    
    ia_resposta = await ai_service.enrich_insight(prompt)
```

Roadmap:
- Sprint 5 (atual): Insights determinísticos
- Sprint 6: Enriquecimento com IA
- Sprint 7: Alertas automáticos (WhatsApp/Email)
- Sprint 8: Persistência e histórico de insights
"""

from .models import (
    Insight,
    TipoInsight,
    SeveridadeInsight,
    EntidadeInsight
)

from .engine import InsightEngine

from app.utils.logger import logger
from .rules import (
    regra_cliente_recorrente_atrasado,
    regra_cliente_inativo,
    regra_produtos_comprados_juntos,
    regra_kit_mais_vantajoso,
    gerar_id_insight
)

__all__ = [
    # Models
    'Insight',
    'TipoInsight',
    'SeveridadeInsight',
    'EntidadeInsight',
    
    # Engine
    'InsightEngine',
    
    # Rules (para uso avançado)
    'regra_cliente_recorrente_atrasado',
    'regra_cliente_inativo',
    'regra_produtos_comprados_juntos',
    'regra_kit_mais_vantajoso',
    'gerar_id_insight',
]
