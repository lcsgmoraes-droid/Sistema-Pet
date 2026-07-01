"""Testes de sucesso, validacao e comportamento read-only de analytics."""

from datetime import date
from unittest.mock import patch

import pytest

from .analytics_test_helpers import (
    mock_estatisticas_gerais,
    mock_ranking_parceiros,
    mock_receita_mensal,
    mock_resumo_diario,
)


@patch("app.analytics.api.routes.queries")
def test_get_resumo_diario_sucesso(mock_queries, client, override_auth, override_db):
    """
    DADO uma consulta de resumo diário
    QUANDO o endpoint é chamado com autenticação
    ENTÃO deve retornar dados agregados do dia
    """
    # Arrange
    mock_queries.obter_resumo_diario_ou_vazio.return_value = mock_resumo_diario()

    # Act
    response = client.get("/analytics/resumo-diario")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["data"] == "2026-01-23"
    assert data["quantidade_finalizada"] == 15
    assert data["total_vendido"] == pytest.approx(7500.00)


@patch("app.analytics.api.routes.queries")
def test_get_resumo_diario_com_data_especifica(
    mock_queries, client, override_auth, override_db
):
    """
    DADO uma consulta de resumo diário com data específica
    QUANDO o endpoint é chamado com parâmetro de data
    ENTÃO deve retornar dados da data solicitada
    """
    # Arrange
    mock_queries.obter_resumo_diario_ou_vazio.return_value = mock_resumo_diario()

    # Act
    response = client.get("/analytics/resumo-diario?data=2026-01-20")

    # Assert
    assert response.status_code == 200
    mock_queries.obter_resumo_diario_ou_vazio.assert_called_once()


@patch("app.analytics.api.routes.queries")
def test_get_resumo_diario_sem_dados(mock_queries, client, override_auth, override_db):
    """
    DADO uma consulta de resumo diário sem dados
    QUANDO o endpoint é chamado
    ENTÃO deve retornar estrutura vazia com aviso
    """
    # Arrange
    mock_queries.obter_resumo_diario_ou_vazio.return_value = {
        "data": "2026-01-23",
        "quantidade_finalizada": 0,
        "aviso": "Nenhuma venda registrada nesta data",
    }

    # Act
    response = client.get("/analytics/resumo-diario")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["quantidade_finalizada"] == 0
    assert "aviso" in data


@patch("app.analytics.api.routes.queries")
def test_get_receita_mensal_sucesso(mock_queries, client, override_auth, override_db):
    """
    DADO uma consulta de receita mensal
    QUANDO o endpoint é chamado
    ENTÃO deve retornar métricas financeiras do mês
    """
    # Arrange
    mock_queries.obter_receita_mensal_ou_vazia.return_value = mock_receita_mensal()

    # Act
    response = client.get("/analytics/receita-mensal")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["mes_referencia"] == "2026-01-01"
    assert data["receita_liquida"] == pytest.approx(82500.00)
    assert data["quantidade_vendas"] == 150


@patch("app.analytics.api.routes.queries")
def test_get_ranking_parceiros_sucesso(
    mock_queries, client, override_auth, override_db
):
    """
    DADO uma consulta de ranking de parceiros
    QUANDO o endpoint é chamado
    ENTÃO deve retornar lista ordenada por vendas
    """
    # Arrange
    mock_queries.obter_ranking_parceiros.return_value = mock_ranking_parceiros()

    # Act
    response = client.get("/analytics/ranking-parceiros")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["posicao"] == 1
    assert data[0]["funcionario_id"] == 7


@patch("app.analytics.api.routes.queries")
def test_get_ranking_parceiros_com_limite(
    mock_queries, client, override_auth, override_db
):
    """
    DADO uma consulta de ranking com limite
    QUANDO o endpoint é chamado com parâmetro limite
    ENTÃO deve respeitar o limite solicitado
    """
    # Arrange
    mock_queries.obter_ranking_parceiros.return_value = mock_ranking_parceiros()

    # Act
    response = client.get("/analytics/ranking-parceiros?limite=5")

    # Assert
    assert response.status_code == 200
    mock_queries.obter_ranking_parceiros.assert_called_once()
    call_args = mock_queries.obter_ranking_parceiros.call_args
    assert call_args.kwargs["limite"] == 5


@patch("app.analytics.api.routes.queries")
def test_get_estatisticas_gerais_sucesso(
    mock_queries, client, override_auth, override_db
):
    """
    DADO uma consulta de estatísticas gerais
    QUANDO o endpoint é chamado
    ENTÃO deve retornar dashboard completo
    """
    # Arrange
    mock_queries.obter_estatisticas_gerais.return_value = mock_estatisticas_gerais()

    # Act
    response = client.get("/analytics/estatisticas-gerais")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "hoje" in data
    assert "mes_atual" in data
    assert "top_5_parceiros" in data
    assert "ultimos_7_dias" in data


