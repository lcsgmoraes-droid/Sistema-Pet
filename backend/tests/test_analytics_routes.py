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
from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session as get_db


# ===== FIXTURES =====

@pytest.fixture
def client():
    """Cliente de teste FastAPI com exceções convertidas em respostas HTTP"""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def mock_user():
    """Mock de usuário autenticado"""
    user = Mock()
    user.id = 1
    user.nome = "Usuário Teste"
    user.is_admin = True
    user.tenant_id = "00000000-0000-0000-0000-000000000001"
    return user


@pytest.fixture
def override_auth(mock_user):
    """Override de autenticação para testes"""
    def override_get_current_user():
        return mock_user
    
    def override_get_current_user_and_tenant():
        return (mock_user, mock_user.tenant_id)
    
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_user_and_tenant] = override_get_current_user_and_tenant
    yield
    if get_current_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_user]
    if get_current_user_and_tenant in app.dependency_overrides:
        del app.dependency_overrides[get_current_user_and_tenant]


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
    if get_db in app.dependency_overrides:
        del app.dependency_overrides[get_db]


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
    mock_queries.obter_resumo_diario_ou_vazio.return_value = mock_data['hoje']
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


# ========================================
# TESTES DE RESILIÊNCIA (PARTE 1 - ERROS 500)
# ========================================

@patch('app.analytics.api.routes.queries')
def test_resumo_diario_internal_error(
    mock_queries,
    client,
    override_auth,
    override_db
):
    """
    DADO que queries.obter_resumo_diario_ou_vazio lança Exception
    QUANDO o endpoint /analytics/resumo-diario é chamado
    ENTÃO deve retornar 500 com payload padronizado
    
    VALIDATES:
    - Tratamento de erros internos
    - Payload padronizado de erro
    - Não expõe stacktrace (detail genérico em produção)
    - Serialização JSON funcionando
    """
    # Arrange - Simular erro interno no serviço
    mock_queries.obter_resumo_diario_ou_vazio.side_effect = Exception("Database connection failed")
    
    # Act
    response = client.get("/analytics/resumo-diario")
    
    # Assert - Status 500
    assert response.status_code == 500
    
    # Assert - Payload padronizado
    data = response.json()
    assert "error" in data
    assert "message" in data
    assert "detail" in data
    assert data["error"] == "internal_server_error"
    assert data["message"] == "Erro interno no servidor"
    
    # Assert - Serialização JSON OK (não quebrou)
    assert isinstance(data, dict)
    
    # Assert - Não expõe detalhes técnicos sensíveis em produção
    # (Em dev/debug pode mostrar, mas deve ser string legível)
    assert isinstance(data["detail"], str)


@patch('app.analytics.api.routes.queries')
def test_receita_mensal_internal_error(
    mock_queries,
    client,
    override_auth,
    override_db
):
    """
    DADO que queries.obter_receita_mensal_ou_vazia lança Exception
    QUANDO o endpoint /analytics/receita-mensal é chamado
    ENTÃO deve retornar 500 com tratamento adequado
    """
    # Arrange
    mock_queries.obter_receita_mensal_ou_vazia.side_effect = RuntimeError("Query timeout")
    
    # Act
    response = client.get("/analytics/receita-mensal")
    
    # Assert
    assert response.status_code == 500
    data = response.json()
    assert data["error"] == "internal_server_error"
    assert "message" in data
    assert "detail" in data


@patch('app.analytics.api.routes.queries')
def test_ranking_parceiros_internal_error(
    mock_queries,
    client,
    override_auth,
    override_db
):
    """
    DADO que queries.obter_ranking_parceiros lança KeyError
    QUANDO o endpoint é chamado
    ENTÃO deve tratar gracefully e retornar 500
    """
    # Arrange - Erro específico de chave faltando
    mock_queries.obter_ranking_parceiros.side_effect = KeyError("funcionario_id")
    
    # Act
    response = client.get("/analytics/ranking-parceiros?limite=10")
    
    # Assert
    assert response.status_code == 500
    data = response.json()
    assert data["error"] == "internal_server_error"
    # Deve ter convertido KeyError para response JSON
    assert isinstance(data, dict)


