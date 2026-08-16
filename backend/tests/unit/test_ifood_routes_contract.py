from fastapi import status

from app.integrations.ifood.client import IfoodClientError
from app.routes.ifood_integration_routes import _provider_http_status


def test_provider_auth_failure_is_not_exposed_as_corepet_session_failure():
    error = IfoodClientError("credenciais recusadas", status_code=401)

    assert _provider_http_status(error) == status.HTTP_502_BAD_GATEWAY


def test_provider_rate_limit_is_preserved_for_retry_feedback():
    error = IfoodClientError("limite atingido", status_code=429)

    assert _provider_http_status(error) == status.HTTP_429_TOO_MANY_REQUESTS
