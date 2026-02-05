"""
Analytics Module - CQRS Read Side
==================================

Módulo de analytics construído sobre read models.

ESTRUTURA:
- api/        - Endpoints REST (FastAPI routers)
- queries/    - (futuro) Queries específicas de analytics se necessário

PRINCÍPIOS:
- Read-only: Nunca modifica dados
- CQRS puro: Usa apenas read models
- Performance: Dados pré-agregados
- Isolamento: Zero acesso a domínio
"""

__version__ = "1.0.0"
