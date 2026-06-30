"""Dados mock compartilhados dos testes da API de analytics."""

from itertools import islice
from typing import Any, Dict


def mock_resumo_diario() -> Dict[str, Any]:
    """Dados mock de resumo diário"""
    return {
        "data": "2026-01-23",
        "quantidade_aberta": 2,
        "quantidade_finalizada": 15,
        "quantidade_cancelada": 1,
        "total_vendido": 7500.00,
        "total_cancelado": 300.00,
        "ticket_medio": 500.00,
        "atualizado_em": "2026-01-23T14:30:00",
    }


def mock_receita_mensal() -> Dict[str, Any]:
    """Dados mock de receita mensal"""
    return {
        "mes_referencia": "2026-01-01",
        "receita_bruta": 85000.00,
        "receita_cancelada": 2500.00,
        "receita_liquida": 82500.00,
        "quantidade_vendas": 150,
        "quantidade_cancelamentos": 5,
        "ticket_medio": 566.67,
        "variacao_percentual": 12.5,
        "atualizado_em": "2026-01-23T14:30:00",
    }


def mock_ranking_parceiros():
    """Dados mock de ranking de parceiros"""
    return [
        {
            "posicao": 1,
            "funcionario_id": 7,
            "quantidade_vendas": 25,
            "total_vendido": 15000.00,
            "ticket_medio": 600.00,
            "taxa_cancelamento": 5.5,
        },
        {
            "posicao": 2,
            "funcionario_id": 5,
            "quantidade_vendas": 22,
            "total_vendido": 13500.00,
            "ticket_medio": 613.64,
            "taxa_cancelamento": 3.2,
        },
    ]


def mock_estatisticas_gerais() -> Dict[str, Any]:
    """Dados mock de estatísticas gerais"""
    return {
        "hoje": mock_resumo_diario(),
        "mes_atual": mock_receita_mensal(),
        "top_5_parceiros": list(islice(mock_ranking_parceiros(), 5)),
        "ultimos_7_dias": [mock_resumo_diario()],
        "atualizado_em": "2026-01-23T14:30:00Z",
    }
