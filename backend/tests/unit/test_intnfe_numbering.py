from copy import deepcopy
from uuid import uuid4

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.intnfe.client import IntNFeError
from app.intnfe.service import activate
from tests.unit import test_intnfe_activation as activation_fixtures

http_pilot = activation_fixtures.http_pilot
intnfe_db = activation_fixtures.intnfe_db
pilot = activation_fixtures.pilot


def row(serie="003", last=1, environment=2, model=55):
    return {
        "serie": serie,
        "modelo": model,
        "ambienteCodigo": environment,
        "ultimoNumero": last,
        "proximoNumero": last + 1,
    }


def body(**changes):
    return {
        "serie": "003",
        "ambiente_codigo": 2,
        "modelo": 55,
        "proximo_numero": 4501,
        "ultimo_numero_consultado": 1,
        **changes,
    }


class Store:
    def __init__(self):
        self.rows = [row(), row(last=20, environment=1), row(last=7, model=65)]
        self.writes = []
        self.reads = []
        self.error = None
        self.read_error = None
        self.fail_after_write = False
        self.advance_after_write = 0

    def read(self, token, emitter):
        assert token == "token-integrador-ficticio"
        self.reads.append(emitter)
        if self.read_error or (self.writes and self.fail_after_write):
            raise IntNFeError("NaoEncontrado", status=404)
        return deepcopy(self.rows)

    def write(self, token, emitter, payload):
        assert token == "token-integrador-ficticio"
        assert emitter == "emitente-teste"
        self.writes.append(deepcopy(payload))
        if self.error:
            raise self.error

        def match(r):
            return int(r["serie"]), r["modelo"], r["ambienteCodigo"]

        self.rows = [r for r in self.rows if match(r) != match(payload)]
        self.rows.append(
            row(
                payload["serie"],
                payload["ultimoNumero"] + self.advance_after_write,
                payload["ambienteCodigo"],
                payload["modelo"],
            )
        )
        return {
            "serie": payload["serie"],
            "modelo": payload["modelo"],
            "ambienteCodigo": payload["ambienteCodigo"],
            "proximoNumero": payload["ultimoNumero"] + 1,
        }


@pytest.fixture
def store(pilot):
    activate(pilot.db, pilot.id, pilot.api)
    result = Store()
    pilot.api.numbering = result.read
    pilot.api.set_numbering = result.write
    return result


@pytest.mark.parametrize("environment,last", [(1, 20), (2, 1)])
def test_save_converts_next_and_preserves_other_sequences(
    store, http_pilot, environment, last
):
    client, access, _app = http_pilot
    before = deepcopy(store.rows)
    response = client.put(
        "/intnfe/numeracao",
        json=body(ambiente_codigo=environment, ultimo_numero_consultado=last),
    )
    assert response.status_code == 200, response.text
    assert store.writes == [
        {
            "serie": "3",
            "ultimoNumero": 4500,
            "ambienteCodigo": environment,
            "modelo": 55,
        }
    ]
    assert store.reads == ["emitente-teste", "emitente-teste"]
    for previous in before:
        if previous["ambienteCodigo"] != environment or previous["modelo"] != 55:
            assert previous in store.rows
    assert [item["new_value"]["resultado"] for item in access["audits"]] == [
        "solicitado",
        "confirmado",
    ]
    assert access["audits"][0]["old_value"] == {"ultimoNumero": last}
    assert "segredo" not in response.text + str(access["audits"])


def test_read_normalizes_series_and_status_enables_numbering(store, http_pilot):
    client, _access, _app = http_pilot
    assert client.get("/intnfe/status").json()["pode_configurar_numeracao"] is True
    response = client.get("/intnfe/numeracao")
    assert response.status_code == 200
    assert response.json()["series"][0]["serie"] == "3"
    assert store.writes == []


