from copy import deepcopy

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.intnfe.client import IntNFeError
from app.intnfe.service import activate
from tests.unit import test_intnfe_activation as activation_fixtures

http_pilot = activation_fixtures.http_pilot
intnfe_db = activation_fixtures.intnfe_db
pilot = activation_fixtures.pilot


def body(**changes):
    return {
        "ambiente_codigo": 2,
        "csc_id": "000001",
        "csc": "codigo-csc-ficticio",
        "csc_id_consultado": None,
        "confirmar_substituicao": False,
        **changes,
    }


class Store:
    def __init__(self):
        self.state = {
            "temCscHomologacao": False,
            "cscIdHomologacao": None,
            "temCscProducao": False,
            "cscIdProducao": None,
        }
        self.reads = []
        self.writes = []
        self.error = None
        self.fail_after_write = False

    def read(self, token, emitter):
        assert token == "token-integrador-ficticio"
        self.reads.append(emitter)
        if self.writes and self.fail_after_write:
            raise IntNFeError("EmissorIndisponivel", status=503)
        return deepcopy(self.state)

    def write(self, token, emitter, payload):
        assert token == "token-integrador-ficticio"
        assert emitter == "emitente-teste"
        self.writes.append(deepcopy(payload))
        if self.error:
            raise self.error
        suffix = "Producao" if payload["ambienteCodigo"] == 1 else "Homologacao"
        self.state[f"temCsc{suffix}"] = True
        self.state[f"cscId{suffix}"] = payload["cscId"]


@pytest.fixture
def store(pilot):
    activate(pilot.db, pilot.id, pilot.api)
    result = Store()
    pilot.api.csc = result.read
    pilot.api.set_csc = result.write
    return result


def test_reads_and_saves_homologation_csc_without_exposing_secret(store, http_pilot):
    client, access, _app = http_pilot
    response = client.get("/intnfe/csc")
    assert response.status_code == 200
    assert response.json() == {
        "ambientes": [
            {
                "ambiente_codigo": 2,
                "ambiente": "homologacao",
                "tem_csc": False,
                "csc_id": None,
            },
            {
                "ambiente_codigo": 1,
                "ambiente": "producao",
                "tem_csc": False,
                "csc_id": None,
            },
        ]
    }

    response = client.put("/intnfe/csc", json=body())
    assert response.status_code == 200, response.text
    assert response.json()["ambientes"][0]["tem_csc"] is True
    assert response.json()["ambientes"][0]["csc_id"] == "000001"
    assert "codigo-csc-ficticio" not in response.text
    assert store.writes == [
        {
            "cscId": "000001",
            "csc": "codigo-csc-ficticio",
            "ambienteCodigo": 2,
        }
    ]
    assert [item["new_value"]["resultado"] for item in access["audits"]] == [
        "solicitado",
        "confirmado",
    ]
    assert "codigo-csc-ficticio" not in str(access["audits"])


def test_existing_csc_requires_explicit_replacement(store, http_pilot):
    client, _access, _app = http_pilot
    store.state.update({"temCscHomologacao": True, "cscIdHomologacao": "000001"})
    request = body(csc_id_consultado="000001")
    response = client.put("/intnfe/csc", json=request)
    assert response.status_code == 422
    assert response.json()["detail"]["codigo"] == "SubstituicaoNaoConfirmada"
    assert store.writes == []

    request["confirmar_substituicao"] = True
    assert client.put("/intnfe/csc", json=request).status_code == 200
    assert len(store.writes) == 1


def test_stale_csc_screen_requires_refresh(store, http_pilot):
    client, _access, _app = http_pilot
    store.state.update({"temCscHomologacao": True, "cscIdHomologacao": "000002"})
    response = client.put(
        "/intnfe/csc",
        json=body(csc_id_consultado="000001", confirmar_substituicao=True),
    )
    assert response.status_code == 409
    assert response.json()["detail"]["codigo"] == "CscAlterado"
    assert store.writes == []


@pytest.mark.parametrize(
    "changes",
    [
        {"ambiente_codigo": 3},
        {"ambiente_codigo": True},
        {"ambiente_codigo": "2"},
        {"csc_id": ""},
        {"csc_id": "../outro"},
        {"csc": ""},
        {"confirmar_substituicao": "true"},
        {"tenant_id": "outra-empresa"},
    ],
)
def test_invalid_payload_never_reaches_provider(store, http_pilot, changes):
    client, _access, _app = http_pilot
    secret = "codigo-csc-ficticio"
    response = client.put("/intnfe/csc", json=body(**changes))
    assert response.status_code == 422
    assert secret not in response.text
    assert store.reads == [] and store.writes == []


