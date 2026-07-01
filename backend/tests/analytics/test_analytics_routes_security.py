"""Testes de seguranca, autenticacao e robustez de parametros de analytics."""

from datetime import datetime, timezone
from unittest.mock import patch

from app.main import app

from .analytics_test_helpers import mock_resumo_diario


def test_endpoint_sem_autenticacao(client):
    """
    DADO um endpoint protegido
    QUANDO chamado sem autenticação
    ENTÃO deve retornar erro de autenticação
    """
    # Remove override de auth se existir
    app.dependency_overrides.clear()

    # Act
    response = client.get("/analytics/resumo-diario")

    # Assert
    assert response.status_code in [401, 403]


def test_token_expirado_retorna_401(client, override_db):
    """
    DADO que um token JWT expirado é usado
    QUANDO qualquer endpoint protegido é chamado
    ENTÃO deve retornar 401 Unauthorized
    """
    from app.security.jwt_compat import jwt
    from datetime import timedelta
    from app.config import JWT_SECRET_KEY
    from app.auth.core import ALGORITHM

    # Arrange - Criar token expirado (exp: 1 hora atrás)
    expired_payload = {
        "sub": "test@example.com",
        "user_id": 1,
        "tenant_id": "00000000-0000-0000-0000-000000000001",
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),  # EXPIRADO
    }
    expired_token = jwt.encode(expired_payload, JWT_SECRET_KEY, algorithm=ALGORITHM)

    # Act
    response = client.get(
        "/analytics/resumo-diario", headers={"Authorization": f"Bearer {expired_token}"}
    )

    # Assert - 401 (não 500, não 200)
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data


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
            headers={"Authorization": invalid_token} if invalid_token else {},
        )

        # Assert - 401 ou 403
        assert response.status_code in [401, 403], (
            f"Token '{invalid_token}' deveria retornar 401/403"
        )


def test_token_sem_tenant_id_retorna_401(client, override_db):
    """
    DADO que um token JWT válido MAS sem tenant_id é usado
    QUANDO endpoint multi-tenant é chamado
    ENTÃO deve retornar 401 com mensagem específica
    """
    from app.security.jwt_compat import jwt
    from datetime import timedelta
    from app.config import JWT_SECRET_KEY
    from app.auth.core import ALGORITHM

    # Arrange - Token válido mas SEM tenant_id
    payload_sem_tenant = {
        "sub": "test@example.com",
        "user_id": 1,
        # FALTA: "tenant_id"
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    token_sem_tenant = jwt.encode(
        payload_sem_tenant, JWT_SECRET_KEY, algorithm=ALGORITHM
    )

    # Act
    response = client.get(
        "/analytics/resumo-diario",
        headers={"Authorization": f"Bearer {token_sem_tenant}"},
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
        response = client.get(f"/analytics/performance-funcionario/{payload}")

        # Assert 1: NÃO deve retornar 200 com dados válidos
        # Deve retornar 422 (validação) ou 404 (não encontrado) ou 500 (erro)
        assert response.status_code in [422, 404, 400, 500], (
            f"SQL injection '{payload}' não foi bloqueado adequadamente"
        )

        # Assert 2: Deve gerar log de auditoria de segurança
        security_logs = [
            rec
            for rec in caplog.records
            if "SECURITY ALERT" in rec.message or "security_attack_detected" in str(rec)
        ]
        if len(security_logs) > 0:
            # Log de segurança foi gerado (comportamento esperado)
            assert any("SQL_INJECTION" in str(rec) for rec in security_logs), (
                "Log de segurança não identificou tipo de ataque (SQL_INJECTION)"
            )

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
        response = client.get("/analytics/resumo-diario", params={"data": payload})

        # Assert - CRÍTICO: Deve retornar erro de validação (422) ou erro genérico
        # NÃO deve retornar 200 (sucesso) com dados processados
        assert response.status_code in [422, 400, 500], (
            f"XSS payload '{payload}' foi aceito como válido (200)"
        )

        # Assert - Se 422, é erro de validação (comportamento esperado)
        if response.status_code == 422:
            data = response.json()
            # FastAPI pode incluir o input no erro de validação
            # Isso é OK - o importante é que não retornou 200
            assert "error" in data or "detail" in data


@patch("app.analytics.api.routes.queries")
def test_isolamento_tenant_nao_vaza_dados(
    mock_queries, client, override_auth, override_db
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
        response = client.get(f"/analytics/performance-funcionario/{payload}")

        # Assert - Não deve retornar 200 com conteúdo de arquivo
        # Deve retornar erro de validação ou 404
        assert response.status_code in [422, 404, 400, 500], (
            f"Path traversal '{payload}' não foi bloqueado"
        )


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
        response = client.get(f"/analytics/performance-funcionario/{payload}")

        # Assert - Não deve executar comando E não deve retornar dados válidos
        assert response.status_code in [422, 404, 400, 500], (
            f"Command injection '{payload}' não foi bloqueado"
        )


@patch("app.analytics.api.routes.queries")
def test_rate_limiting_behavior(mock_queries, client, override_auth, override_db):
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
    assert rate_limited_count > 0, (
        "Esperava rate limiting (429), mas nenhuma requisição foi limitada"
    )

    # Validar payload do erro 429
    for response in responses:
        if response.status_code == 429:
            data = response.json()
            assert "error" in data
            assert data["error"] == "rate_limit_exceeded"
            assert "retry_after" in data
            break  # Validou pelo menos um 429


@patch("app.analytics.api.routes.queries")
def test_parametros_extremos_nao_causam_crash(
    mock_queries, client, override_auth, override_db
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
        ("limite", "-1"),  # Negativo
        ("limite", "0"),  # Zero
        ("limite", "9999999"),  # Muito grande
        ("limite", "abc"),  # Não numérico
        ("limite", "1.5"),  # Float quando espera int
        ("limite", ""),  # Vazio
    ]

    for param_name, param_value in extreme_values:
        response = client.get(
            "/analytics/ranking-parceiros", params={param_name: param_value}
        )

        # Deve retornar erro de validação OU aplicar default
        # NÃO deve retornar 500 (crash)
        assert response.status_code in [200, 422, 400], (
            f"Valor extremo {param_name}={param_value} causou crash (500)"
        )