@pytest.mark.parametrize("next_number", [1, 2])
def test_equal_or_backward_sequence_never_sends_put(store, http_pilot, next_number):
    client, _access, _app = http_pilot
    response = client.put("/intnfe/numeracao", json=body(proximo_numero=next_number))
    assert response.status_code == 422
    assert response.json()["detail"]["codigo"] == "NumeracaoRetrocede"
    assert store.writes == []


def test_stale_screen_requires_refresh_before_any_write(store, http_pilot):
    client, _access, _app = http_pilot
    store.rows[0] = row(last=3)
    response = client.put("/intnfe/numeracao", json=body())
    assert response.status_code == 409
    assert response.json()["detail"]["codigo"] == "NumeracaoAlterada"
    assert response.json()["detail"]["exige_consulta"] is True
    assert store.writes == []


def test_new_series_zero_can_start_above_one(store, http_pilot):
    client, _access, _app = http_pilot
    response = client.put(
        "/intnfe/numeracao", json=body(serie="000", ultimo_numero_consultado=0)
    )
    assert response.status_code == 200
    assert store.writes[0]["serie"] == "0"
    assert store.writes[0]["ultimoNumero"] == 4500


@pytest.mark.parametrize(
    "changes",
    [
        {"serie": "900"},
        {"serie": "890"},
        {"serie": "-1"},
        {"serie": "3.0"},
        {"ambiente_codigo": 3},
        {"ambiente_codigo": True},
        {"modelo": 65},
        {"modelo": 55.0},
        {"proximo_numero": 0},
        {"proximo_numero": "4501"},
        {"proximo_numero": 4.5},
        {"proximo_numero": 1000000000},
        {"ultimo_numero_consultado": -1},
        {"tenant_id": "outra-empresa"},
        {"emitente_id": "outro-emissor"},
    ],
)
def test_invalid_or_cross_tenant_payload_cannot_reach_remote(
    store, http_pilot, changes
):
    client, _access, _app = http_pilot
    response = client.put("/intnfe/numeracao", json=body(**changes))
    assert response.status_code == 422
    assert store.writes == [] and store.reads == []


@pytest.mark.parametrize(
    "mode", ["unlinked", "changed_cnpj", "disabled", "remote_changed", "other_tenant"]
)
def test_invalid_context_blocks_read_and_write(
    pilot, store, http_pilot, monkeypatch, mode
):
    from app.auth.dependencies import get_current_user_and_tenant
    from types import SimpleNamespace

    client, _access, app = http_pilot
    if mode == "unlinked":
        from app.intnfe.repository import get_connection

        connection = get_connection(pilot.db, pilot.id)
        connection.client_secret_encrypted = None
    elif mode == "changed_cnpj":
        pilot.tenant.cnpj = "11444777000161"
    elif mode == "disabled":
        monkeypatch.setattr(settings, "INTNFE_ACTIVATION_ENABLED", False)
    elif mode == "remote_changed":
        pilot.api.emitters[0]["tenantId"] = "novo-vinculo"
    else:

        async def other_context():
            return SimpleNamespace(id=7), uuid4()

        app.dependency_overrides[get_current_user_and_tenant] = other_context
        # Permission mocked separately: test service/ORM tenant isolation here.
        from app.security import permissions_decorator

        monkeypatch.setattr(
            permissions_decorator, "check_permission", lambda *_a, **_kw: None
        )
    pilot.db.commit()
    assert client.get("/intnfe/numeracao").status_code in {404, 409}
    assert client.put("/intnfe/numeracao", json=body()).status_code in {404, 409}
    assert store.writes == [] and store.reads == []


def test_permission_and_auth_required_for_both_routes(store, http_pilot):
    from app.auth.dependencies import get_current_user_and_tenant

    client, access, app = http_pilot
    access["allowed"] = False
    assert client.get("/intnfe/numeracao").status_code == 403
    assert client.put("/intnfe/numeracao", json=body()).status_code == 403
    access["allowed"] = True
    del app.dependency_overrides[get_current_user_and_tenant]
    assert client.get("/intnfe/numeracao").status_code in {401, 403}
    assert client.put("/intnfe/numeracao", json=body()).status_code in {401, 403}
    assert store.writes == [] and store.reads == []


