"""
⚠️ HELPERS DE VALIDAÇÃO DE ERROS

Funções para validar comportamento de erros e segurança.

Exemplo de uso:
    assert_401(response)
    assert_500_production(response)
    assert_error_sanitized(response)
"""

from unittest.mock import patch
from typing import Any


def assert_401(response: Any, expected_detail: str = None):
    """
    Valida que response é 401 Unauthorized.
    
    Args:
        response: Response do TestClient
        expected_detail: Mensagem esperada (opcional)
    
    Raises:
        AssertionError: Se status code não for 401
    
    Exemplo:
        token = create_expired_token()
        response = client.get("/api/vendas", headers={"Authorization": f"Bearer {token}"})
        assert_401(response)
    """
    assert response.status_code == 401, \
        f"❌ Esperado 401 Unauthorized, recebido {response.status_code}"
    
    data = response.json()
    assert "detail" in data, "❌ Response 401 deve conter 'detail'"
    
    if expected_detail:
        assert expected_detail in data["detail"], \
            f"❌ Esperado '{expected_detail}' em detail, recebido: {data['detail']}"


def assert_429(response: Any):
    """
    Valida que response é 429 Too Many Requests (rate limit).
    
    Args:
        response: Response do TestClient
    
    Raises:
        AssertionError: Se status code não for 429
    
    Exemplo:
        # Fazer 101 requests rápidos
        for i in range(101):
            response = client.get("/api/vendas", headers=headers)
        
        assert_429(response)  # Último deve ser 429
    """
    assert response.status_code == 429, \
        f"❌ Esperado 429 Too Many Requests, recebido {response.status_code}"
    
    data = response.json()
    assert "detail" in data, "❌ Response 429 deve conter 'detail'"
    
    # Valida headers de rate limit
    assert "X-RateLimit-Limit" in response.headers, \
        "❌ Response 429 deve conter header 'X-RateLimit-Limit'"
    assert "X-RateLimit-Remaining" in response.headers, \
        "❌ Response 429 deve conter header 'X-RateLimit-Remaining'"


def assert_500(response: Any):
    """
    Valida que response é 500 Internal Server Error.
    
    Args:
        response: Response do TestClient
    
    Raises:
        AssertionError: Se status code não for 500
    
    Exemplo:
        with patch("app.analytics.queries.obter_resumo", side_effect=Exception("DB error")):
            response = client.get("/api/analytics/resumo")
        
        assert_500(response)
    """
    assert response.status_code == 500, \
        f"❌ Esperado 500 Internal Server Error, recebido {response.status_code}"
    
    data = response.json()
    assert "detail" in data, "❌ Response 500 deve conter 'detail'"


def assert_500_production(response: Any):
    """
    Valida que erro 500 em produção NÃO expõe detalhes sensíveis.
    
    Args:
        response: Response do TestClient
    
    Raises:
        AssertionError: Se detalhes sensíveis forem expostos
    
    Exemplo:
        with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
            with patch("app.analytics.queries.obter_resumo", side_effect=Exception("DB_PASSWORD=secret")):
                response = client.get("/api/analytics/resumo")
        
        assert_500_production(response)
    """
    assert_500(response)
    
    data = response.json()
    
    # Em produção, deve ter apenas mensagem genérica
    assert data["detail"] == "Erro interno do servidor", \
        f"❌ VAZAMENTO: Detalhes expostos em produção: {data['detail']}"
    
    # Não deve ter stacktrace, type, ou mensagem detalhada
    assert "type" not in data, "❌ VAZAMENTO: 'type' exposto em produção"
    assert "traceback" not in data, "❌ VAZAMENTO: 'traceback' exposto em produção"
    assert "message" not in data or data["message"] == "Erro interno do servidor", \
        "❌ VAZAMENTO: Mensagem detalhada exposta em produção"


def assert_500_development(response: Any):
    """
    Valida que erro 500 em desenvolvimento MOSTRA detalhes para debug.
    
    Args:
        response: Response do TestClient
    
    Raises:
        AssertionError: Se detalhes não forem fornecidos
    
    Exemplo:
        with patch.dict("os.environ", {"ENVIRONMENT": "development"}):
            with patch("app.analytics.queries.obter_resumo", side_effect=Exception("Connection timeout")):
                response = client.get("/api/analytics/resumo")
        
        assert_500_development(response)
    """
    assert_500(response)
    
    data = response.json()
    
    # Em dev, deve ter detalhes para debug
    # (pode ser detail completo ou campos separados)
    has_details = (
        len(data.get("detail", "")) > 30 or  # Mensagem longa
        "type" in data or  # Tipo da exceção
        "message" in data  # Mensagem original
    )
    
    assert has_details, \
        f"❌ Desenvolvimento deve fornecer detalhes para debug. Recebido: {data}"


def assert_error_sanitized(response: Any, sensitive_words: list = None):
    """
    Valida que erro não expõe informações sensíveis.
    
    Args:
        response: Response do TestClient
        sensitive_words: Lista de palavras que não devem aparecer
    
    Raises:
        AssertionError: Se informação sensível for encontrada
    
    Exemplo:
        response = client.get("/api/vendas/999999")
        assert_error_sanitized(response, ["password", "secret", "token"])
    """
    if sensitive_words is None:
        sensitive_words = [
            "password", "senha", "secret", "token", "api_key",
            "database", "postgres", "mysql", "connection",
            "traceback", "file", "line", "exception"
        ]
    
    response_text = str(response.json()).lower()
    
    found_sensitive = []
    for word in sensitive_words:
        if word.lower() in response_text:
            found_sensitive.append(word)
    
    assert len(found_sensitive) == 0, \
        f"❌ VAZAMENTO DE SEGURANÇA: Palavras sensíveis encontradas: {found_sensitive}"


def assert_sql_injection_blocked(response: Any):
    """
    Valida que tentativa de SQL injection foi bloqueada ou sanitizada.
    
    Args:
        response: Response do TestClient
    
    Raises:
        AssertionError: Se SQL injection foi bem-sucedida
    
    Exemplo:
        response = client.get("/api/vendas?id=' OR '1'='1")
        assert_sql_injection_blocked(response)
    """
    # Payload deve ser rejeitado (400/422) ou sanitizado (200 sem dados incorretos)
    assert response.status_code in [200, 400, 422], \
        f"❌ Status inesperado para SQL injection: {response.status_code}"
    
    # Se 200, não deve retornar todos os dados
    if response.status_code == 200:
        data = response.json()
        # Heurística: não deve retornar mais de 100 registros de uma vez
        # (indica que ' OR '1'='1 foi executado)
        if isinstance(data, list):
            assert len(data) < 100, \
                "❌ SQL INJECTION BEM-SUCEDIDA: Retornou todos os registros"


def assert_xss_sanitized(response: Any):
    """
    Valida que payload XSS foi sanitizado.
    
    Args:
        response: Response do TestClient
    
    Raises:
        AssertionError: Se XSS não foi sanitizado
    
    Exemplo:
        response = client.get("/api/busca?q=<script>alert('xss')</script>")
        assert_xss_sanitized(response)
    """
    response_text = str(response.json())
    
    # Não deve conter tags script, onerror, etc.
    dangerous_patterns = ["<script", "onerror=", "onclick=", "javascript:", "eval("]
    
    found_dangerous = []
    for pattern in dangerous_patterns:
        if pattern.lower() in response_text.lower():
            found_dangerous.append(pattern)
    
    assert len(found_dangerous) == 0, \
        f"❌ XSS NÃO SANITIZADO: Padrões perigosos encontrados: {found_dangerous}"
