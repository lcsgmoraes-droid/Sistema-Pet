from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.db import Base
from app.intnfe.client import IntNFeError
from app.intnfe.models import IntNFeConnection
from app.intnfe.presentation import certificate_state, public_status, valid_cnpj
from app.intnfe.repository import ActivationError, get_connection, reserve, save
from app.intnfe.service import activate, bind_existing
from app.models import Tenant


CNPJ = "11222333000181"
OTHER_CNPJ = "11444777000161"


class FakeAPI:
    integrador_id = "integrador-teste"

    def __init__(self):
        self.emitters = []
        self.creates = 0
        self.certificate_value = None
        self.create_error = None
        self.cert_error = None
        self.auth_error = None
        self.sent_companies = []

    def record(self, cnpj=CNPJ):
        return {
            "tenantId": "emitente-teste",
            "clientId": "cliente-teste",
            "cnpj": cnpj,
            "integradorId": self.integrador_id,
            "ativo": True,
        }

    def integrator_token(self):
        return "token-integrador-ficticio"

    def list_emitters(self, _token):
        return list(self.emitters)

    def create_emitter(self, _token, company):
        self.creates += 1
        self.sent_companies.append(company)
        if self.create_error:
            raise self.create_error
        self.emitters.append(self.record(company["cnpj"]))
        return {**self.record(), "clientSecret": "segredo-emitente-ficticio"}

    def emitter_token(self, client_id, client_secret):
        if self.auth_error:
            raise self.auth_error
        assert client_id == "cliente-teste"
        assert client_secret == "segredo-emitente-ficticio"
        return "token-emitente-ficticio"

    def certificate(self, _token):
        if self.cert_error:
            raise self.cert_error
        return self.certificate_value


@pytest.fixture
def intnfe_db():
    # Apenas o schema usado neste fluxo; nao depende de tabelas de outros modulos.
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(
        engine, tables=[Tenant.__table__, IntNFeConnection.__table__]
    )
    with Session(engine) as session:
        yield session
    engine.dispose()


@pytest.fixture
def pilot(intnfe_db, tenant_context, monkeypatch):
    db_session = intnfe_db
    monkeypatch.setenv("PAYMENT_CONFIG_ENCRYPTION_KEY", "chave-local-ficticia-intnfe")
    monkeypatch.setattr(settings, "INTNFE_ACTIVATION_ENABLED", True)
    monkeypatch.setattr(settings, "INTNFE_INTEGRADOR_ID", FakeAPI.integrador_id)
    monkeypatch.setattr(
        settings, "INTNFE_INTEGRADOR_SECRET", SecretStr("segredo-integrador-ficticio")
    )
    tenant_id = uuid4()
    tenant_context(tenant_id)
    tenant = Tenant(
        id=str(tenant_id),
        name="Loja Teste",
        name_normalized=str(tenant_id),
        razao_social="Loja Teste Ltda",
        cnpj="11.222.333/0001-81",
    )
    db_session.add(tenant)
    db_session.commit()
    return SimpleNamespace(
        db=db_session,
        tenant=tenant,
        id=tenant_id,
        api=FakeAPI(),
        context=tenant_context,
    )


def test_activation_creates_once_stores_secret_and_does_not_issue(pilot):
    first = activate(pilot.db, pilot.id, pilot.api)
    assert first.status == "certificado_pendente"
    assert first.client_secret == "segredo-emitente-ficticio"
    assert first.client_secret_encrypted.startswith("fernet:")
    assert "segredo-emitente-ficticio" not in first.client_secret_encrypted
    second = activate(pilot.db, pilot.id, pilot.api)
    assert first.id == second.id
    assert pilot.api.creates == 1
    assert pilot.api.sent_companies == [
        {"cnpj": CNPJ, "razaoSocial": "Loja Teste Ltda", "nomeFantasia": "Loja Teste"}
    ]
    view = public_status(pilot.tenant, second, pilot.api.integrador_id)
    assert view["vinculado"] is True
    assert view["emissao_disponivel"] is False
    assert view["ambiente"] == "homologacao"
    assert all("secret" not in key and "token" not in key for key in view)


