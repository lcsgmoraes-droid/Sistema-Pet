"""
Testes de autenticação e JWT
"""
import jwt
import os
from datetime import datetime


def test_login_returns_jwt_token(client, tenant_factory, user_factory):
    """
    Testa que login com credenciais válidas retorna JWT.
    Protege: fluxo de autenticação básico.
    """
    tenant = tenant_factory()
    password = "TestPassword@123"
    user = user_factory(
        tenant_id=tenant.id,
        email="login@test.com",
        password=password
    )
    
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "login@test.com", "password": password}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_jwt_contains_tenant_id(client, tenant_factory, user_factory):
    """
    Testa que JWT contém tenant_id no payload.
    Protege: contexto de tenant em requests autenticadas.
    """
    tenant = tenant_factory(nome="Tenant JWT Test")
    password = "Pass@123"
    user = user_factory(
        tenant_id=tenant.id,
        email="jwt@test.com",
        password=password
    )
    
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "jwt@test.com", "password": password}
    )
    
    assert response.status_code == 200
    token = response.json()["access_token"]
    
    # Decodificar JWT
    secret_key = os.getenv("JWT_SECRET_KEY", "test-secret-key-min-32-chars-long-for-security")
    payload = jwt.decode(token, secret_key, algorithms=["HS256"])
    
    assert "tenant_id" in payload
    assert payload["tenant_id"] == tenant.id
    assert payload["sub"] == str(user.id)


def test_login_with_invalid_credentials_fails(client, tenant_factory, user_factory):
    """
    Testa que login com credenciais inválidas falha.
    Protege: segurança de autenticação.
    """
    tenant = tenant_factory()
    user = user_factory(
        tenant_id=tenant.id,
        email="valid@test.com",
        password="CorrectPassword@123"
    )
    
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "valid@test.com", "password": "WrongPassword"}
    )
    
    assert response.status_code in [401, 403]


def test_auth_headers_contain_valid_jwt(auth_headers):
    """
    Testa que fixture auth_headers gera JWT válido.
    Protege: infraestrutura de testes autenticados.
    """
    headers, tenant, user = auth_headers()
    
    assert "Authorization" in headers
    assert headers["Authorization"].startswith("Bearer ")
    
    token = headers["Authorization"].split(" ")[1]
    secret_key = os.getenv("JWT_SECRET_KEY", "test-secret-key-min-32-chars-long-for-security")
    
    payload = jwt.decode(token, secret_key, algorithms=["HS256"])
    
    assert payload["tenant_id"] == tenant.id
    assert payload["sub"] == str(user.id)
    assert payload["exp"] > datetime.utcnow().timestamp()
