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


def test_numbering_uses_integrator_get_and_put_with_exact_body(api):
    api.session.request.return_value = response(body=[])
    assert api.numbering("token", "emitente-teste") == []
    assert api.session.request.call_args.args == (
        "GET",
        BASE_URL + "/integrador/emitentes/emitente-teste/numeracao",
    )
    payload = {"serie": "3", "ultimoNumero": 4500, "ambienteCodigo": 1, "modelo": 55}
    api.session.request.return_value = response(body={"proximoNumero": 4501})
    api.set_numbering("token", "emitente-teste", payload)
    assert api.session.request.call_args.args == (
        "PUT",
        BASE_URL + "/integrador/emitentes/emitente-teste/numeracao",
    )
    assert api.session.request.call_args.kwargs["json"] == payload
    assert api.session.request.call_args.kwargs["allow_redirects"] is False


def test_numbering_error_only_exposes_allowlisted_code(api):
    api.session.request.return_value = response(
        422, {"erro": "NumeracaoRetrocede", "mensagem": "segredo-nao-expor"}
    )
    with pytest.raises(IntNFeError) as error:
        api.set_numbering("token", "emitente-teste", {})
    assert error.value.code == "NumeracaoRetrocede"
    assert not error.value.uncertain
    assert "segredo" not in str(error.value)


def test_numbering_timeout_is_uncertain_and_never_retries(api):
    api.session.request.side_effect = requests.Timeout("nao-expor")
    with pytest.raises(IntNFeError) as error:
        api.set_numbering("token", "emitente-teste", {})
    assert error.value.uncertain
    assert api.session.request.call_count == 1


def test_numbering_invalid_path_is_rejected_before_network(api):
    with pytest.raises(IntNFeError):
        api.numbering("token", "../outra-rota?tenant=outro")
    assert api.session.request.call_count == 0


def test_csc_uses_integrator_get_and_put_without_expecting_secret_back(api):
    api.session.request.return_value = response(
        body={
            "temCscHomologacao": True,
            "cscIdHomologacao": "000001",
            "temCscProducao": False,
            "cscIdProducao": None,
        }
    )
    assert api.csc("token", "emitente-teste") == {
        "temCscHomologacao": True,
        "cscIdHomologacao": "000001",
        "temCscProducao": False,
        "cscIdProducao": None,
    }
    assert api.session.request.call_args.args == (
        "GET",
        BASE_URL + "/integrador/emitentes/emitente-teste/csc",
    )

    payload = {
        "cscId": "000001",
        "csc": "codigo-ficticio",
        "ambienteCodigo": 2,
    }
    api.session.request.return_value = response(status=204)
    assert api.set_csc("token", "emitente-teste", payload) is None
    assert api.session.request.call_args.args == (
        "PUT",
        BASE_URL + "/integrador/emitentes/emitente-teste/csc",
    )
    assert api.session.request.call_args.kwargs["json"] == payload


def test_csc_write_requires_documented_empty_response(api):
    api.session.request.return_value = response(
        status=200, body={"csc": "codigo-nao-deve-voltar"}
    )
    with pytest.raises(IntNFeError) as error:
        api.set_csc("token", "emitente-teste", {})
    assert error.value.code == "RespostaInvalida"
    assert error.value.uncertain
    assert "codigo-nao-deve-voltar" not in str(error.value)


def test_csc_invalid_path_is_rejected_before_network(api):
    with pytest.raises(IntNFeError):
        api.csc("token", "../outro-emissor")
    assert api.session.request.call_count == 0


def test_certificate_upload_uses_integrator_multipart_without_json(api):
    api.session.request.return_value = response(
        body={
            "cnpj": "11222333000181",
            "validoDe": "2026-01-01T00:00:00Z",
            "validoAte": "2027-01-01T00:00:00Z",
            "expirado": False,
        }
    )

    api.upload_emitter_certificate(
        "token",
        "emitente-teste",
        filename="empresa.pfx",
        content=b"certificado-ficticio",
        password="senha-ficticia",
    )

    call = api.session.request.call_args
    assert call.args == (
        "POST",
        BASE_URL + "/integrador/emitentes/emitente-teste/certificado",
    )
    assert "json" not in call.kwargs
    assert call.kwargs["data"] == {"Senha": "senha-ficticia"}
    assert call.kwargs["files"]["Arquivo"] == (
        "empresa.pfx",
        b"certificado-ficticio",
        "application/x-pkcs12",
    )
    assert call.kwargs["allow_redirects"] is False


def test_certificate_error_only_exposes_allowlisted_code(api):
    api.session.request.return_value = response(
        422, {"erro": "CnpjDivergente", "mensagem": "senha-nao-deve-vazar"}
    )
    with pytest.raises(IntNFeError) as error:
        api.upload_emitter_certificate(
            "token",
            "emitente-teste",
            filename="empresa.pfx",
            content=b"certificado-ficticio",
            password="senha-ficticia",
        )
    assert error.value.code == "CnpjDivergente"
    assert "senha" not in str(error.value)


def test_fiscal_profile_uses_integrator_get_and_patch(api):
    remote = {
        "razaoSocial": "Loja Teste Ltda",
        "inscricaoEstadual": "123",
        "crt": "1",
        "endereco": {"codigoMunicipio": "3550308"},
    }
    api.session.request.return_value = response(body=remote)
    assert api.fiscal_registration("token", "emitente-teste") == remote
    assert api.session.request.call_args.args == (
        "GET",
        BASE_URL + "/integrador/emitentes/emitente-teste/cadastro",
    )

    api.session.request.return_value = response(body=remote)
    assert api.set_fiscal_registration("token", "emitente-teste", remote) == remote
    assert api.session.request.call_args.args == (
        "PATCH",
        BASE_URL + "/integrador/emitentes/emitente-teste/cadastro",
    )
    assert api.session.request.call_args.kwargs["json"] == remote