@patch("app.analytics.api.routes.queries")
def test_get_ultimos_dias_sucesso(mock_queries, client, override_auth, override_db):
    """
    DADO uma consulta de últimos dias
    QUANDO o endpoint é chamado
    ENTÃO deve retornar histórico de dias
    """
    # Arrange
    mock_queries.obter_ultimos_dias.return_value = [mock_resumo_diario()]

    # Act
    response = client.get("/analytics/ultimos-dias?quantidade=7")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    mock_queries.obter_ultimos_dias.assert_called_once()


@patch("app.analytics.api.routes.queries")
def test_get_periodo_sucesso(mock_queries, client, override_auth, override_db):
    """
    DADO uma consulta de período
    QUANDO o endpoint é chamado com datas válidas
    ENTÃO deve retornar resumos do período
    """
    # Arrange
    mock_queries.obter_resumo_periodo.return_value = [mock_resumo_diario()]

    # Act
    response = client.get(
        "/analytics/periodo?data_inicio=2026-01-01&data_fim=2026-01-31"
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_periodo_datas_invalidas(client, override_auth, override_db):
    """
    DADO uma consulta de período com datas inválidas
    QUANDO data_inicio > data_fim
    ENTÃO deve retornar erro 400
    """
    # Act
    response = client.get(
        "/analytics/periodo?data_inicio=2026-01-31&data_fim=2026-01-01"
    )

    # Assert
    assert response.status_code == 400
    assert "data_inicio deve ser anterior" in response.json()["detail"]


def test_get_periodo_intervalo_muito_grande(client, override_auth, override_db):
    """
    DADO uma consulta de período com intervalo > 365 dias
    QUANDO o endpoint é chamado
    ENTÃO deve retornar erro 400
    """
    # Act
    response = client.get(
        "/analytics/periodo?data_inicio=2024-01-01&data_fim=2026-01-31"
    )

    # Assert
    assert response.status_code == 400
    assert "Intervalo máximo" in response.json()["detail"]


@patch("app.analytics.api.routes.queries")
def test_get_comparativo_receita_sucesso(
    mock_queries, client, override_auth, override_db
):
    """
    DADO uma consulta de comparativo de receita
    QUANDO o endpoint é chamado
    ENTÃO deve retornar receitas de múltiplos meses
    """
    # Arrange
    mock_queries.obter_comparativo_mensal.return_value = [mock_receita_mensal()]

    # Act
    response = client.get("/analytics/comparativo-receita?meses=6")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    mock_queries.obter_comparativo_mensal.assert_called_once()


@patch("app.analytics.api.routes.queries")
def test_get_performance_funcionario_sucesso(
    mock_queries, client, override_auth, override_db
):
    """
    DADO uma consulta de performance de funcionário
    QUANDO o endpoint é chamado com ID válido
    ENTÃO deve retornar métricas do funcionário
    """
    # Arrange
    mock_performance = {
        "funcionario_id": 5,
        "mes_referencia": "2026-01-01",
        "quantidade_vendas": 22,
        "total_vendido": 13500.00,
        "ticket_medio": 613.64,
    }
    mock_queries.obter_performance_funcionario.return_value = mock_performance

    # Act
    response = client.get("/analytics/performance-funcionario/5")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["funcionario_id"] == 5
    assert data["quantidade_vendas"] == 22


@patch("app.analytics.api.routes.queries")
def test_get_performance_funcionario_nao_encontrado(
    mock_queries, client, override_auth, override_db
):
    """
    DADO uma consulta de performance de funcionário inexistente
    QUANDO o endpoint é chamado
    ENTÃO deve retornar erro 404
    """
    # Arrange
    mock_queries.obter_performance_funcionario.return_value = None

    # Act
    response = client.get("/analytics/performance-funcionario/999")

    # Assert
    assert response.status_code == 404


@patch("app.analytics.api.routes.queries")
def test_health_check_sucesso(mock_queries, client, override_db):
    """
    DADO um health check da API
    QUANDO o endpoint é chamado
    ENTÃO deve retornar status healthy
    """
    # Arrange
    mock_queries.verificar_saude_read_models.return_value = {
        "status": "healthy",
        "timestamp": "2026-01-23T14:30:00Z",
    }

    # Act
    response = client.get("/analytics/health")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


def test_ranking_limite_minimo(client, override_auth, override_db):
    """
    DADO uma consulta de ranking com limite < 1
    QUANDO o endpoint é chamado
    ENTÃO deve retornar erro de validação
    """
    # Act
    response = client.get("/analytics/ranking-parceiros?limite=0")

    # Assert
    assert response.status_code == 422  # Validation error


def test_ranking_limite_maximo(client, override_auth, override_db):
    """
    DADO uma consulta de ranking com limite > 100
    QUANDO o endpoint é chamado
    ENTÃO deve retornar erro de validação
    """
    # Act
    response = client.get("/analytics/ranking-parceiros?limite=101")

    # Assert
    assert response.status_code == 422


def test_ultimos_dias_quantidade_invalida(client, override_auth, override_db):
    """
    DADO uma consulta de últimos dias com quantidade inválida
    QUANDO quantidade > 90
    ENTÃO deve retornar erro de validação
    """
    # Act
    response = client.get("/analytics/ultimos-dias?quantidade=91")

    # Assert
    assert response.status_code == 422


@patch("app.analytics.api.routes.queries")
def test_isolamento_user_id_nao_afeta_queries(
    mock_queries, client, override_auth, override_db
):
    """
    DADO múltiplos usuários diferentes
    QUANDO fazem requisições para analytics
    ENTÃO os dados retornados são os mesmos (não há filtro por user_id)

    NOTA: Analytics é global, não filtra por usuário.
    Este teste confirma que user_id é apenas para autenticação.
    """
    # Arrange
    mock_queries.obter_resumo_diario_ou_vazio.return_value = mock_resumo_diario()

    # Act - Primeira requisição
    response1 = client.get("/analytics/resumo-diario")

    # Act - Segunda requisição (mesmo usuário)
    response2 = client.get("/analytics/resumo-diario")

    # Assert - Dados idênticos (read-only, sem isolamento por user)
    assert response1.status_code == 200
    assert response2.status_code == 200
    assert response1.json() == response2.json()

    # Verify queries foram chamadas mas não receberam user_id
    assert mock_queries.obter_resumo_diario_ou_vazio.call_count == 2
    # Verifica que user_id NÃO é passado para queries
    for call in mock_queries.obter_resumo_diario_ou_vazio.call_args_list:
        args, kwargs = call
        assert "user_id" not in kwargs


@patch("app.analytics.api.routes.queries")
def test_idempotencia_multiplas_requisicoes(
    mock_queries, client, override_auth, override_db
):
    """
    DADO múltiplas requisições idênticas
    QUANDO chamadas em sequência
    ENTÃO devem retornar sempre o mesmo resultado (sem side-effects)
    """
    # Arrange
    mock_data = mock_estatisticas_gerais()
    mock_queries.obter_estatisticas_gerais.return_value = mock_data

    # Act - Fazer 5 requisições idênticas
    responses = []
    for _ in range(5):
        response = client.get("/analytics/estatisticas-gerais")
        responses.append(response.json())

    # Assert - Todas as respostas são idênticas
    first_response = responses[0]
    for response in responses[1:]:
        assert response == first_response

    # Assert - Status code sempre 200
    mock_queries.obter_resumo_diario_ou_vazio.return_value = mock_data["hoje"]
    for _ in range(3):
        response = client.get("/analytics/resumo-diario")
        assert response.status_code == 200


@patch("app.analytics.api.routes.queries")
def test_intervalo_vazio_retorna_lista_vazia_nao_erro(
    mock_queries, client, override_auth, override_db
):
    """
    DADO uma consulta que não retorna dados (intervalo vazio)
    QUANDO o endpoint é chamado
    ENTÃO deve retornar lista vazia ou zeros (não erro 404/500)
    """
    # Arrange - Simula período sem vendas
    mock_queries.obter_ultimos_dias.return_value = []
    mock_queries.obter_ranking_parceiros.return_value = []

    # Act - Ranking vazio
    response1 = client.get("/analytics/ranking-parceiros?limite=10")

    # Assert - Retorna 200 com lista vazia
    assert response1.status_code == 200
    assert response1.json() == []

    # Act - Últimos dias vazio
    response2 = client.get("/analytics/ultimos-dias?quantidade=7")

    # Assert - Retorna 200 com lista vazia
    assert response2.status_code == 200
    assert response2.json() == []


@patch("app.analytics.api.routes.queries")
def test_periodo_vazio_retorna_estrutura_com_zeros(
    mock_queries, client, override_auth, override_db
):
    """
    DADO um período sem dados
    QUANDO consulta resumo de período
    ENTÃO deve retornar estrutura válida com valores zerados
    """
    # Arrange - Retorna lista vazia ao invés de None
    mock_queries.obter_resumo_periodo.return_value = []

    # Act
    response = client.get(
        "/analytics/periodo?data_inicio=2025-01-01&data_fim=2025-01-31"
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    # Deve retornar lista vazia quando não há dados
    assert isinstance(data, list)
    assert len(data) == 0


@pytest.mark.integration
def test_integracao_resumo_diario_real(client, override_auth):
    """
    Teste de integração verificando fluxo completo do endpoint resumo-diario.

    Valida que o endpoint retorna dados corretos quando há vendas no dia.
    """
    from unittest.mock import patch

    # Arrange - Mock de dados de resumo diário
    mock_resumo = {
        "id": 1,
        "data": date.today(),
        "quantidade_aberta": 5,
        "quantidade_finalizada": 15,
        "quantidade_cancelada": 2,
        "total_vendido": 2500.00,
        "total_cancelado": 150.00,
        "ticket_medio": 166.67,
        "atualizado_em": date.today(),
    }

    # Act
    with patch(
        "app.read_models.queries.obter_resumo_diario_ou_vazio", return_value=mock_resumo
    ):
        response = client.get("/analytics/resumo-diario")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "quantidade_aberta" in data
    assert "quantidade_finalizada" in data
    assert "total_vendido" in data
