"""Testes de contrato dos schemas de resposta de analytics."""

from datetime import date
from unittest.mock import patch


@patch("app.analytics.api.routes.queries")
def test_contrato_resumo_diario_schema(
    mock_queries, client, override_auth, override_db
):
    """
    DADO um response de /analytics/resumo-diario
    QUANDO validamos o schema
    ENTÃO todos campos obrigatórios devem estar presentes e com tipos corretos
    """
    # Arrange - Mock com dados válidos
    mock_data = {
        "id": 1,
        "data": date(2026, 2, 8),
        "quantidade_aberta": 5,
        "quantidade_finalizada": 10,
        "quantidade_cancelada": 2,
        "total_vendido": 1500.50,
        "total_cancelado": 200.00,
        "ticket_medio": 150.05,
    }
    mock_queries.obter_resumo_diario_ou_vazio.return_value = mock_data

    # Act
    response = client.get("/analytics/resumo-diario?data=2026-02-08")

    # Assert - Status
    assert response.status_code == 200

    # Assert - Schema
    data = response.json()
    assert "data" in data
    assert "quantidade_aberta" in data
    assert "quantidade_finalizada" in data
    assert "quantidade_cancelada" in data
    assert "total_vendido" in data
    assert "total_cancelado" in data
    assert "ticket_medio" in data

    # Assert - Tipos
    assert isinstance(data["data"], str), "Data deve ser string ISO 8601"
    assert isinstance(data["quantidade_aberta"], int)
    assert isinstance(data["quantidade_finalizada"], int)
    assert isinstance(data["quantidade_cancelada"], int)
    assert isinstance(data["total_vendido"], (int, float))
    assert isinstance(data["total_cancelado"], (int, float))
    assert isinstance(data["ticket_medio"], (int, float))

    # Assert - Formato ISO 8601
    assert data["data"] == "2026-02-08"

    # Assert - Valores não negativos
    assert data["quantidade_aberta"] >= 0
    assert data["quantidade_finalizada"] >= 0
    assert data["quantidade_cancelada"] >= 0
    assert data["total_vendido"] >= 0
    assert data["total_cancelado"] >= 0
    assert data["ticket_medio"] >= 0


@patch("app.analytics.api.routes.queries")
def test_contrato_resumo_periodo_schema(
    mock_queries, client, override_auth, override_db
):
    """
    DADO um response de /analytics/periodo
    QUANDO validamos o schema
    ENTÃO deve retornar lista de resumos diários com campos corretos
    """
    # Arrange - A rota retorna LISTA de resumos diários
    mock_data = [
        {
            "id": 1,
            "data": date(2026, 2, 1),
            "quantidade_aberta": 3,
            "quantidade_finalizada": 10,
            "quantidade_cancelada": 1,
            "total_vendido": 1500.00,
            "total_cancelado": 100.00,
            "ticket_medio": 150.00,
        },
        {
            "id": 2,
            "data": date(2026, 2, 2),
            "quantidade_aberta": 5,
            "quantidade_finalizada": 15,
            "quantidade_cancelada": 2,
            "total_vendido": 2000.00,
            "total_cancelado": 200.00,
            "ticket_medio": 133.33,
        },
    ]
    mock_queries.obter_resumo_periodo.return_value = mock_data

    # Act
    response = client.get(
        "/analytics/periodo?data_inicio=2026-02-01&data_fim=2026-02-08"
    )

    # Assert
    assert response.status_code == 200
    data = response.json()

    # Deve ser lista
    assert isinstance(data, list)
    assert len(data) > 0

    # Validar primeiro item
    item = data[0]
    assert "data" in item
    assert "quantidade_aberta" in item
    assert "quantidade_finalizada" in item
    assert "total_vendido" in item

    # Tipos corretos
    assert isinstance(item["data"], str)
    assert isinstance(item["quantidade_aberta"], int)
    assert isinstance(item["quantidade_finalizada"], int)
    assert isinstance(item["total_vendido"], (int, float))

    # Formato ISO 8601
    assert item["data"] == "2026-02-01"

    # Valores não negativos
    assert item["total_vendido"] >= 0
    assert item["quantidade_finalizada"] >= 0