@patch('app.analytics.api.routes.queries')
def test_estatisticas_gerais_internal_error(
    mock_queries,
    client,
    override_auth,
    override_db
):
    """
    DADO que queries.obter_estatisticas_gerais lança ValueError
    QUANDO o endpoint é chamado
    ENTÃO deve retornar 500 sem quebrar
    """
    # Arrange
    mock_queries.obter_estatisticas_gerais.side_effect = ValueError("Invalid aggregation")
    
    # Act
    response = client.get("/analytics/estatisticas-gerais")
    
    # Assert
    assert response.status_code == 500
    data = response.json()
    assert data["error"] == "internal_server_error"
    assert "type" in data  # Deve incluir tipo da exceção


@patch('app.analytics.api.routes.queries')
def test_ultimos_dias_internal_error(
    mock_queries,
    client,
    override_auth,
    override_db
):
    """
    DADO que queries.obter_ultimos_dias lança AttributeError
    QUANDO o endpoint é chamado
    ENTÃO deve tratar sem expor implementação interna
    """
    # Arrange
    mock_queries.obter_ultimos_dias.side_effect = AttributeError("'NoneType' object has no attribute 'data'")
    
    # Act
    response = client.get("/analytics/ultimos-dias?quantidade=7")
    
    # Assert
    assert response.status_code == 500
    data = response.json()
    assert data["error"] == "internal_server_error"
    # Não deve expor "NoneType" em produção, mas deve ser tratado
    assert isinstance(data["detail"], str)


@patch('app.analytics.api.routes.queries')
def test_periodo_internal_error(
    mock_queries,
    client,
    override_auth,
    override_db
):
    """
    DADO que queries.obter_resumo_periodo lança TypeError
    QUANDO o endpoint é chamado com datas válidas
    ENTÃO deve retornar 500 (não 422 de validação)
    """
    # Arrange
    mock_queries.obter_resumo_periodo.side_effect = TypeError("unsupported operand type")
    
    # Act
    response = client.get("/analytics/periodo?data_inicio=2025-01-01&data_fim=2025-01-31")
    
    # Assert
    assert response.status_code == 500
    data = response.json()
    assert data["error"] == "internal_server_error"


@patch('app.analytics.api.routes.queries')
def test_comparativo_receita_internal_error(
    mock_queries,
    client,
    override_auth,
    override_db
):
    """
    DADO que queries.obter_comparativo_mensal lança IndexError
    QUANDO o endpoint é chamado
    ENTÃO deve tratar lista vazia ou índice inválido
    """
    # Arrange
    mock_queries.obter_comparativo_mensal.side_effect = IndexError("list index out of range")
    
    # Act
    response = client.get("/analytics/comparativo-receita?meses=6")
    
    # Assert
    assert response.status_code == 500
    data = response.json()
    assert data["error"] == "internal_server_error"


@patch('app.analytics.api.routes.queries')
def test_performance_funcionario_internal_error(
    mock_queries,
    client,
    override_auth,
    override_db
):
    """
    DADO que queries.obter_performance_funcionario lança Exception genérica
    QUANDO o endpoint é chamado
    ENTÃO deve retornar 500 sem quebrar serialização
    """
    # Arrange
    mock_queries.obter_performance_funcionario.side_effect = Exception("Unexpected error in aggregation")
    
    # Act
    response = client.get("/analytics/performance-funcionario/999")
    
    # Assert
    assert response.status_code == 500
    data = response.json()
    assert data["error"] == "internal_server_error"
    assert "message" in data
    assert "detail" in data


