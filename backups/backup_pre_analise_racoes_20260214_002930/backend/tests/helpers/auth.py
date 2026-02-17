"""
🔐 HELPERS DE AUTENTICAÇÃO

Funções reutilizáveis para criar tokens JWT e headers de autenticação.

Exemplo de uso:
    headers = create_auth_header(user_id=1, tenant_id="uuid")
    response = client.get("/api/endpoint", headers=headers)
"""

from datetime import datetime, timedelta
from jose import jwt
from app.config import JWT_SECRET_KEY
from app.auth.core import ALGORITHM


def create_auth_header(
    user_id: int = 1,
    tenant_id: str = "00000000-0000-0000-0000-000000000001",
    email: str = "test@example.com"
) -> dict:
    """
    Cria header Authorization com token JWT válido.
    
    Args:
        user_id: ID do usuário (default: 1)
        tenant_id: ID do tenant (default: UUID padrão de teste)
        email: Email do usuário (default: test@example.com)
    
    Returns:
        Dict com header Authorization pronto para uso
    
    Exemplo:
        headers = create_auth_header(user_id=5, tenant_id="abc-123")
        response = client.get("/api/vendas", headers=headers)
    """
    payload = {
        "sub": email,
        "user_id": user_id,
        "tenant_id": tenant_id,
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


def create_expired_token() -> str:
    """
    Cria token JWT expirado (exp: 1 hora atrás).
    
    Útil para testar comportamento de segurança.
    
    Returns:
        Token JWT expirado
    
    Exemplo:
        token = create_expired_token()
        response = client.get("/api/vendas", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401
    """
    payload = {
        "sub": "test@example.com",
        "user_id": 1,
        "tenant_id": "00000000-0000-0000-0000-000000000001",
        "exp": datetime.utcnow() - timedelta(hours=1)  # Expirado
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=ALGORITHM)


def create_invalid_token() -> str:
    """
    Cria token JWT completamente inválido/malformado.
    
    Útil para testar validação de tokens.
    
    Returns:
        Token JWT inválido
    
    Exemplo:
        token = create_invalid_token()
        response = client.get("/api/vendas", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401
    """
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.INVALID_PAYLOAD.INVALID_SIGNATURE"


def create_token_without_tenant() -> str:
    """
    Cria token JWT válido mas sem tenant_id.
    
    Útil para testar isolamento de tenants.
    
    Returns:
        Token JWT sem tenant_id
    
    Exemplo:
        token = create_token_without_tenant()
        response = client.get("/api/vendas", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401
    """
    payload = {
        "sub": "test@example.com",
        "user_id": 1,
        # tenant_id ausente propositalmente
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=ALGORITHM)


def create_token_for_different_tenant(tenant_id: str) -> str:
    """
    Cria token JWT para tenant diferente.
    
    Útil para testar isolamento entre tenants.
    
    Args:
        tenant_id: ID do tenant diferente
    
    Returns:
        Token JWT com tenant_id especificado
    
    Exemplo:
        token = create_token_for_different_tenant("99999999-9999-9999-9999-999999999999")
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/vendas", headers=headers)
        # Deve retornar apenas dados do tenant 99999999-9999-9999-9999-999999999999
    """
    payload = {
        "sub": "test@example.com",
        "user_id": 999,
        "tenant_id": tenant_id,
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=ALGORITHM)