@patch("app.analytics.api.routes.queries")
def test_contrato_ranking_parceiros_schema(
    mock_queries, client, override_auth, override_db
):
    """
    DADO um response de /analytics/ranking-parceiros
    QUANDO validamos o schema
    ENTÃO deve retornar lista de parceiros com campos corretos
    """
    # Arrange
    mock_data = [
        {
            "parceiro_id": 1,
            "parceiro_nome": "Parceiro A",
            "total_vendido": 25000.00,
            "quantidade_vendas": 50,
        },
        {
            "parceiro_id": 2,
            "parceiro_nome": "Parceiro B",
            "total_vendido": 15000.00,
            "quantidade_vendas": 30,
        },
    ]
    mock_queries.obter_ranking_parceiros.return_value = mock_data

    # Act
    response = client.get("/analytics/ranking-parceiros?limite=10")

    # Assert
    assert response.status_code == 200
    data = response.json()

    # Deve ser lista
    assert isinstance(data, list)
    assert len(data) > 0

    # Validar primeiro item
    item = data[0]
    assert "parceiro_id" in item
    assert "parceiro_nome" in item
    assert "total_vendido" in item
    assert "quantidade_vendas" in item

    # Tipos corretos
    assert isinstance(item["parceiro_id"], int)
    assert isinstance(item["parceiro_nome"], str)
    assert isinstance(item["total_vendido"], (int, float))
    assert isinstance(item["quantidade_vendas"], int)

    # Valores positivos
    assert item["parceiro_id"] > 0
    assert len(item["parceiro_nome"]) > 0
    assert item["total_vendido"] > 0
    assert item["quantidade_vendas"] > 0


@patch("app.analytics.api.routes.queries")
def test_contrato_receita_mensal_schema(
    mock_queries, client, override_auth, override_db
):
    """
    DADO um response de /analytics/receita-mensal
    QUANDO validamos o schema
    ENTÃO todos campos obrigatórios devem estar presentes
    """
    # Arrange
    mock_data = {
        "mes": date(2026, 2, 1),
        "receita_total": 50000.00,
        "quantidade_vendas": 200,
        "ticket_medio": 250.00,
    }
    mock_queries.obter_receita_mensal_ou_vazia.return_value = mock_data

    # Act
    response = client.get("/analytics/receita-mensal?mes=2026-02")

    # Assert
    assert response.status_code == 200
    data = response.json()

    # Campos obrigatórios
    assert "mes" in data
    assert "receita_total" in data
    assert "quantidade_vendas" in data
    assert "ticket_medio" in data

    # Tipos
    assert isinstance(data["mes"], str)
    assert isinstance(data["receita_total"], (int, float))
    assert isinstance(data["quantidade_vendas"], int)
    assert isinstance(data["ticket_medio"], (int, float))

    # Valores válidos
    assert data["receita_total"] >= 0
    assert data["quantidade_vendas"] >= 0
    assert data["ticket_medio"] >= 0


@patch("app.analytics.api.routes.queries")
def test_contrato_ultimos_dias_schema(mock_queries, client, override_auth, override_db):
    """
    DADO um response de /analytics/ultimos-dias
    QUANDO validamos o schema
    ENTÃO deve retornar lista de resumos diários
    """
    # Arrange
    mock_data = [
        {
            "data": date(2026, 2, 8),
            "total_vendido": 1500.00,
            "quantidade_vendas": 10,
            "ticket_medio": 150.00,
        },
        {
            "data": date(2026, 2, 7),
            "total_vendido": 2000.00,
            "quantidade_vendas": 15,
            "ticket_medio": 133.33,
        },
    ]
    mock_queries.obter_ultimos_dias.return_value = mock_data

    # Act
    response = client.get("/analytics/ultimos-dias?dias=7")

    # Assert
    assert response.status_code == 200
    data = response.json()

    assert isinstance(data, list)
    item = data[0]

    # Campos obrigatórios
    assert "data" in item
    assert "total_vendido" in item
    assert "quantidade_vendas" in item
    assert "ticket_medio" in item

    # Tipos
    assert isinstance(item["data"], str)
    assert isinstance(item["total_vendido"], (int, float))
    assert isinstance(item["quantidade_vendas"], int)
    assert isinstance(item["ticket_medio"], (int, float))

    # Formato ISO 8601
    assert item["data"] == "2026-02-08"

    # Valores não negativos
    assert item["total_vendido"] >= 0
    assert item["quantidade_vendas"] >= 0
    assert item["ticket_medio"] >= 0