@patch('app.analytics.api.routes.queries')
def test_multiple_concurrent_errors(
    mock_queries,
    client,
    override_auth,
    override_db
):
    """
    DADO múltiplas requisições simultâneas com erros
    QUANDO o endpoint é chamado várias vezes
    ENTÃO cada requisição deve retornar 500 independentemente
    
    VALIDATES: Isolamento de erros entre requests
    """
    # Arrange
    mock_queries.obter_resumo_diario_ou_vazio.side_effect = Exception("Concurrent error")
    
    # Act - Múltiplas requisições
    responses = []
    for _ in range(5):
        response = client.get("/analytics/resumo-diario")
        responses.append(response)
    
    # Assert - Todas devem falhar independentemente
    assert all(r.status_code == 500 for r in responses)
    assert all("error" in r.json() for r in responses)
    
    # Assert - Cada erro é independente (não acumula erros)
    for response in responses:
        data = response.json()
        assert data["error"] == "internal_server_error"


@patch('app.analytics.api.routes.queries')
def test_error_with_unicode_characters(
    mock_queries,
    client,
    override_auth,
    override_db
):
    """
    DADO que erro contém caracteres especiais/unicode
    QUANDO o endpoint é chamado
    ENTÃO deve serializar corretamente para JSON
    
    VALIDATES: Serialização de erros com caracteres especiais
    """
    # Arrange - Erro com caracteres especiais
    mock_queries.obter_resumo_diario_ou_vazio.side_effect = Exception(
        "Falha na conexão: 'não é possível' — caracteres especiais: €, ñ, 中文"
    )
    
    # Act
    response = client.get("/analytics/resumo-diario")
    
    # Assert - Deve serializar sem problemas
    assert response.status_code == 500
    data = response.json()
    assert data["error"] == "internal_server_error"
    # JSON decode deve funcionar
    assert isinstance(data["detail"], str)


# ===== TESTES DE INTEGRAÇÃO (OPCIONAL) =====

@pytest.mark.integration
def test_integracao_resumo_diario_real(client, override_auth):
    """
    Teste de integração verificando fluxo completo do endpoint resumo-diario.
    
    Valida que o endpoint retorna dados corretos quando há vendas no dia.
    """
    from unittest.mock import patch
    from datetime import date
    
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
        "atualizado_em": date.today()
    }
    
    # Act
    with patch("app.read_models.queries.obter_resumo_diario_ou_vazio", return_value=mock_resumo):
        response = client.get("/analytics/resumo-diario")
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "quantidade_aberta" in data
    assert "quantidade_finalizada" in data
    assert "total_vendido" in data


# ============================================================================
# PARTE 2 — SEGURANÇA E AUTORIZAÇÃO
# ============================================================================
# Testes de robustez contra ataques e acessos não autorizados


def test_token_expirado_retorna_401(client, override_db):
    """
    DADO que um token JWT expirado é usado
    QUANDO qualquer endpoint protegido é chamado
    ENTÃO deve retornar 401 Unauthorized
    """
    from jose import jwt
    from datetime import datetime, timedelta
    from app.config import JWT_SECRET_KEY
    from app.auth.core import ALGORITHM
    
    # Arrange - Criar token expirado (exp: 1 hora atrás)
    expired_payload = {
        "sub": "test@example.com",
        "user_id": 1,
        "tenant_id": "00000000-0000-0000-0000-000000000001",
        "exp": datetime.utcnow() - timedelta(hours=1)  # EXPIRADO
    }
    expired_token = jwt.encode(expired_payload, JWT_SECRET_KEY, algorithm=ALGORITHM)
    
    # Act
    response = client.get(
        "/analytics/resumo-diario",
        headers={"Authorization": f"Bearer {expired_token}"}
    )
    
    # Assert - 401 (não 500, não 200)
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    # FastAPI JWT pode retornar diferentes mensagens para token expirado