def test_existing_cnpj_requires_emitter_credentials_not_automatic_takeover(pilot):
    pilot.api.emitters = [pilot.api.record()]
    result = activate(pilot.db, pilot.id, pilot.api)
    assert result.status == "credenciais_pendentes"
    assert not result.client_secret_encrypted
    assert not result.emitente_id
    assert pilot.api.creates == 0
    result = bind_existing(
        pilot.db, pilot.id, pilot.api, "cliente-teste", "segredo-emitente-ficticio"
    )
    assert result.status == "certificado_pendente"
    assert result.emitente_id == "emitente-teste"


def test_conflicting_cnpj_preserves_code_and_allows_manual_retry_after_fix(pilot):
    pilot.api.create_error = IntNFeError(
        "EmitenteDuplicado", status=409, correlation="erro-teste-409"
    )
    first = activate(pilot.db, pilot.id, pilot.api)
    assert first.status == "cnpj_em_uso"
    assert first.ultimo_codigo == "EmitenteDuplicado"
    assert first.correlation_id == "erro-teste-409"
    assert first.criacao_iniciada is False
    activate(pilot.db, pilot.id, pilot.api, consult_only=True)
    assert pilot.api.creates == 1
    pilot.api.create_error = None
    result = activate(pilot.db, pilot.id, pilot.api)
    assert result.status == "certificado_pendente"
    assert pilot.api.creates == 2


def test_uncertain_creation_is_not_repeated_even_when_list_is_empty(pilot):
    pilot.api.create_error = IntNFeError("EmissorIndisponivel", uncertain=True)
    result = activate(pilot.db, pilot.id, pilot.api)
    assert result.status == "conciliacao_pendente"
    for consult in (True, False):
        result = activate(pilot.db, pilot.id, pilot.api, consult_only=consult)
        assert result.status == "conciliacao_pendente"
    assert pilot.api.creates == 1
    pilot.api.emitters = [pilot.api.record()]
    result = activate(pilot.db, pilot.id, pilot.api, consult_only=True)
    assert result.status == "credenciais_pendentes"
    assert pilot.api.creates == 1


def test_confirmed_rejection_allows_correcting_company_names_before_retry(pilot):
    pilot.api.create_error = IntNFeError("DadosRecusados", status=422)
    activate(pilot.db, pilot.id, pilot.api)
    pilot.tenant.razao_social = "Razão social corrigida Ltda"
    pilot.tenant.name = "Loja Corrigida"
    pilot.db.commit()
    pilot.api.create_error = None
    activate(pilot.db, pilot.id, pilot.api)
    assert pilot.api.sent_companies[-1]["razaoSocial"] == "Razão social corrigida Ltda"
    assert pilot.api.sent_companies[-1]["nomeFantasia"] == "Loja Corrigida"


def test_concurrent_request_and_stale_worker_cannot_overwrite_current_operation(pilot):
    connection, old_operation, _ = reserve(pilot.db, pilot.id, pilot.api.integrador_id)
    with pytest.raises(ActivationError, match="andamento"):
        activate(pilot.db, pilot.id, pilot.api)
    assert pilot.api.creates == 0
    connection.operacao_iniciada_em = datetime.now(timezone.utc) - timedelta(minutes=3)
    connection.criacao_iniciada = True  # Processo caiu depois de iniciar POST.
    pilot.db.commit()
    result = activate(pilot.db, pilot.id, pilot.api)
    assert result.status == "conciliacao_pendente"
    with pytest.raises(ActivationError, match="substituída"):
        save(pilot.db, pilot.id, old_operation, finish=True, status="vinculado")
    assert get_connection(pilot.db, pilot.id).status == "conciliacao_pendente"
    assert pilot.api.creates == 0


def test_certificate_failure_does_not_lose_one_time_credentials(pilot):
    pilot.api.cert_error = IntNFeError("EmissorIndisponivel")
    first = activate(pilot.db, pilot.id, pilot.api)
    assert first.client_secret == "segredo-emitente-ficticio"
    pilot.api.cert_error = None
    second = activate(pilot.db, pilot.id, pilot.api, consult_only=True)
    assert second.status == "certificado_pendente"
    assert pilot.api.creates == 1


