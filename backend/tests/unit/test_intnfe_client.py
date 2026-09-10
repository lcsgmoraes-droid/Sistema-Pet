from unittest.mock import Mock

import pytest
import requests
from pydantic import SecretStr

from app.config import settings
from app.intnfe.client import BASE_URL, IntNFeClient, IntNFeError


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setattr(settings, "INTNFE_ACTIVATION_ENABLED", True)
    monkeypatch.setattr(settings, "INTNFE_INTEGRADOR_ID", "integrador-teste")
    monkeypatch.setattr(
        settings, "INTNFE_INTEGRADOR_SECRET", SecretStr("segredo-integrador-ficticio")
    )
    return IntNFeClient(session=Mock())


def response(status=200, body=None):
    result = Mock(status_code=status, headers={"X-Correlation-Id": "diagnostico-123"})
    result.json.return_value = body
    return result


def test_authentication_uses_fixed_origin_without_redirect_or_retry(api):
    api.session.request.return_value = response(body={"accessToken": "token-ficticio"})
    assert api.integrator_token() == "token-ficticio"
    api.session.request.assert_called_once_with(
        "POST",
        BASE_URL + "/integrador/auth/token",
        json={
            "integradorId": "integrador-teste",
            "integradorSecret": "segredo-integrador-ficticio",
        },
        headers={"Accept": "application/json"},
        timeout=(3, 15),
        allow_redirects=False,
    )


@pytest.mark.parametrize(
    "status,uncertain",
    [
        (409, False),
        (422, False),
        (401, False),
        (429, False),
        (500, True),
        (503, True),
        (408, True),
    ],
)
def test_creation_failure_classification_is_safe(api, status, uncertain):
    api.session.request.return_value = response(
        status, {"mensagem": "segredo-nao-deve-vazar"}
    )
    with pytest.raises(IntNFeError) as error:
        api.create_emitter("token", {"cnpj": "11222333000181"})
    assert error.value.uncertain == uncertain
    assert error.value.status == status
    assert "segredo-nao-deve-vazar" not in str(error.value)
    assert error.value.correlation == "diagnostico-123"
    assert api.session.request.call_count == 1


def test_timeout_or_invalid_success_response_is_uncertain_for_creation(api):
    api.session.request.side_effect = requests.Timeout("mensagem-privada")
    with pytest.raises(IntNFeError) as error:
        api.create_emitter("token", {})
    assert error.value.uncertain
    assert "mensagem-privada" not in str(error.value)
    api.session.request.side_effect = None
    api.session.request.return_value = response(201, {"tenantId": "id-sem-segredo"})
    with pytest.raises(IntNFeError) as error:
        api.create_emitter("token", {})
    assert error.value.uncertain


def test_invalid_listing_does_not_become_empty_list(api):
    api.session.request.return_value = response(200, {"error": "resposta-alterada"})
    with pytest.raises(IntNFeError, match="RespostaInvalida"):
        api.list_emitters("token")


def test_missing_certificate_is_an_explicit_pending_step(api):
    api.session.request.return_value = response(404, {})
    assert api.certificate("token") is None


def test_disabled_integration_does_not_open_network(monkeypatch):
    monkeypatch.setattr(settings, "INTNFE_ACTIVATION_ENABLED", False)
    with pytest.raises(IntNFeError, match="IntegracaoNaoConfigurada"):
        IntNFeClient(session=Mock())
