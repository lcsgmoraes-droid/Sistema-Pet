"""
Módulo de Read Models
======================

Read Models são serviços de leitura que consomem eventos de domínio
e fornecem agregações e insights em tempo real.

Características:
- Trabalham APENAS com eventos em memória
- NÃO persistem dados
- NÃO modificam estado
- Retornam dados estruturados (dict/list)
- Multi-tenant (filtro por user_id)

Arquitetura Event-Driven:
- Eventos: VendaRealizadaEvent, ProdutoVendidoEvent, KitVendidoEvent
- Dispatcher: EventDispatcher (singleton em memória)
- Read Models: Serviços de leitura especializados

Read Models disponíveis:
1. ProdutosMaisVendidosReadModel
   - top_produtos(): Top N produtos mais vendidos
   - produto_detalhado(): Análise detalhada de um produto
   - produtos_por_tipo(): Filtrar por tipo (SIMPLES/VARIACAO)

2. KitsMaisVendidosReadModel
   - top_kits(): Top N kits mais vendidos
   - kit_detalhado(): Análise detalhada de um kit
   - componentes_mais_vendidos_em_kits(): Componentes mais usados
   - kits_por_tipo(): Filtrar por tipo (FISICO/VIRTUAL)

3. ProdutosCompradosJuntosReadModel
   - produtos_comprados_juntos(): Market basket analysis
   - produtos_que_aparecem_juntos(): Pares frequentes
   - analise_cesta_venda(): Sugestões para uma venda específica

4. ClientesRecorrentesReadModel
   - clientes_recorrentes(): Clientes com múltiplas compras
   - cliente_detalhado(): Análise detalhada de um cliente
   - clientes_em_risco_churn(): Clientes inativos
   - rfm_analise(): Segmentação RFM (Recency, Frequency, Monetary)

Uso:
```python
from app.read_models import (
    ProdutosMaisVendidosReadModel,
    KitsMaisVendidosReadModel,
    ProdutosCompradosJuntosReadModel,
    ClientesRecorrentesReadModel
)

# Exemplo 1: Top produtos
produtos_rm = ProdutosMaisVendidosReadModel()
top10 = produtos_rm.top_produtos(limit=10, user_id=1)

# Exemplo 2: Produtos comprados juntos
comprados_rm = ProdutosCompradosJuntosReadModel()
sugestoes = comprados_rm.produtos_comprados_juntos(
    produto_id=123,
    limit=5,
    user_id=1
)

# Exemplo 3: Clientes recorrentes
clientes_rm = ClientesRecorrentesReadModel()
recorrentes = clientes_rm.clientes_recorrentes(dias=30, user_id=1)

# Exemplo 4: Top kits
kits_rm = KitsMaisVendidosReadModel()
top_kits = kits_rm.top_kits(limit=10, tipo_kit="VIRTUAL", user_id=1)
```

Roadmap (Sprint 6 - IA):
- Integrar com IA para recomendações inteligentes
- Usar read models como fonte de dados para treinamento
- Dashboard de insights em tempo real
- Alertas proativos baseados em padrões
"""

# Read Models baseados em eventos (novos)
from .base_read_model import BaseReadModel
from .produtos_mais_vendidos import ProdutosMaisVendidosReadModel
from .kits_mais_vendidos import KitsMaisVendidosReadModel
from .produtos_comprados_juntos import ProdutosCompradosJuntosReadModel
from .clientes_recorrentes import ClientesRecorrentesReadModel

# Read Models persistidos (legado)
from .models import (
    VendasResumoDiario,
    PerformanceParceiro,
    ReceitaMensal
)

from .handlers import VendaReadModelHandler

from .queries import (
    obter_resumo_diario,
    obter_ranking_parceiros,
    obter_receita_mensal,
    obter_receita_por_periodo
)

__all__ = [
    # Read Models baseados em eventos (NOVOS - Sprint 5)
    'BaseReadModel',
    'ProdutosMaisVendidosReadModel',
    'KitsMaisVendidosReadModel',
    'ProdutosCompradosJuntosReadModel',
    'ClientesRecorrentesReadModel',
    
    # Models persistidos (LEGADO)
    "VendasResumoDiario",
    "PerformanceParceiro",
    "ReceitaMensal",
    
    # Handlers
    "VendaReadModelHandler",
    
    # Queries
    "obter_resumo_diario",
    "obter_ranking_parceiros",
    "obter_receita_mensal",
    "obter_receita_por_periodo",
]

