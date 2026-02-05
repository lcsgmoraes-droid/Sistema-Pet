"""
Testes da API de Analytics - Read Models
=========================================

Testes dos endpoints REST de consulta (read-only).

ESTRATÉGIA:
- Mock de queries de read models
- Validação de respostas
- Testes de segurança e validação
- Sem dependência de banco real

NOTA: Router agora está em app.analytics.api.routes
"""

import pytest
from fastapi.testclient import TestClient
from datetime import date, datetime
from unittest.mock import Mock, patch
from typing import Dict, Any

from app.main import app
from app.auth import get_current_user
from app.db import get_db


# ===== FIXTURES =====

@pytest.fixture
def client():
    """Cliente de teste FastAPI"""
    return TestClient(app)


@pytest.fixture
def mock_user():
    """Mock de usuário autenticado"""
    user = Mock()
    user.id = 1
    user.nome = "Usuário Teste"
    user.is_admin = True
    return user


@pytest.fixture
def override_auth(mock_user):
    """Override de autenticação para testes"""
    def override_get_current_user():
        return mock_user
    
    app.dependency_overrides[get_current_user] = override_get_current_user
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def mock_db():
    """Mock de sessão do banco"""
    return Mock()


@pytest.fixture
def override_db(mock_db):
    """Override de sessão do banco para testes"""
    def override_get_db():
        yield mock_db
    
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()


# ===== DADOS MOCK =====

def mock_resumo_diario() -> Dict[str, Any]:
    """Dados mock de resumo diário"""
    return {
        'data': '2026-01-23',
        'quantidade_aberta': 2,
        'quantidade_finalizada': 15,
        'quantidade_cancelada': 1,
        'total_vendido': 7500.00,
        'total_cancelado': 300.00,
        'ticket_medio': 500.00,
        'atualizado_em': '2026-01-23T14:30:00'
    }


def mock_receita_mensal() -> Dict[str, Any]:
    """Dados mock de receita mensal"""
    return {
        'mes_referencia': '2026-01-01',
        'receita_bruta': 85000.00,
        'receita_cancelada': 2500.00,
        'receita_liquida': 82500.00,
        'quantidade_vendas': 150,
        'quantidade_cancelamentos': 5,
        'ticket_medio': 566.67,
        'variacao_percentual': 12.5,
        'atualizado_em': '2026-01-23T14:30:00'
    }


def mock_ranking_parceiros():
    """Dados mock de ranking de parceiros"""
    return [
        {
            'posicao': 1,
            'funcionario_id': 7,
            'quantidade_vendas': 25,
            'total_vendido': 15000.00,
            'ticket_medio': 600.00,
            'taxa_cancelamento': 5.5
        },
        {
            'posicao': 2,
            'funcionario_id': 5,
            'quantidade_vendas': 22,
            'total_vendido': 13500.00,
            'ticket_medio': 613.64,
            'taxa_cancelamento': 3.2
        }
    ]


def mock_estatisticas_gerais() -> Dict[str, Any]:
    """Dados mock de estatísticas gerais"""
    return {
        'hoje': mock_resumo_diario(),
        'mes_atual': mock_receita_mensal(),
        'top_5_parceiros': mock_ranking_parceiros()[:5],
        'ultimos_7_dias': [mock_resumo_diario()],
        'atualizado_em': '2026-01-23T14:30:00Z'
    }


# ===== TESTES DE ENDPOINTS =====

@patch('app.analytics.api.routes.queries')
def test_get_resumo_diario_sucesso(
    mock_queries,
    client,
    override_auth,
    override_db
):
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
    assert data['data'] == '2026-01-23'
    assert data['quantidade_finalizada'] == 15
    assert data['total_vendido'] == 7500.00


