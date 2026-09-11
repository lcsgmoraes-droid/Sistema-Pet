from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.intnfe.client import IntNFeError
from app.intnfe.service import activate
from tests.unit import test_intnfe_activation as activation_fixtures

http_pilot = activation_fixtures.http_pilot
intnfe_db = activation_fixtures.intnfe_db
pilot = activation_fixtures.pilot


def certificate(cnpj=activation_fixtures.CNPJ, days=365):
    now = datetime.now(timezone.utc)
    return {
        "razaoSocial": "Loja Teste Ltda",
        "cnpj": cnpj,
        "thumbprint": "ficticio",
        "nomeArquivo": "empresa.pfx",
        "validoDe": (now - timedelta(days=1)).isoformat(),
        "validoAte": (now + timedelta(days=days)).isoformat(),
        "diasParaExpirar": days,
        "expirado": days < 0,
        "atualizadoEm": now.isoformat(),
    }


class Store:
    def __init__(self):
        self.value = None
        self.uploads = []
        self.error = None

    def read(self, token, emitter):
        assert token == "token-integrador-ficticio"
        assert emitter == "emitente-teste"
        return deepcopy(self.value)

    def upload(self, token, emitter, *, filename, content, password):
        assert token == "token-integrador-ficticio"
        assert emitter == "emitente-teste"
        self.uploads.append((filename, content, password))
        if self.error:
            raise self.error
        self.value = certificate()
        return deepcopy(self.value)


@pytest.fixture
def store(pilot):
    activate(pilot.db, pilot.id, pilot.api)
    result = Store()
    pilot.api.emitter_certificate = result.read
    pilot.api.upload_emitter_certificate = result.upload
    return result


def test_uploads_a1_inside_corepet_and_never_returns_or_audits_password(
    store, http_pilot
):
    client, access, _app = http_pilot
    response = client.post(
        "/intnfe/certificado",
        files={
            "arquivo": ("empresa.pfx", b"certificado-ficticio", "application/x-pkcs12")
        },
        data={"senha": "senha-ficticia"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["situacao"] == "valido"
    assert store.uploads == [("empresa.pfx", b"certificado-ficticio", "senha-ficticia")]
    assert "senha-ficticia" not in response.text
    assert "senha-ficticia" not in str(access["audits"])
    assert [item["new_value"]["resultado"] for item in access["audits"]] == [
        "solicitado",
        "confirmado",
    ]


@pytest.mark.parametrize(
    "filename,content,password",
    [
        ("empresa.txt", b"certificado", "senha"),
        ("empresa.pfx", b"", "senha"),
        ("empresa.p12", b"certificado", ""),
        ("empresa.pfx", b"x" * (512 * 1024 + 1), "senha"),
    ],
    ids=["extension", "empty", "password", "size"],
)
def test_invalid_upload_never_reaches_provider(
    store, http_pilot, filename, content, password
):
    client, _access, _app = http_pilot
    response = client.post(
        "/intnfe/certificado",
        files={"arquivo": (filename, content, "application/octet-stream")},
        data={"senha": password},
    )
    assert response.status_code == 422
    assert store.uploads == []


def test_expiry_warning_is_returned_without_certificate_bytes(store, http_pilot):
    client, _access, _app = http_pilot
    store.value = certificate(days=20)
    response = client.get("/intnfe/certificado")
    assert response.status_code == 200
    assert response.json()["situacao"] == "expirando"
    assert response.json()["alerta_vencimento"] is True
    assert 19 <= response.json()["dias_para_expirar"] <= 20
    assert "thumbprint" not in response.json()
    assert "nomeArquivo" not in response.json()


def test_provider_rejection_is_safe_and_does_not_retry(store, http_pilot):
    client, access, _app = http_pilot
    store.error = IntNFeError(
        "CnpjDivergente", status=422, correlation="protocolo-ficticio"
    )
    response = client.post(
        "/intnfe/certificado",
        files={"arquivo": ("empresa.pfx", b"certificado", "application/x-pkcs12")},
        data={"senha": "senha-ficticia"},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["codigo"] == "CnpjDivergente"
    assert len(store.uploads) == 1
    assert access["audits"][-1]["new_value"]["resultado"] == "recusado"
    assert "senha-ficticia" not in response.text + str(access["audits"])


def test_audit_failure_before_upload_prevents_transmission(
    store, http_pilot, monkeypatch
):
    from app.intnfe import routes

    client, _access, _app = http_pilot

    def fail(*_args, **_kwargs):
        raise SQLAlchemyError("falha-local-ficticia")

    monkeypatch.setattr(routes, "log_action", fail)
    response = client.post(
        "/intnfe/certificado",
        files={"arquivo": ("empresa.pfx", b"certificado", "application/x-pkcs12")},
        data={"senha": "senha-ficticia"},
    )
    assert response.status_code == 503
    assert response.json()["detail"]["codigo"] == "AuditoriaIndisponivel"
    assert store.uploads == []