def test_changed_company_or_integrator_never_reuses_credentials(pilot):
    activate(pilot.db, pilot.id, pilot.api)
    pilot.tenant.cnpj = OTHER_CNPJ
    pilot.db.commit()
    with pytest.raises(ActivationError, match="CNPJ mudou"):
        activate(pilot.db, pilot.id, pilot.api)
    pilot.tenant.cnpj = CNPJ
    pilot.db.commit()
    pilot.api.integrador_id = "outra-conta"
    with pytest.raises(ActivationError, match="conta do emissor mudou"):
        activate(pilot.db, pilot.id, pilot.api)
    assert pilot.api.creates == 1


def test_duplicate_cnpj_cannot_be_claimed_by_another_corepet_tenant(pilot):
    activate(pilot.db, pilot.id, pilot.api)
    other_id = uuid4()
    pilot.context(other_id)
    assert get_connection(pilot.db, other_id) is None
    assert (
        get_connection(pilot.db, pilot.id) is None
    )  # filtro ORM impede acesso cruzado
    other = Tenant(
        id=str(other_id),
        name="Outra loja",
        name_normalized=str(other_id),
        razao_social="Outra Loja",
        cnpj=CNPJ,
    )
    pilot.db.add(other)
    pilot.db.commit()
    with pytest.raises(ActivationError, match="já possui"):
        activate(pilot.db, other_id, pilot.api)
    assert pilot.api.creates == 1


def test_invalid_company_does_not_reserve_or_call_provider(pilot):
    pilot.tenant.cnpj = "123"
    pilot.db.commit()
    with pytest.raises(ActivationError, match="Complete os dados"):
        activate(pilot.db, pilot.id, pilot.api)
    assert get_connection(pilot.db, pilot.id) is None
    assert pilot.api.creates == 0


def test_consult_does_not_create_remote_emitter(pilot):
    result = activate(pilot.db, pilot.id, pilot.api, consult_only=True)
    assert result.status == "nao_vinculado"
    assert pilot.api.creates == 0


def test_bind_wrong_client_or_wrong_certificate_does_not_save_credentials(pilot):
    pilot.api.emitters = [pilot.api.record()]
    wrong = bind_existing(pilot.db, pilot.id, pilot.api, "outro-cliente", "segredo")
    assert wrong.status == "credenciais_invalidas"
    assert not wrong.client_secret_encrypted
    pilot.api.certificate_value = {"cnpj": OTHER_CNPJ}
    wrong = bind_existing(
        pilot.db, pilot.id, pilot.api, "cliente-teste", "segredo-emitente-ficticio"
    )
    assert wrong.status == "vinculo_inconsistente"
    assert not wrong.client_secret_encrypted


def test_deleted_or_inactive_remote_emitter_is_not_recreated(pilot):
    activate(pilot.db, pilot.id, pilot.api)
    pilot.api.emitters = []
    result = activate(pilot.db, pilot.id, pilot.api)
    assert result.status == "vinculo_inconsistente"
    pilot.api.emitters = [{**pilot.api.record(), "ativo": False}]
    result = activate(pilot.db, pilot.id, pilot.api)
    assert result.status == "emitente_inativo"
    assert pilot.api.creates == 1


def test_certificate_readiness_and_company_validation():
    now = datetime.now(timezone.utc)
    certificate = {
        "cnpj": CNPJ,
        "validoDe": (now - timedelta(days=5)).isoformat(),
        "validoAte": (now + timedelta(days=30)).isoformat(),
        "expirado": False,
    }
    assert certificate_state(certificate, CNPJ)[0] == "certificado_validado"
    assert certificate_state(certificate, OTHER_CNPJ)[0] == "certificado_invalido"
    assert (
        certificate_state({**certificate, "expirado": True}, CNPJ)[0]
        == "certificado_invalido"
    )
    assert certificate_state(None, CNPJ) == ("certificado_pendente", None)
    with pytest.raises(IntNFeError):
        certificate_state({}, CNPJ)
    assert valid_cnpj(CNPJ) and valid_cnpj(OTHER_CNPJ)
    assert not valid_cnpj("00000000000000")
    assert not valid_cnpj("11222333000180")


