from copy import deepcopy

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.empresa_config_fiscal_models import EmpresaConfigFiscal
from app.intnfe.client import IntNFeError
from app.intnfe.service import activate
from tests.unit import test_intnfe_activation as activation_fixtures

http_pilot = activation_fixtures.http_pilot
intnfe_db = activation_fixtures.intnfe_db
pilot = activation_fixtures.pilot


class Store:
    def __init__(self):
        self.value = None
        self.writes = []
        self.error = None

    def read(self, token, emitter):
        assert token == "token-integrador-ficticio"
        assert emitter == "emitente-teste"
        return deepcopy(self.value)

    def write(self, token, emitter, payload):
        assert token == "token-integrador-ficticio"
        assert emitter == "emitente-teste"
        self.writes.append(deepcopy(payload))
        if self.error:
            raise self.error
        self.value = {**deepcopy(payload), "atualizadoEm": "2026-09-11T12:00:00Z"}
        return deepcopy(self.value)


@pytest.fixture
def store(pilot):
    EmpresaConfigFiscal.__table__.create(bind=pilot.db.get_bind(), checkfirst=True)
    pilot.tenant.inscricao_estadual = "123456789"
    pilot.tenant.inscricao_municipal = "987654"
    pilot.tenant.endereco = "Rua das Flores"
    pilot.tenant.numero = "100"
    pilot.tenant.complemento = "Sala 2"
    pilot.tenant.bairro = "Centro"
    pilot.tenant.cidade = "São Paulo"
    pilot.tenant.codigo_municipio = "3550308"
    pilot.tenant.uf = "SP"
    pilot.tenant.cep = "01001-000"
    pilot.tenant.telefone = "(11) 99999-8888"
    pilot.tenant.email = "fiscal@empresa.com.br"
    pilot.tenant.email_resposta = "notas@empresa.com.br"
    pilot.db.add(
        EmpresaConfigFiscal(
            tenant_id=pilot.id,
            uf="SP",
            regime_tributario="Simples Nacional",
            contribuinte_icms=True,
            icms_aliquota_interna=18,
            icms_aliquota_interestadual=12,
            aplica_difal=True,
            cfop_venda_interna="5102",
            cfop_venda_interestadual="6102",
            cfop_compra="1102",
            simples_ativo=True,
        )
    )
    pilot.db.commit()
    activate(pilot.db, pilot.id, pilot.api)
    result = Store()
    pilot.api.fiscal_registration = result.read
    pilot.api.set_fiscal_registration = result.write
    return result


def test_syncs_complete_corepet_profile_without_customer_retyping(store, http_pilot):
    client, access, _app = http_pilot
    before = client.get("/intnfe/cadastro-fiscal")
    assert before.status_code == 200
    assert before.json()["pronto_para_sincronizar"] is True
    assert before.json()["sincronizado"] is False

    response = client.post("/intnfe/cadastro-fiscal/sincronizar")
    assert response.status_code == 200, response.text
    assert response.json()["sincronizado"] is True
    assert store.writes == [
        {
            "razaoSocial": "Loja Teste Ltda",
            "nomeFantasia": "Loja Teste",
            "inscricaoEstadual": "123456789",
            "crt": "1",
            "inscricaoMunicipal": "987654",
            "endereco": {
                "logradouro": "Rua das Flores",
                "numero": "100",
                "complemento": "Sala 2",
                "bairro": "Centro",
                "municipio": "São Paulo",
                "codigoMunicipio": "3550308",
                "uf": "SP",
                "cep": "01001000",
            },
            "telefone": "11999998888",
            "email": "notas@empresa.com.br",
        }
    ]
    assert [item["new_value"]["resultado"] for item in access["audits"]] == [
        "solicitado",
        "confirmado",
    ]


def test_same_profile_does_not_write_again(store, http_pilot):
    client, _access, _app = http_pilot
    assert client.post("/intnfe/cadastro-fiscal/sincronizar").status_code == 200
    assert client.post("/intnfe/cadastro-fiscal/sincronizar").status_code == 200
    assert len(store.writes) == 1


def test_missing_core_field_blocks_provider_write(store, pilot, http_pilot):
    client, _access, _app = http_pilot
    pilot.tenant.codigo_municipio = None
    pilot.db.commit()
    response = client.post("/intnfe/cadastro-fiscal/sincronizar")
    assert response.status_code == 422
    assert response.json()["detail"]["codigo"] == "DadosFiscaisPendentes"
    assert "código IBGE" in response.json()["detail"]["mensagem"]
    assert store.writes == []


def test_provider_failure_does_not_expose_remote_body_or_retry(store, http_pilot):
    client, access, _app = http_pilot
    store.error = IntNFeError(
        "DadosRecusados", status=422, correlation="protocolo-ficticio"
    )
    response = client.post("/intnfe/cadastro-fiscal/sincronizar")
    assert response.status_code == 422
    assert len(store.writes) == 1
    assert access["audits"][-1]["new_value"]["resultado"] == "recusado"


def test_audit_failure_before_sync_prevents_external_write(
    store, http_pilot, monkeypatch
):
    from app.intnfe import routes

    client, _access, _app = http_pilot

    def fail(*_args, **_kwargs):
        raise SQLAlchemyError("falha-local-ficticia")

    monkeypatch.setattr(routes, "log_action", fail)
    response = client.post("/intnfe/cadastro-fiscal/sincronizar")
    assert response.status_code == 503
    assert response.json()["detail"]["codigo"] == "AuditoriaIndisponivel"
    assert store.writes == []
