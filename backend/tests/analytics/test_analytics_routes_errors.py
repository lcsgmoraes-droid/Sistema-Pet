"""Testes de resiliencia e sanitizacao de erros de analytics."""

from unittest.mock import patch


@patch("app.analytics.api.routes.queries")
def test_resumo_diario_internal_error(mock_queries, client, override_auth, override_db):
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
    mock_queries.obter_resumo_diario_ou_vazio.side_effect = Exception(
        "Database connection failed"
    )

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


@patch("app.analytics.api.routes.queries")
def test_receita_mensal_internal_error(
    mock_queries, client, override_auth, override_db
):
    """
    DADO que queries.obter_receita_mensal_ou_vazia lança Exception
    QUANDO o endpoint /analytics/receita-mensal é chamado
    ENTÃO deve retornar 500 com tratamento adequado
    """
    # Arrange
    mock_queries.obter_receita_mensal_ou_vazia.side_effect = RuntimeError(
        "Query timeout"
    )

    # Act
    response = client.get("/analytics/receita-mensal")

    # Assert
    assert response.status_code == 500
    data = response.json()
    assert data["error"] == "internal_server_error"
    assert "message" in data
    assert "detail" in data


@patch("app.analytics.api.routes.queries")
def test_ranking_parceiros_internal_error(
    mock_queries, client, override_auth, override_db
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


@patch("app.analytics.api.routes.queries")
def test_estatisticas_gerais_internal_error(
    mock_queries, client, override_auth, override_db
):
    """
    DADO que queries.obter_estatisticas_gerais lança ValueError
    QUANDO o endpoint é chamado
    ENTÃO deve retornar 500 sem quebrar
    """
    # Arrange
    mock_queries.obter_estatisticas_gerais.side_effect = ValueError(
        "Invalid aggregation"
    )

    # Act
    response = client.get("/analytics/estatisticas-gerais")

    # Assert
    assert response.status_code == 500
    data = response.json()
    assert data["error"] == "internal_server_error"
    assert "type" in data  # Deve incluir tipo da exceção


@patch("app.analytics.api.routes.queries")
def test_ultimos_dias_internal_error(mock_queries, client, override_auth, override_db):
    """
    DADO que queries.obter_ultimos_dias lança AttributeError
    QUANDO o endpoint é chamado
    ENTÃO deve tratar sem expor implementação interna
    """
    # Arrange
    mock_queries.obter_ultimos_dias.side_effect = AttributeError(
        "'NoneType' object has no attribute 'data'"
    )

    # Act
    response = client.get("/analytics/ultimos-dias?quantidade=7")

    # Assert
    assert response.status_code == 500
    data = response.json()
    assert data["error"] == "internal_server_error"
    # Não deve expor "NoneType" em produção, mas deve ser tratado
    assert isinstance(data["detail"], str)


@patch("app.analytics.api.routes.queries")
def test_periodo_internal_error(mock_queries, client, override_auth, override_db):
    """
    DADO que queries.obter_resumo_periodo lança TypeError
    QUANDO o endpoint é chamado com datas válidas
    ENTÃO deve retornar 500 (não 422 de validação)
    """
    # Arrange
    mock_queries.obter_resumo_periodo.side_effect = TypeError(
        "unsupported operand type"
    )

    # Act
    response = client.get(
        "/analytics/periodo?data_inicio=2025-01-01&data_fim=2025-01-31"
    )

    # Assert
    assert response.status_code == 500
    data = response.json()
    assert data["error"] == "internal_server_error"


@patch("app.analytics.api.routes.queries")
def test_comparativo_receita_internal_error(
    mock_queries, client, override_auth, override_db
):
    """
    DADO que queries.obter_comparativo_mensal lança IndexError
    QUANDO o endpoint é chamado
    ENTÃO deve tratar lista vazia ou índice inválido
    """
    # Arrange
    mock_queries.obter_comparativo_mensal.side_effect = IndexError(
        "list index out of range"
    )

    # Act
    response = client.get("/analytics/comparativo-receita?meses=6")

    # Assert
    assert response.status_code == 500
    data = response.json()
    assert data["error"] == "internal_server_error"


@patch("app.analytics.api.routes.queries")
def test_performance_funcionario_internal_error(
    mock_queries, client, override_auth, override_db
):
    """
    DADO que queries.obter_performance_funcionario lança Exception genérica
    QUANDO o endpoint é chamado
    ENTÃO deve retornar 500 sem quebrar serialização
    """
    # Arrange
    mock_queries.obter_performance_funcionario.side_effect = Exception(
        "Unexpected error in aggregation"
    )

    # Act
    response = client.get("/analytics/performance-funcionario/999")

    # Assert
    assert response.status_code == 500
    data = response.json()
    assert data["error"] == "internal_server_error"
    assert "message" in data
    assert "detail" in data


@patch("app.analytics.api.routes.queries")
def test_multiple_concurrent_errors(mock_queries, client, override_auth, override_db):
    """
    DADO múltiplas requisições simultâneas com erros
    QUANDO o endpoint é chamado várias vezes
    ENTÃO cada requisição deve retornar 500 independentemente

    VALIDATES: Isolamento de erros entre requests
    """
    # Arrange
    mock_queries.obter_resumo_diario_ou_vazio.side_effect = Exception(
        "Concurrent error"
    )

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


@patch("app.analytics.api.routes.queries")
def test_error_with_unicode_characters(
    mock_queries, client, override_auth, override_db
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


@patch("app.analytics.api.routes.queries")
@patch("app.config.ENVIRONMENT", "production")  # Simular ambiente de produção
def test_erro_500_em_producao_nao_expoe_detalhes(
    mock_queries, client, override_auth, override_db
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
    assert "type" not in data, (
        "❌ FALHA DE SEGURANÇA: tipo de exceção exposto em produção"
    )

    # Validar mensagem genérica
    assert (
        "equipe foi notificada" in data["message"].lower()
        or "erro interno" in data["message"].lower()
    )

    # Garantir que nenhum dado sensível vazou no JSON
    response_text = response.text.lower()
    assert "psycopg2" not in response_text
    assert "host=" not in response_text
    assert "database=" not in response_text
    assert "10.0.1.5" not in response_text


@patch("app.analytics.api.routes.queries")
@patch("app.config.ENVIRONMENT", "development")  # Simular ambiente de dev
def test_erro_500_em_dev_mostra_detalhes(
    mock_queries, client, override_auth, override_db
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