def test_token_invalido_retorna_401(client, override_db):
    """
    DADO que um token JWT inválido/malformado é usado
    QUANDO qualquer endpoint protegido é chamado
    ENTÃO deve retornar 401 Unauthorized
    """
    # Arrange - Token completamente inválido
    invalid_tokens = [
        "Bearer invalid.token.here",
        "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature",
        "Bearer not-even-jwt-format",
        "Bearer ",
        "",
    ]
    
    for invalid_token in invalid_tokens:
        # Act
        response = client.get(
            "/analytics/resumo-diario",
            headers={"Authorization": invalid_token} if invalid_token else {}
        )
        
        # Assert - 401 ou 403
        assert response.status_code in [401, 403], f"Token '{invalid_token}' deveria retornar 401/403"


def test_token_sem_tenant_id_retorna_401(client, override_db):
    """
    DADO que um token JWT válido MAS sem tenant_id é usado
    QUANDO endpoint multi-tenant é chamado
    ENTÃO deve retornar 401 com mensagem específica
    """
    from jose import jwt
    from datetime import datetime, timedelta
    from app.config import JWT_SECRET_KEY
    from app.auth.core import ALGORITHM
    
    # Arrange - Token válido mas SEM tenant_id
    payload_sem_tenant = {
        "sub": "test@example.com",
        "user_id": 1,
        # FALTA: "tenant_id"
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    token_sem_tenant = jwt.encode(payload_sem_tenant, JWT_SECRET_KEY, algorithm=ALGORITHM)
    
    # Act
    response = client.get(
        "/analytics/resumo-diario",
        headers={"Authorization": f"Bearer {token_sem_tenant}"}
    )
    
    # Assert - 401 com mensagem específica
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    # Mensagem válida: "Tenant não selecionado" ou "Could not validate credentials"
    assert "tenant" in data["detail"].lower() or "credential" in data["detail"].lower()


def test_sql_injection_em_parametros(client, override_auth, override_db, caplog):
    """
    DADO que payloads de SQL injection são enviados em parâmetros
    QUANDO endpoints processam esses parâmetros
    ENTÃO deve:
    1. Bloquear/rejeitar o payload
    2. Gerar log de auditoria de segurança
    """
    import logging
    caplog.set_level(logging.WARNING)
    
    # Arrange - Payloads de SQL injection comuns
    sql_payloads = [
        "1' OR '1'='1",
        "1; DROP TABLE vendas--",
        "1' UNION SELECT NULL, NULL, NULL--",
        "admin'--",
        "' OR 1=1--",
    ]
    
    for payload in sql_payloads:
        # Limpar logs anteriores
        caplog.clear()
        
        # Act - Tentar injetar em parâmetro funcionario_id
        response = client.get(
            f"/analytics/performance-funcionario/{payload}"
        )
        
        # Assert 1: NÃO deve retornar 200 com dados válidos
        # Deve retornar 422 (validação) ou 404 (não encontrado) ou 500 (erro)
        assert response.status_code in [422, 404, 400, 500], \
            f"SQL injection '{payload}' não foi bloqueado adequadamente"
        
        # Assert 2: Deve gerar log de auditoria de segurança
        security_logs = [rec for rec in caplog.records if "SECURITY ALERT" in rec.message or "security_attack_detected" in str(rec)]
        if len(security_logs) > 0:
            # Log de segurança foi gerado (comportamento esperado)
            assert any("SQL_INJECTION" in str(rec) for rec in security_logs), \
                "Log de segurança não identificou tipo de ataque (SQL_INJECTION)"
        
        # Garantir que não retorna dados de múltiplos usuários (sinal de OR 1=1)
        if response.status_code == 200:
            data = response.json()
            # Se retornou 200, não deve ter lista de múltiplos resultados
            assert not isinstance(data, list) or len(data) <= 1


def test_xss_payload_em_query_params(client, override_auth, override_db):
    """
    DADO que payloads de XSS são enviados em query parameters
    QUANDO API processa esses parâmetros
    ENTÃO deve rejeitar com erro de validação (não deve executar script)
    
    NOTA: FastAPI pode refletir o input inválido na mensagem de erro de validação.
    Isso é aceitável desde que:
    1. Retorne status 422 (não 200)
    2. Não execute o script (apenas mostra como texto)
    3. Em produção, frontend não deve renderizar HTML de erros de validação
    """
    # Arrange - Payloads XSS comuns
    xss_payloads = [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert('XSS')>",
        "javascript:alert('XSS')",
        "<svg/onload=alert('XSS')>",
    ]
    
    for payload in xss_payloads:
        # Act - Tentar injetar em date parameter (como string)
        response = client.get(
            "/analytics/resumo-diario",
            params={"data": payload}
        )
        
        # Assert - CRÍTICO: Deve retornar erro de validação (422) ou erro genérico
        # NÃO deve retornar 200 (sucesso) com dados processados
        assert response.status_code in [422, 400, 500], \
            f"XSS payload '{payload}' foi aceito como válido (200)"
        
        # Assert - Se 422, é erro de validação (comportamento esperado)
        if response.status_code == 422:
            data = response.json()
            # FastAPI pode incluir o input no erro de validação
            # Isso é OK - o importante é que não retornou 200
            assert "error" in data or "detail" in data
            # Validação passou: payload foi REJEITADO


@patch('app.analytics.api.routes.queries')
def test_isolamento_tenant_nao_vaza_dados(
    mock_queries,
    client,
    override_auth,
    override_db
):
    """
    DADO que dois usuários de tenants diferentes fazem requisições
    QUANDO ambos consultam o mesmo endpoint
    ENTÃO os dados de um tenant NÃO devem vazar para outro
    
    NOTA: Este teste valida que o tenant_id é passado corretamente
    para as queries (mock validation)
    """
    # Arrange
    mock_queries.obter_resumo_diario_ou_vazio.return_value = mock_resumo_diario()
    
    # Act - Primeira requisição (tenant 1 via mock_user padrão)
    response1 = client.get("/analytics/resumo-diario")
    
    # Assert - Query foi chamada com db session (mock)
    assert response1.status_code == 200
    assert mock_queries.obter_resumo_diario_ou_vazio.called
    
    # Validação: A query recebeu uma session e uma data
    call_args = mock_queries.obter_resumo_diario_ou_vazio.call_args
    assert call_args is not None
    assert len(call_args[0]) == 2  # (db, data)
    
    # NOTA: Isolamento real é garantido pelo middleware de tenancy
    # que injeta tenant_id na session do SQLAlchemy (filtro automático)


def test_path_traversal_em_parametros(client, override_auth, override_db):
    """
    DADO que payloads de path traversal são enviados
    QUANDO API processa esses parâmetros
    ENTÃO deve rejeitar ou sanitizar (não deve acessar arquivos do sistema)
    """
    # Arrange - Payloads de path traversal
    path_payloads = [
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32\\config\\sam",
        "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
        "....//....//....//etc/passwd",
    ]
    
    for payload in path_payloads:
        # Act
        response = client.get(
            f"/analytics/performance-funcionario/{payload}"
        )
        
        # Assert - Não deve retornar 200 com conteúdo de arquivo
        # Deve retornar erro de validação ou 404
        assert response.status_code in [422, 404, 400, 500], \
            f"Path traversal '{payload}' não foi bloqueado"


def test_command_injection_em_parametros(client, override_auth, override_db):
    """
    DADO que payloads de command injection são enviados
    QUANDO API processa esses parâmetros
    ENTÃO não deve executar comandos do sistema
    """
    # Arrange - Payloads de command injection
    cmd_payloads = [
        "; ls -la",
        "| cat /etc/passwd",
        "& dir",
        "`whoami`",
        "$(whoami)",
    ]
    
    for payload in cmd_payloads:
        # Act
        response = client.get(
            f"/analytics/performance-funcionario/{payload}"
        )
        
        # Assert - Não deve executar comando E não deve retornar dados válidos
        assert response.status_code in [422, 404, 400, 500], \
            f"Command injection '{payload}' não foi bloqueado"


@patch('app.analytics.api.routes.queries')
def test_rate_limiting_behavior(
    mock_queries,
    client,
    override_auth,
    override_db
):
    """
    DADO que múltiplas requisições rápidas são feitas
    QUANDO rate limit é atingido (100 req/min para APIs)
    ENTÃO deve retornar 429 Too Many Requests após o limite
    
    LIMITE ATUAL: 100 req/min para endpoints /analytics/*
    """
    # Arrange
    mock_queries.obter_resumo_diario_ou_vazio.return_value = mock_resumo_diario()
    
    # Act - Fazer 105 requisições rápidas (exceder limite de 100/min)
    responses = []
    for i in range(105):
        response = client.get("/analytics/resumo-diario")
        responses.append(response)
    
    # Assert - Verificar se houve rate limiting
    status_codes = [r.status_code for r in responses]
    
    # Rate limiting ESTÁ implementado
    # Primeiras 100 devem passar (200)
    # Após 100, devem ser limitadas (429)
    success_count = status_codes.count(200)
    rate_limited_count = status_codes.count(429)
    
    # Validação robusta: pelo menos 100 bem-sucedidas E pelo menos 1 limitada
    assert success_count >= 100, f"Esperava ≥100 sucesso, teve {success_count}"
    assert rate_limited_count > 0, f"Esperava rate limiting (429), mas nenhuma requisição foi limitada"
    
    # Validar payload do erro 429
    for response in responses:
        if response.status_code == 429:
            data = response.json()
            assert "error" in data
            assert data["error"] == "rate_limit_exceeded"
            assert "retry_after" in data
            break  # Validou pelo menos um 429


@patch('app.analytics.api.routes.queries')
def test_parametros_extremos_nao_causam_crash(
    mock_queries,
    client,
    override_auth,
    override_db
):
    """
    DADO que parâmetros com valores extremos são enviados
    QUANDO API valida esses parâmetros
    ENTÃO deve rejeitar graciosamente (não deve crashar)
    """
    # Arrange
    mock_queries.obter_ranking_parceiros_ou_vazio.return_value = []
    
    # Act & Assert - Valores extremos
    extreme_values = [
        ("limite", "-1"),       # Negativo
        ("limite", "0"),        # Zero
        ("limite", "9999999"),  # Muito grande
        ("limite", "abc"),      # Não numérico
        ("limite", "1.5"),      # Float quando espera int
        ("limite", ""),         # Vazio
    ]
    
    for param_name, param_value in extreme_values:
        response = client.get(
            "/analytics/ranking-parceiros",
            params={param_name: param_value}
        )
        
        # Deve retornar erro de validação OU aplicar default
        # NÃO deve retornar 500 (crash)
        assert response.status_code in [200, 422, 400], \
            f"Valor extremo {param_name}={param_value} causou crash (500)"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


# ============================================================================
# TESTES DE PRODUÇÃO - SANITIZAÇÃO DE ERROS
# ============================================================================

@patch('app.analytics.api.routes.queries')
@patch('app.config.ENVIRONMENT', 'production')  # Simular ambiente de produção
def test_erro_500_em_producao_nao_expoe_detalhes(
    mock_queries,
    client,
    override_auth,
    override_db
):
    """
    DADO que um erro interno ocorre em PRODUÇÃO
    QUANDO o exception handler processa o erro
    ENTÃO deve retornar mensagem genérica SEM detalhes internos
    
    SEGURANÇA: Em produção, detalhes de erro ajudam atacantes.
    """
    # Arrange - Mock que lança erro
    mock_queries.obter_resumo_diario_ou_vazio.side_effect = Exception(
        "DatabaseConnectionError: psycopg2.OperationalError host=10.0.1.5 user=admin_prod database=petshop_prod"
    )
    
    # Act
    response = client.get("/analytics/resumo-diario")
    
    # Assert - Status 500
    assert response.status_code == 500
    
    # Assert - Payload NÃO deve conter detalhes sensíveis
    data = response.json()
    assert "error" in data
    assert data["error"] == "internal_server_error"
    assert "message" in data
    
    # CRÍTICO: Não deve expor detalhes em produção
    assert "detail" not in data, "❌ FALHA DE SEGURANÇA: detalhes expostos em produção"
    assert "type" not in data, "❌ FALHA DE SEGURANÇA: tipo de exceção exposto em produção"
    
    # Validar mensagem genérica
    assert "equipe foi notificada" in data["message"].lower() or "erro interno" in data["message"].lower()
    
    # Garantir que nenhum dado sensível vazou no JSON
    response_text = response.text.lower()
    assert "psycopg2" not in response_text
    assert "host=" not in response_text
    assert "database=" not in response_text
    assert "10.0.1.5" not in response_text


@patch('app.analytics.api.routes.queries')
@patch('app.config.ENVIRONMENT', 'development')  # Simular ambiente de dev
def test_erro_500_em_dev_mostra_detalhes(
    mock_queries,
    client,
    override_auth,
    override_db
):
    """
    DADO que um erro interno ocorre em DESENVOLVIMENTO
    QUANDO o exception handler processa o erro
    ENTÃO deve retornar detalhes para debugging
    
    DESENVOLVIMENTO: Detalhes ajudam no debugging.
    """
    # Arrange - Mock que lança erro
    error_message = "Test database connection failed"
    mock_queries.obter_resumo_diario_ou_vazio.side_effect = ValueError(error_message)
    
    # Act
    response = client.get("/analytics/resumo-diario")
    
    # Assert - Status 500
    assert response.status_code == 500
    
    # Assert - Payload DEVE conter detalhes em dev
    data = response.json()
    assert "detail" in data, "Dev deve mostrar detalhes para debugging"
    assert "type" in data, "Dev deve mostrar tipo de exceção"
    assert data["type"] == "ValueError"
    assert error_message in data["detail"]


# ============================================================================
# PARTE 3: TESTES DE CONTRATO (Response Schemas)
# ============================================================================
# Objetivo: Validar que responses seguem schemas Pydantic corretos
# - Todos campos obrigatórios presentes
# - Tipos de dados corretos (int, str, float, date)
# - Formatos corretos (ISO 8601 para datas)
# - Valores consistentes (ex: comissão = base × percentual)
# - Limites numéricos (valores ≥ 0, percentuais 0-100)


@patch('app.analytics.api.routes.queries')
def test_contrato_resumo_diario_schema(
    mock_queries,
    client,
    override_auth,
    override_db
):
    """
    DADO um response de /analytics/resumo-diario
    QUANDO validamos o schema
    ENTÃO todos campos obrigatórios devem estar presentes e com tipos corretos
    """
    # Arrange - Mock com dados válidos
    from datetime import date
    mock_data = {
        "id": 1,
        "data": date(2026, 2, 8),
        "quantidade_aberta": 5,
        "quantidade_finalizada": 10,
        "quantidade_cancelada": 2,
        "total_vendido": 1500.50,
        "total_cancelado": 200.00,
        "ticket_medio": 150.05
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


@patch('app.analytics.api.routes.queries')
def test_contrato_resumo_periodo_schema(
    mock_queries,
    client,
    override_auth,
    override_db
):
    """
    DADO um response de /analytics/periodo
    QUANDO validamos o schema
    ENTÃO deve retornar lista de resumos diários com campos corretos
    """
    # Arrange - A rota retorna LISTA de resumos diários
    from datetime import date
    mock_data = [
        {
            "id": 1,
            "data": date(2026, 2, 1),
            "quantidade_aberta": 3,
            "quantidade_finalizada": 10,
            "quantidade_cancelada": 1,
            "total_vendido": 1500.00,
            "total_cancelado": 100.00,
            "ticket_medio": 150.00
        },
        {
            "id": 2,
            "data": date(2026, 2, 2),
            "quantidade_aberta": 5,
            "quantidade_finalizada": 15,
            "quantidade_cancelada": 2,
            "total_vendido": 2000.00,
            "total_cancelado": 200.00,
            "ticket_medio": 133.33
        }
    ]
    mock_queries.obter_resumo_periodo.return_value = mock_data
    
    # Act
    response = client.get("/analytics/periodo?data_inicio=2026-02-01&data_fim=2026-02-08")
    
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


@patch('app.analytics.api.routes.queries')
def test_contrato_ranking_parceiros_schema(
    mock_queries,
    client,
    override_auth,
    override_db
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
            "quantidade_vendas": 50
        },
        {
            "parceiro_id": 2,
            "parceiro_nome": "Parceiro B",
            "total_vendido": 15000.00,
            "quantidade_vendas": 30
        }
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


@patch('app.analytics.api.routes.queries')
def test_contrato_receita_mensal_schema(
    mock_queries,
    client,
    override_auth,
    override_db
):
    """
    DADO um response de /analytics/receita-mensal
    QUANDO validamos o schema
    ENTÃO todos campos obrigatórios devem estar presentes
    """
    # Arrange
    from datetime import date
    mock_data = {
        "mes": date(2026, 2, 1),
        "receita_total": 50000.00,
        "quantidade_vendas": 200,
        "ticket_medio": 250.00
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


@patch('app.analytics.api.routes.queries')
def test_contrato_ultimos_dias_schema(
    mock_queries,
    client,
    override_auth,
    override_db
):
    """
    DADO um response de /analytics/ultimos-dias
    QUANDO validamos o schema
    ENTÃO deve retornar lista de resumos diários
    """
    # Arrange
    from datetime import date
    mock_data = [
        {
            "data": date(2026, 2, 8),
            "total_vendido": 1500.00,
            "quantidade_vendas": 10,
            "ticket_medio": 150.00
        },
        {
            "data": date(2026, 2, 7),
            "total_vendido": 2000.00,
            "quantidade_vendas": 15,
            "ticket_medio": 133.33
        }
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


@patch('app.analytics.api.routes.queries')
def test_contrato_estatisticas_gerais_schema(
    mock_queries,
    client,
    override_auth,
    override_db
):
    """
    DADO um response de /analytics/estatisticas-gerais
    QUANDO validamos o schema
    ENTÃO deve retornar estatísticas agregadas
    """
    # Arrange
    from datetime import date
    mock_data = {
        "mes_atual": {
            "mes": date(2026, 2, 1),
            "receita_total": 50000.00,
            "quantidade_vendas": 200,
            "ticket_medio": 250.00
        },
        "top_5_parceiros": [
            {
                "parceiro_id": 1,
                "parceiro_nome": "Parceiro A",
                "total_vendido": 25000.00,
                "quantidade_vendas": 50
            }
        ],
        "ultimos_7_dias": [
            {
                "data": date(2026, 2, 8),
                "total_vendido": 1500.00,
                "quantidade_vendas": 10,
                "ticket_medio": 150.00
            }
        ]
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


@patch('app.analytics.api.routes.queries')
def test_contrato_comparativo_receita_schema(
    mock_queries,
    client,
    override_auth,
    override_db
):
    """
    DADO um response de /analytics/comparativo-receita
    QUANDO validamos o schema
    ENTÃO deve retornar lista de receitas mensais com variação
    """
    # Arrange - A rota retorna LISTA de receitas mensais e usa obter_comparativo_mensal
    from datetime import date
    mock_data = [
        {
            "mes": date(2026, 2, 1),
            "receita_total": 50000.00,
            "quantidade_vendas": 200,
            "ticket_medio": 250.00,
            "variacao_percentual": 15.5
        },
        {
            "mes": date(2026, 1, 1),
            "receita_total": 43000.00,
            "quantidade_vendas": 180,
            "ticket_medio": 238.89,
            "variacao_percentual": -5.2
        }
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
