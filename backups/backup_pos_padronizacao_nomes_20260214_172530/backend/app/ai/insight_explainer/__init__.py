"""
Insight Explainer - IA Explicadora de Insights (Sprint 6, Passo 2)

Este módulo transforma Insights técnicos (Sprint 5) em explicações
compreensíveis para humanos usando o AI Engine (Passo 1).

PRINCÍPIOS:
- A IA NÃO cria insights
- A IA NÃO altera severidade
- A IA NÃO executa ações
- A IA apenas explica e sugere abordagem

COMPONENTES:
- InsightAIAdapter: Converte Insight em AIContext
- InsightExplanationService: Orquestra explicação
- Prompts específicos por tipo de insight
- Sistema auditável e multi-tenant

USO:
```python
from app.ai.insight_explainer import InsightExplanationService

service = InsightExplanationService()
explicacao = await service.explicar_insight(insight, tenant_id=1)

print(explicacao['titulo'])
print(explicacao['explicacao'])
print(explicacao['sugestao'])
```
"""

from app.ai.insight_explainer.adapter import InsightAIAdapter
from app.ai.insight_explainer.service import InsightExplanationService
from app.ai.insight_explainer.prompts import InsightPromptLibrary

__all__ = [
    "InsightAIAdapter",
    "InsightExplanationService",
    "InsightPromptLibrary",
]