def test_production_csc_is_saved_without_changing_homologation(store, http_pilot):
    client, access, _app = http_pilot
    store.state.update({"temCscHomologacao": True, "cscIdHomologacao": "homologacao-1"})

    response = client.put(
        "/intnfe/csc",
        json=body(ambiente_codigo=1, csc_id="producao-1"),
    )

    assert response.status_code == 200, response.text
    assert store.writes == [
        {
            "cscId": "producao-1",
            "csc": "codigo-csc-ficticio",
            "ambienteCodigo": 1,
        }
    ]
    assert response.json()["ambientes"] == [
        {
            "ambiente_codigo": 2,
            "ambiente": "homologacao",
            "tem_csc": True,
            "csc_id": "homologacao-1",
        },
        {
            "ambiente_codigo": 1,
            "ambiente": "producao",
            "tem_csc": True,
            "csc_id": "producao-1",
        },
    ]
    assert access["audits"][0]["old_value"] == {
        "cscId": None,
        "ambienteCodigo": 1,
    }


def test_write_that_changes_other_environment_is_not_confirmed(
    pilot, store, http_pilot
):
    client, _access, _app = http_pilot
    store.state.update({"temCscProducao": True, "cscIdProducao": "producao-existente"})
    original_write = store.write

    def overwrite_both(token, emitter, payload):
        original_write(token, emitter, payload)
        store.state.update({"temCscProducao": False, "cscIdProducao": None})

    pilot.api.set_csc = overwrite_both
    response = client.put("/intnfe/csc", json=body())

    assert response.status_code == 503
    assert response.json()["detail"]["codigo"] == "ResultadoNaoConfirmado"
    assert len(store.writes) == 1


@pytest.mark.parametrize(
    "remote_state",
    [
        {"temCsc": True, "cscId": "formato-legado"},
        {
            "temCscHomologacao": True,
            "cscIdHomologacao": None,
            "temCscProducao": False,
            "cscIdProducao": None,
        },
        {
            "temCscHomologacao": "true",
            "cscIdHomologacao": "000001",
            "temCscProducao": False,
            "cscIdProducao": None,
        },
    ],
)
def test_invalid_remote_state_is_blocked(store, http_pilot, remote_state):
    client, _access, _app = http_pilot
    store.state = remote_state

    response = client.get("/intnfe/csc")

    assert response.status_code == 503
    assert response.json()["detail"]["codigo"] == "RespostaInvalida"
    assert store.writes == []


def test_permission_and_auth_are_required(store, http_pilot):
    from app.auth.dependencies import get_current_user_and_tenant

    client, access, app = http_pilot
    access["allowed"] = False
    assert client.get("/intnfe/csc").status_code == 403
    assert client.put("/intnfe/csc", json=body()).status_code == 403
    access["allowed"] = True
    del app.dependency_overrides[get_current_user_and_tenant]
    assert client.get("/intnfe/csc").status_code in {401, 403}
    assert client.put("/intnfe/csc", json=body()).status_code in {401, 403}
    assert store.writes == []


def test_uncertain_write_is_not_retried_and_requires_query(store, http_pilot):
    client, access, _app = http_pilot
    store.error = IntNFeError(
        "EmissorIndisponivel",
        status=503,
        uncertain=True,
        correlation="protocolo-ficticio",
    )
    response = client.put("/intnfe/csc", json=body())
    assert response.status_code == 503
    assert response.json()["detail"]["codigo"] == "ResultadoNaoConfirmado"
    assert response.json()["detail"]["exige_consulta"] is True
    assert len(store.writes) == 1
    assert access["audits"][-1]["new_value"]["resultado"] == "nao_confirmado"


def test_audit_failure_before_write_prevents_csc_change(store, http_pilot, monkeypatch):
    from app.intnfe import routes

    client, _access, _app = http_pilot

    def fail(*_args, **_kwargs):
        raise SQLAlchemyError("falha-local-ficticia")

    monkeypatch.setattr(routes, "log_action", fail)
    response = client.put("/intnfe/csc", json=body())
    assert response.status_code == 503
    assert response.json()["detail"]["codigo"] == "AuditoriaIndisponivel"
    assert store.writes == []
