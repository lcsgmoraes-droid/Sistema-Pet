# ⚠️  ROTAS DESATIVADAS — MÉTRICAS INTERNAS APENAS
# 
# As rotas de métricas de oportunidades foram desativadas e não estão expostas
# publicamente via API. O serviço de métricas (opportunity_metrics_service.py)
# permanece disponível para uso interno e por processos em background.
#
# ⏳ Ativar somente em PHASE 5 quando o roadmap de IA chegar à otimização completa.
#
# Código comentado preservado para fácil reativação.
#
# ============================================================================

"""
# [DESATIVADO - PRESERVADO PARA REFERÊNCIA]
#
# Rotas de API para métricas de oportunidades.
#
# Endpoints para expor dados de analytics das oportunidades, permitindo:
# - Monitoramento de performance de recomendações
# - Análise de comportamento do operador
# - Suporte a futura integração com IA (treino e refinamento)
#
# IMPORTANTE: Todas as rotas filtram automaticamente por tenant_id da requisição,
# garantindo isolamento multi-tenant seguro.
"""

# from fastapi import APIRouter, Depends, HTTPException, status
# from sqlalchemy.orm import Session
# from typing import Dict, List, Any
# 
# from app.database import get_db
# from app.services.opportunity_metrics_service import (
#     count_events_by_type,
#     conversion_rate_by_type,
#     top_products_converted,
#     top_products_ignored,
#     operator_event_summary,
#     get_metrics_dashboard_summary,
# )
# from app.auth import get_current_user
# from app.models import User
# 
# router = APIRouter(
#     prefix="/api/opportunities/metrics",
#     tags=["opportunity-metrics"],
#     dependencies=[Depends(get_current_user)],
# )
# 
# 
# @router.get("/events/by-type")
# async def get_events_by_type(
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user),
# ) -> Dict[str, int]:
#     """
#     Retorna contagem de eventos por tipo.
#     
#     **Tipos de evento:**
#     - `convertida`: Operador adicionou oportunidade ao pedido
#     - `refinada`: Operador clicou "Alternativa" (alternativa sugerida)
#     - `rejeitada`: Operador clicou "Ignorar"
#     
#     **Exemplo de resposta:**
#     ```json
#     {
#         "convertida": 156,
#         "refinada": 89,
#         "rejeitada": 234
#     }
#     ```
#     
#     **Isolamento:** Filtrado automaticamente por tenant_id do usuário
#     """
#     try:
#         metrics = count_events_by_type(db, current_user.tenant_id)
#         return metrics
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Erro ao buscar eventos por tipo: {str(e)}",
#         )
# 
# 
# @router.get("/conversion-rate")
# async def get_conversion_rate(
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user),
# ) -> Dict[str, float]:
#     """
#     Retorna taxa de conversão geral e por tipo.
#     
#     **Cálculo:**
#     - Taxa geral = (eventos "convertida") / (total de eventos) * 100
#     - Mostra também taxa de "refinada" (alternativa sugerida)
#     
#     **Exemplo de resposta:**
#     ```json
#     {
#         "overall_conversion_rate": 35.2,
#         "convertida_rate": 35.2,
#         "refinada_rate": 25.1,
#         "rejeitada_rate": 39.7,
#         "total_events": 479
#     }
#     ```
#     
#     **Uso:** Monitorar efetividade do sistema de recomendações
#     """
#     try:
#         metrics = conversion_rate_by_type(db, current_user.tenant_id)
#         return metrics
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Erro ao calcular taxa de conversão: {str(e)}",
#         )
# 
# 
# @router.get("/top-products/converted")
# async def get_top_converted_products(
#     limit: int = 10,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user),
# ) -> List[Dict[str, Any]]:
#     """
#     Retorna top N produtos mais frequentemente aceitos em oportunidades.
#     
#     **Parâmetros:**
#     - `limit`: Número máximo de produtos (default: 10)
#     
#     **Exemplo de resposta:**
#     ```json
#     [
#         {
#             "produto_id": "550e8400-e29b-41d4-a716-446655440000",
#             "product_name": "Ração Premium 15kg",
#             "conversion_count": 89,
#             "last_converted": "2025-01-27T10:30:00"
#         },
#         {
#             "produto_id": "550e8400-e29b-41d4-a716-446655440001",
#             "product_name": "Coleira Anti-Pulga",
#             "conversion_count": 76,
#             "last_converted": "2025-01-27T09:15:00"
#         }
#     ]
#     ```
#     
#     **Uso:** Identificar quais produtos geram mais interesse/confiança dos clientes
#     """
#     if limit < 1 or limit > 100:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Limit deve estar entre 1 e 100",
#         )
#     
#     try:
#         products = top_products_converted(db, current_user.tenant_id, limit)
#         return products
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Erro ao buscar produtos convertidos: {str(e)}",
#         )
# 
# 
# @router.get("/top-products/ignored")
# async def get_top_ignored_products(
#     limit: int = 10,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user),
# ) -> List[Dict[str, Any]]:
#     """
#     Retorna top N produtos mais frequentemente rejeitados/ignorados.
#     
#     **Parâmetros:**
#     - `limit`: Número máximo de produtos (default: 10)
#     
#     **Exemplo de resposta:**
#     ```json
#     [
#         {
#             "produto_id": "550e8400-e29b-41d4-a716-446655440002",
#             "product_name": "Brinquedo de Corda",
#             "rejection_count": 45,
#             "last_rejected": "2025-01-27T11:00:00"
#         }
#     ]
#     ```
#     
#     **Uso:** Identificar produtos com baixa aceitação para revisão de algoritmo
#     """
#     if limit < 1 or limit > 100:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Limit deve estar entre 1 e 100",
#         )
#     
#     try:
#         products = top_products_ignored(db, current_user.tenant_id, limit)
#         return products
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Erro ao buscar produtos ignorados: {str(e)}",
#         )
# 
# 
# @router.get("/operators/summary")
# async def get_operators_summary(
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user),
# ) -> List[Dict[str, Any]]:
#     """
#     Retorna sumário de performance de cada operador (caixa/atendente).
#     
#     **Exemplo de resposta:**
#     ```json
#     [
#         {
#             "user_id": "550e8400-e29b-41d4-a716-446655440003",
#             "operator_name": "João Silva",
#             "total_events": 125,
#             "total_converted": 45,
#             "total_refined": 35,
#             "total_ignored": 45,
#             "conversion_rate": 36.0,
#             "last_event": "2025-01-27T14:30:00"
#         },
#         {
#             "user_id": "550e8400-e29b-41d4-a716-446655440004",
#             "operator_name": "Maria Santos",
#             "total_events": 89,
#             "total_converted": 32,
#             "total_refined": 24,
#             "total_ignored": 33,
#             "conversion_rate": 35.96,
#             "last_event": "2025-01-27T13:45:00"
#         }
#     ]
#     ```
#     
#     **Uso:** 
#     - Monitorar tendências individuais de cada operador
#     - Identificar operadores com taxas altas/baixas para treinamento
#     - Avaliar consistência da aceitação entre equipes
#     """
#     try:
#         summary = operator_event_summary(db, current_user.tenant_id)
#         return summary
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Erro ao buscar sumário de operadores: {str(e)}",
#         )
# 
# 
# @router.get("/dashboard/summary")
# async def get_dashboard_summary(
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user),
# ) -> Dict[str, Any]:
#     """
#     Retorna consolidação de todas as métricas para dashboard executivo.
#     
#     **Exemplo de resposta:**
#     ```json
#     {
#         "summary": {
#             "total_events": 479,
#             "total_converted": 169,
#             "total_refined": 120,
#             "total_ignored": 190,
#             "overall_conversion_rate": 35.28
#         },
#         "top_converted_products": [
#             {
#                 "produto_id": "...",
#                 "product_name": "Ração Premium 15kg",
#                 "conversion_count": 89,
#                 "last_converted": "2025-01-27T10:30:00"
#             }
#         ],
#         "top_ignored_products": [
#             {
#                 "produto_id": "...",
#                 "product_name": "Brinquedo de Corda",
#                 "rejection_count": 45,
#                 "last_rejected": "2025-01-27T11:00:00"
#             }
#         ],
#         "operator_performance": [
#             {
#                 "user_id": "...",
#                 "operator_name": "João Silva",
#                 "total_events": 125,
#                 "conversion_rate": 36.0
#             }
#         ]
#     }
#     ```
#     
#     **Uso:** Exibição em painel único com overview de toda a performance
#     """
#     try:
#         summary = get_metrics_dashboard_summary(db, current_user.tenant_id)
#         return summary
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Erro ao buscar sumário do dashboard: {str(e)}",
#         )
"""