def test_missing_encryption_key_blocks_external_creation(pilot, monkeypatch):
    monkeypatch.delenv("PAYMENT_CONFIG_ENCRYPTION_KEY", raising=False)
    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(ActivationError, match="armazenamento seguro"):
        activate(pilot.db, pilot.id, pilot.api)
    assert pilot.api.creates == 0


def test_integration_disabled_is_not_presented_as_available(pilot, monkeypatch):
    monkeypatch.setattr(settings, "INTNFE_ACTIVATION_ENABLED", False)
    view = public_status(pilot.tenant, None, pilot.api.integrador_id)
    assert view["status"] == "indisponivel"
    assert not any(
        view[key] for key in ("pode_ativar", "pode_consultar", "pode_vincular")
    )


@pytest.fixture
def http_pilot(pilot, monkeypatch):
    from fastapi import FastAPI, HTTPException
    from fastapi.testclient import TestClient
    from app.auth.dependencies import get_current_user_and_tenant
    from app.db import get_session
    from app.intnfe import routes
    from app.security import permissions_decorator

    app = FastAPI()
    app.include_router(routes.router)
    access = {"allowed": True, "audits": []}

    def check(_db, user_id, permission, tenant_id, **_kwargs):
        assert permission == "configuracoes.editar"
        assert user_id == 7 and tenant_id == pilot.id
        if not access["allowed"]:
            raise HTTPException(403, "Sem permissão")

    async def authenticated():
        return SimpleNamespace(id=7), pilot.id

    monkeypatch.setattr(permissions_decorator, "check_permission", check)
    monkeypatch.setattr(
        routes, "log_action", lambda _db, **kwargs: access["audits"].append(kwargs)
    )
    app.dependency_overrides[get_current_user_and_tenant] = authenticated
    app.dependency_overrides[get_session] = lambda: pilot.db
    app.dependency_overrides[routes.get_client] = lambda: pilot.api
    with TestClient(app) as client:
        yield client, access, app


def test_routes_use_authenticated_tenant_and_return_no_secrets(pilot, http_pilot):
    client, access, _app = http_pilot
    response = client.post(
        "/intnfe/ativar", json={"tenant_id": str(uuid4()), "cnpj": OTHER_CNPJ}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "certificado_pendente"
    assert response.json()["empresa"]["cnpj"] == pilot.tenant.cnpj
    assert pilot.api.sent_companies[0]["cnpj"] == CNPJ
    assert "segredo-emitente" not in response.text
    assert "token-" not in response.text
    assert access["audits"][0]["tenant_id"] == pilot.id
    assert "client_secret" not in str(access["audits"])
    assert client.get("/intnfe/status").json()["emissao_disponivel"] is False


def test_routes_require_configuration_permission(pilot, http_pilot):
    client, access, _app = http_pilot
    access["allowed"] = False
    assert client.get("/intnfe/status").status_code == 403
    assert client.post("/intnfe/ativar").status_code == 403
    assert client.post("/intnfe/consultar").status_code == 403
    assert (
        client.post(
            "/intnfe/vincular", json={"client_id": "test", "client_secret": "test"}
        ).status_code
        == 403
    )
    assert pilot.api.creates == 0


def test_route_schema_errors_never_echo_secret(http_pilot):
    client, _access, _app = http_pilot
    secret = "segredo-deve-ser-oculto"
    for body in (
        {"client_secret": secret},
        {"client_id": "id", "client_secret": secret, "tenant_id": "proibido"},
    ):
        response = client.post("/intnfe/vincular", json=body)
        assert response.status_code == 422
        assert secret not in response.text


def test_routes_reject_unauthenticated_calls(http_pilot):
    from app.auth.dependencies import get_current_user_and_tenant

    client, _access, app = http_pilot
    del app.dependency_overrides[get_current_user_and_tenant]
    assert client.get("/intnfe/status").status_code in {401, 403}
    assert client.post("/intnfe/ativar").status_code in {401, 403}