@pytest.mark.parametrize(
    "code,status,uncertain,expected",
    [
        ("NumeracaoRetrocede", 422, False, 422),
        ("NaoEncontrado", 404, False, 404),
        ("EmissorIndisponivel", 503, True, 503),
    ],
)
def test_remote_race_and_uncertain_write_require_query_without_retry(
    store, http_pilot, code, status, uncertain, expected
):
    client, access, _app = http_pilot
    store.error = IntNFeError(
        code, status=status, uncertain=uncertain, correlation="protocolo-ficticio"
    )
    response = client.put("/intnfe/numeracao", json=body())
    assert response.status_code == expected
    assert response.json()["detail"]["exige_consulta"] is True
    assert response.json()["detail"]["protocolo_suporte"] == "protocolo-ficticio"
    assert len(store.writes) == 1
    assert access["audits"][-1]["new_value"]["resultado"] == (
        "nao_confirmado" if uncertain else "recusado"
    )


def test_failed_readback_of_accepted_put_remains_uncertain(store, http_pilot):
    client, _access, _app = http_pilot
    store.fail_after_write = True
    response = client.put("/intnfe/numeracao", json=body())
    assert response.status_code == 503
    assert response.json()["detail"]["codigo"] == "ResultadoNaoConfirmado"
    assert len(store.writes) == 1
    store.fail_after_write = False
    # Reenvio antigo tampouco pode avançar novamente; GET permite conciliar.
    assert client.put("/intnfe/numeracao", json=body()).status_code == 409
    assert len(store.writes) == 1
    assert any(
        r["proximoNumero"] == 4501
        for r in client.get("/intnfe/numeracao").json()["series"]
    )


def test_new_emission_after_adjustment_returns_latest_remote_number(store, http_pilot):
    client, _access, _app = http_pilot
    store.advance_after_write = 1
    response = client.put("/intnfe/numeracao", json=body())
    assert response.status_code == 200
    assert any(r["proximoNumero"] == 4502 for r in response.json()["series"])


def test_invalid_remote_listing_does_not_look_like_unused_series(store, http_pilot):
    client, _access, _app = http_pilot
    store.rows[0]["proximoNumero"] = 1  # nao corresponde ao ultimoNumero
    assert client.get("/intnfe/numeracao").status_code == 503
    assert client.put("/intnfe/numeracao", json=body()).status_code == 503
    assert store.writes == []


def test_audit_failure_before_write_prevents_adjustment(store, http_pilot, monkeypatch):
    from app.intnfe import routes

    client, _access, _app = http_pilot

    def fail(*_a, **_kw):
        raise SQLAlchemyError("falha-local-ficticia")

    monkeypatch.setattr(routes, "log_action", fail)
    response = client.put("/intnfe/numeracao", json=body())
    assert response.status_code == 503
    assert response.json()["detail"]["codigo"] == "AuditoriaIndisponivel"
    assert store.writes == []


@pytest.mark.parametrize(
    "result",
    [
        {"serie": []},
        {"serie": "3", "modelo": 55, "ambienteCodigo": True, "proximoNumero": 4501},
        [],
    ],
)
def test_malformed_put_acknowledgement_is_uncertain(pilot, store, http_pilot, result):
    client, _access, _app = http_pilot

    def malformed(token, emitter, payload):
        store.write(token, emitter, payload)
        return result

    pilot.api.set_numbering = malformed
    response = client.put("/intnfe/numeracao", json=body())
    assert response.status_code == 503
    assert response.json()["detail"]["codigo"] == "ResultadoNaoConfirmado"
    assert len(store.writes) == 1