@patch('app.analytics.api.routes.queries')
def test_get_resumo_diario_com_data_especifica(
    mock_queries,
    client,
    override_auth,
    override_db
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


@patch('app.analytics.api.routes.queries')
def test_get_resumo_diario_sem_dados(
    mock_queries,
    client,
    override_auth,
    override_db
):
    """
    DADO uma consulta de resumo diário sem dados
    QUANDO o endpoint é chamado
    ENTÃO deve retornar estrutura vazia com aviso
    """
    # Arrange
    mock_queries.obter_resumo_diario_ou_vazio.return_value = {
        "data": "2026-01-23",
        "quantidade_finalizada": 0,
        "aviso": "Nenhuma venda registrada nesta data"
    }
    
    # Act
    response = client.get("/analytics/resumo-diario")
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data['quantidade_finalizada'] == 0
    assert 'aviso' in data


@patch('app.analytics.api.routes.queries')
def test_get_receita_mensal_sucesso(
    mock_queries,
    client,
    override_auth,
    override_db
):
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
    assert data['mes_referencia'] == '2026-01-01'
    assert data['receita_liquida'] == 82500.00
    assert data['quantidade_vendas'] == 150


@patch('app.analytics.api.routes.queries')
def test_get_ranking_parceiros_sucesso(
    mock_queries,
    client,
    override_auth,
    override_db
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
    assert data[0]['posicao'] == 1
    assert data[0]['funcionario_id'] == 7


@patch('app.analytics.api.routes.queries')
def test_get_ranking_parceiros_com_limite(
    mock_queries,
    client,
    override_auth,
    override_db
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
    assert call_args.kwargs['limite'] == 5


@patch('app.analytics.api.routes.queries')
def test_get_estatisticas_gerais_sucesso(
    mock_queries,
    client,
    override_auth,
    override_db
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
    assert 'hoje' in data
    assert 'mes_atual' in data
    assert 'top_5_parceiros' in data
    assert 'ultimos_7_dias' in data


@patch('app.analytics.api.routes.queries')
def test_get_ultimos_dias_sucesso(
    mock_queries,
    client,
    override_auth,
    override_db
):
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


@patch('app.analytics.api.routes.queries')
def test_get_periodo_sucesso(
    mock_queries,
    client,
    override_auth,
    override_db
):
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


def test_get_periodo_datas_invalidas(
    client,
    override_auth,
    override_db
):
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
    assert "data_inicio deve ser anterior" in response.json()['detail']


def test_get_periodo_intervalo_muito_grande(
    client,
    override_auth,
    override_db
):
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
    assert "Intervalo máximo" in response.json()['detail']


@patch('app.analytics.api.routes.queries')
def test_get_comparativo_receita_sucesso(
    mock_queries,
    client,
    override_auth,
    override_db
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


@patch('app.analytics.api.routes.queries')
def test_get_performance_funcionario_sucesso(
    mock_queries,
    client,
    override_auth,
    override_db
):
    """
    DADO uma consulta de performance de funcionário
    QUANDO o endpoint é chamado com ID válido
    ENTÃO deve retornar métricas do funcionário
    """
    # Arrange
    mock_performance = {
        'funcionario_id': 5,
        'mes_referencia': '2026-01-01',
        'quantidade_vendas': 22,
        'total_vendido': 13500.00,
        'ticket_medio': 613.64
    }
    mock_queries.obter_performance_funcionario.return_value = mock_performance
    
    # Act
    response = client.get("/analytics/performance-funcionario/5")
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data['funcionario_id'] == 5
    assert data['quantidade_vendas'] == 22


@patch('app.analytics.api.routes.queries')
def test_get_performance_funcionario_nao_encontrado(
    mock_queries,
    client,
    override_auth,
    override_db
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


@patch('app.analytics.api.routes.queries')
def test_health_check_sucesso(
    mock_queries,
    client,
    override_db
):
    """
    DADO um health check da API
    QUANDO o endpoint é chamado
    ENTÃO deve retornar status healthy
    """
    # Arrange
    mock_queries.verificar_saude_read_models.return_value = {
        "status": "healthy",
        "timestamp": "2026-01-23T14:30:00Z"
    }
    
    # Act
    response = client.get("/analytics/health")
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'healthy'
    assert 'timestamp' in data


def test_endpoint_sem_autenticacao(client):
    """
    DADO um endpoint protegido
    QUANDO chamado sem autenticação
    ENTÃO deve retornar erro 401
    """
    # Remove override de auth se existir
    app.dependency_overrides.clear()
    
    # Act
    response = client.get("/analytics/resumo-diario")
    
    # Assert
    assert response.status_code == 401


# ===== TESTES DE VALIDAÇÃO =====

def test_ranking_limite_minimo(
    client,
    override_auth,
    override_db
):
    """
    DADO uma consulta de ranking com limite < 1
    QUANDO o endpoint é chamado
    ENTÃO deve retornar erro de validação
    """
    # Act
    response = client.get("/analytics/ranking-parceiros?limite=0")
    
    # Assert
    assert response.status_code == 422  # Validation error


def test_ranking_limite_maximo(
    client,
    override_auth,
    override_db
):
    """
    DADO uma consulta de ranking com limite > 100
    QUANDO o endpoint é chamado
    ENTÃO deve retornar erro de validação
    """
    # Act
    response = client.get("/analytics/ranking-parceiros?limite=101")
    
    # Assert
    assert response.status_code == 422


def test_ultimos_dias_quantidade_invalida(
    client,
    override_auth,
    override_db
):
    """
    DADO uma consulta de últimos dias com quantidade inválida
    QUANDO quantidade > 90
    ENTÃO deve retornar erro de validação
    """
    # Act
    response = client.get("/analytics/ultimos-dias?quantidade=91")
    
    # Assert
    assert response.status_code == 422


# ===== TESTES DE ISOLAMENTO E SIDE-EFFECTS =====

@patch('app.analytics.api.routes.queries')
def test_isolamento_user_id_nao_afeta_queries(
    mock_queries,
    client,
    override_auth,
    override_db
):
    """
    DADO múltiplos usuários diferentes
    QUANDO fazem requisições para analytics
    ENTÃO os dados retornados são os mesmos (não há filtro por user_id)
    
    NOTA: Analytics é global, não filtra por usuário.
    Este teste confirma que user_id é apenas para autenticação.
    """
    # Arrange
    mock_queries.obter_resumo_diario.return_value = mock_resumo_diario()
    
    # Act - Primeira requisição
    response1 = client.get("/analytics/resumo-diario")
    
    # Act - Segunda requisição (mesmo usuário)
    response2 = client.get("/analytics/resumo-diario")
    
    # Assert - Dados idênticos (read-only, sem isolamento por user)
    assert response1.status_code == 200
    assert response2.status_code == 200
    assert response1.json() == response2.json()
    
    # Verify queries foram chamadas mas não receberam user_id
    assert mock_queries.obter_resumo_diario.call_count == 2
    # Verifica que user_id NÃO é passado para queries
    for call in mock_queries.obter_resumo_diario.call_args_list:
        args, kwargs = call
        assert 'user_id' not in kwargs


@patch('app.analytics.api.routes.queries')
def test_idempotencia_multiplas_requisicoes(
    mock_queries,
    client,
    override_auth,
    override_db
):
    """
    DADO múltiplas requisições idênticas
    QUANDO chamadas em sequência
    ENTÃO devem retornar sempre o mesmo resultado (sem side-effects)
    """
    # Arrange
    mock_data = mock_estatisticas_gerais()
    mock_queries.obter_resumo_diario.return_value = mock_data['hoje']
    mock_queries.obter_receita_mensal.return_value = mock_data['mes_atual']
    mock_queries.obter_ranking_parceiros.return_value = mock_data['top_5_parceiros']
    mock_queries.obter_ultimos_dias.return_value = mock_data['ultimos_7_dias']
    
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
    for _ in range(3):
        response = client.get("/analytics/resumo-diario")
        assert response.status_code == 200


@patch('app.analytics.api.routes.queries')
def test_intervalo_vazio_retorna_lista_vazia_nao_erro(
    mock_queries,
    client,
    override_auth,
    override_db
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


@patch('app.analytics.api.routes.queries')
def test_periodo_vazio_retorna_estrutura_com_zeros(
    mock_queries,
    client,
    override_auth,
    override_db
):
    """
    DADO um período sem dados
    QUANDO consulta resumo de período
    ENTÃO deve retornar estrutura válida com valores zerados
    """
    # Arrange
    mock_queries.obter_resumo_periodo.return_value = None
    
    # Act
    response = client.get(
        "/analytics/periodo?data_inicio=2025-01-01&data_fim=2025-01-31"
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    # Deve ter estrutura válida mesmo sem dados
    assert 'data_inicio' in data or 'total_vendido' in data


# ===== TESTES DE INTEGRAÇÃO (OPCIONAL) =====

@pytest.mark.integration
def test_integracao_resumo_diario_real(client, override_auth):
    """
    Teste de integração com banco real.
    
    ATENÇÃO: Requer banco de dados configurado.
    Execute com: pytest -m integration
    """
    # Act
    response = client.get("/analytics/resumo-diario")
    
    # Assert
    assert response.status_code == 200
    # Pode retornar dados vazios se não houver vendas


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
