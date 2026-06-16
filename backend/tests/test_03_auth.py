"""
Testes de autenticação e JWT
"""
import jwt
import os
from datetime import datetime, timezone


def _login_and_select_tenant(client, email: str, password: str, tenant_id: str):
    login_response = client.post(
        "/auth/login-multitenant",
        json={"email": email, "password": password}
    )
    assert login_response.status_code == 200
    login_token = login_response.json()["access_token"]

    return client.post(
        "/auth/select-tenant",
        json={"tenant_id": str(tenant_id)},
        headers={"Authorization": f"Bearer {login_token}"}
    )


def _jwt_payload(token: str) -> dict:
    secret_key = os.getenv("JWT_SECRET_KEY", "test-secret-key-min-32-chars-long-for-security")
    return jwt.decode(token, secret_key, algorithms=["HS256"])


def _seconds_until_exp(payload: dict) -> float:
    return payload["exp"] - datetime.now(timezone.utc).timestamp()


def test_login_returns_jwt_token(client, tenant_factory, user_factory):
    """
    Testa que login com credenciais válidas retorna JWT.
    Protege: fluxo de autenticação básico.
    """
    tenant = tenant_factory()
    password = "TestPassword@123"
    user_factory(
        tenant_id=tenant.id,
        email="login@test.com",
        password=password
    )
    
    response = client.post(
        "/auth/login-multitenant",
        json={"email": "login@test.com", "password": password}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_returns_short_access_token_and_refresh_token(client, tenant_factory, user_factory):
    """
    Testa que login usa access token curto e refresh token separado.
    Protege: reducao de janela de uso de token roubado.
    """
    tenant = tenant_factory()
    password = "TestPassword@123"
    user_factory(
        tenant_id=tenant.id,
        email="short-token@test.com",
        password=password
    )

    response = client.post(
        "/auth/login-multitenant",
        json={"email": "short-token@test.com", "password": password}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["expires_in"] <= 20 * 60

    access_payload = _jwt_payload(data["access_token"])
    refresh_payload = _jwt_payload(data["refresh_token"])

    assert access_payload["typ"] == "access"
    assert refresh_payload["typ"] == "refresh"
    assert _seconds_until_exp(access_payload) <= 20 * 60
    assert refresh_payload["jti"] == access_payload["jti"]
    assert refresh_payload["exp"] > access_payload["exp"]


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
    
    response = _login_and_select_tenant(
        client,
        "jwt@test.com",
        password,
        tenant.id,
    )
    
    assert response.status_code == 200
    token = response.json()["access_token"]
    
    payload = _jwt_payload(token)
    
    assert "tenant_id" in payload
    assert payload["tenant_id"] == str(tenant.id)
    assert payload["sub"] == str(user.id)


def test_refresh_token_renews_selected_tenant_access_token(client, tenant_factory, user_factory):
    """
    Testa que refresh token renova access token mantendo tenant selecionado.
    Protege: renovacao automatica sem perder contexto multi-tenant.
    """
    tenant = tenant_factory(nome="Tenant Refresh Test")
    password = "Pass@123"
    user = user_factory(
        tenant_id=tenant.id,
        email="refresh@test.com",
        password=password
    )

    select_response = _login_and_select_tenant(
        client,
        "refresh@test.com",
        password,
        tenant.id,
    )
    assert select_response.status_code == 200
    selected_data = select_response.json()
    assert selected_data["refresh_token"]

    refresh_response = client.post(
        "/auth/refresh",
        json={"refresh_token": selected_data["refresh_token"]},
    )

    assert refresh_response.status_code == 200
    refreshed = refresh_response.json()
    assert refreshed["access_token"]
    assert refreshed["refresh_token"]
    assert refreshed["expires_in"] <= 20 * 60

    access_payload = _jwt_payload(refreshed["access_token"])
    refresh_payload = _jwt_payload(refreshed["refresh_token"])
    assert access_payload["typ"] == "access"
    assert refresh_payload["typ"] == "refresh"
    assert access_payload["sub"] == str(user.id)
    assert access_payload["tenant_id"] == str(tenant.id)
    assert refresh_payload["tenant_id"] == str(tenant.id)


def test_refresh_token_cannot_access_protected_routes(client, tenant_factory, user_factory):
    """
    Testa que refresh token nao funciona como bearer de API.
    Protege: separacao entre credencial de renovacao e acesso.
    """
    tenant = tenant_factory(nome="Tenant Refresh Bearer Test")
    password = "Pass@123"
    user_factory(
        tenant_id=tenant.id,
        email="refresh-bearer@test.com",
        password=password
    )

    select_response = _login_and_select_tenant(
        client,
        "refresh-bearer@test.com",
        password,
        tenant.id,
    )
    assert select_response.status_code == 200
    refresh_token = select_response.json()["refresh_token"]

    response = client.get(
        "/auth/me-multitenant",
        headers={"Authorization": f"Bearer {refresh_token}"},
    )

    assert response.status_code == 401


def test_refresh_fails_after_logout(client, tenant_factory, user_factory):
    """
    Testa que logout revoga tambem a capacidade de renovar tokens.
    Protege: logout efetivo da sessao.
    """
    tenant = tenant_factory(nome="Tenant Refresh Logout Test")
    password = "Pass@123"
    user_factory(
        tenant_id=tenant.id,
        email="refresh-logout@test.com",
        password=password
    )

    select_response = _login_and_select_tenant(
        client,
        "refresh-logout@test.com",
        password,
        tenant.id,
    )
    assert select_response.status_code == 200
    selected_data = select_response.json()

    logout_response = client.post(
        "/auth/logout-multitenant",
        headers={"Authorization": f"Bearer {selected_data['access_token']}"},
    )
    assert logout_response.status_code == 200

    refresh_response = client.post(
        "/auth/refresh",
        json={"refresh_token": selected_data["refresh_token"]},
    )

    assert refresh_response.status_code == 401


def test_login_with_invalid_credentials_fails(client, tenant_factory, user_factory):
    """
    Testa que login com credenciais inválidas falha.
    Protege: segurança de autenticação.
    """
    tenant = tenant_factory()
    user_factory(
        tenant_id=tenant.id,
        email="valid@test.com",
        password="CorrectPassword@123"
    )
    
    response = client.post(
        "/auth/login-multitenant",
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
    payload = _jwt_payload(token)
    
    assert payload["tenant_id"] == str(tenant.id)
    assert payload["sub"] == str(user.id)
    assert payload["exp"] > datetime.utcnow().timestamp()