@patch("app.analytics.api.routes.queries")
def test_contrato_estatisticas_gerais_schema(
    mock_queries, client, override_auth, override_db
):
    """
    DADO um response de /analytics/estatisticas-gerais
    QUANDO validamos o schema
    ENTÃO deve retornar estatísticas agregadas
    """
    # Arrange
    mock_data = {
        "mes_atual": {
            "mes": date(2026, 2, 1),
            "receita_total": 50000.00,
            "quantidade_vendas": 200,
            "ticket_medio": 250.00,
        },
        "top_5_parceiros": [
            {
                "parceiro_id": 1,
                "parceiro_nome": "Parceiro A",
                "total_vendido": 25000.00,
                "quantidade_vendas": 50,
            }
        ],
        "ultimos_7_dias": [
            {
                "data": date(2026, 2, 8),
                "total_vendido": 1500.00,
                "quantidade_vendas": 10,
                "ticket_medio": 150.00,
            }
        ],
    }
    mock_queries.obter_estatisticas_gerais.return_value = mock_data

    # Act
    response = client.get("/analytics/estatisticas-gerais")

    # Assert
    assert response.status_code == 200
    data = response.json()

    # Campos obrigatórios
    assert "mes_atual" in data
    assert "top_5_parceiros" in data
    assert "ultimos_7_dias" in data

    # Tipos
    assert isinstance(data["mes_atual"], dict)
    assert isinstance(data["top_5_parceiros"], list)
    assert isinstance(data["ultimos_7_dias"], list)

    # Validar estrutura mes_atual
    mes_atual = data["mes_atual"]
    assert "mes" in mes_atual
    assert "receita_total" in mes_atual
    assert isinstance(mes_atual["receita_total"], (int, float))
    assert mes_atual["receita_total"] >= 0


@patch("app.analytics.api.routes.queries")
def test_contrato_comparativo_receita_schema(
    mock_queries, client, override_auth, override_db
):
    """
    DADO um response de /analytics/comparativo-receita
    QUANDO validamos o schema
    ENTÃO deve retornar lista de receitas mensais com variação
    """
    # Arrange - A rota retorna LISTA de receitas mensais e usa obter_comparativo_mensal
    mock_data = [
        {
            "mes": date(2026, 2, 1),
            "receita_total": 50000.00,
            "quantidade_vendas": 200,
            "ticket_medio": 250.00,
            "variacao_percentual": 15.5,
        },
        {
            "mes": date(2026, 1, 1),
            "receita_total": 43000.00,
            "quantidade_vendas": 180,
            "ticket_medio": 238.89,
            "variacao_percentual": -5.2,
        },
    ]
    mock_queries.obter_comparativo_mensal.return_value = mock_data

    # Act - A rota usa parâmetro 'meses' não 'data_inicio/data_fim'
    response = client.get("/analytics/comparativo-receita?meses=6")

    # Assert
    assert response.status_code == 200
    data = response.json()

    # Deve ser lista
    assert isinstance(data, list)
    assert len(data) > 0

    # Validar primeiro item
    item = data[0]
    assert "mes" in item
    assert "receita_total" in item
    assert "quantidade_vendas" in item
    assert "ticket_medio" in item

    # Tipos corretos
    assert isinstance(item["mes"], str)
    assert isinstance(item["receita_total"], (int, float))
    assert isinstance(item["quantidade_vendas"], int)
    assert isinstance(item["ticket_medio"], (int, float))

    # Valores não negativos
    assert item["receita_total"] >= 0
    assert item["quantidade_vendas"] >= 0
    assert item["ticket_medio"] >= 0
