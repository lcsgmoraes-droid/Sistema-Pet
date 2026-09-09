"""Contrato de creditos sem banco externo, credencial real ou API paga."""

import base64
import hashlib
import json
from datetime import datetime, timedelta, timezone
from io import BytesIO
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.creditos_schemas import (
    CreditoOrcamentoRequest,
    normalizar_credit_payload,
)
from app.services.ai_usage import record_openai_usage


TENANT_A = "0bc09aa1-aa32-4fb7-aa54-29c8b8b56671"
TENANT_B = "0bc09aa1-aa32-4fb7-aa54-29c8b8b56672"
DESCRIPTION_PAYLOAD = {"codigo_barras": "7891234567890", "nome": "Produto ficticio"}
DESCRIPTION_PATH = "/produtos/assistente-ia/preencher-por-ean"


def test_orcamento_nao_aceita_empresa_ou_usuario_injetados_no_corpo():
    for field in ("tenant_id", "actor_user_id"):
        with pytest.raises(ValidationError):
            CreditoOrcamentoRequest.model_validate(
                {
                    "service_code": "produto.descricao_fiscal",
                    "request_payload": {"codigo_barras": "7891234567890"},
                    field: "outra-identidade",
                }
            )


@pytest.mark.parametrize(
    ("service", "payload"),
    [
        ("oferta.imagem", {"produto_id": 1}),
        ("oferta.imagem", {"produto_id": 1, "file_sha256": "nao-e-hash"}),
        (
            "oferta.imagem",
            {"produto_id": 1, "imagem_url": "/imagem.png", "orientacao": "4k"},
        ),
        (
            "produto.descricao_fiscal",
            {"codigo_barras": "7891234567890", "tenant_id": "outra-empresa"},
        ),
    ],
)
def test_payload_invalido_nao_gera_orcamento_nem_expoe_dados(service, payload):
    with pytest.raises(HTTPException) as caught:
        normalizar_credit_payload(service, payload)

    assert caught.value.status_code == 422
    assert "outra-empresa" not in str(caught.value.detail)


def test_payload_canonico_inclui_defaults_e_identidade_da_imagem():
    payload = normalizar_credit_payload(
        "oferta.imagem", {"produto_id": 7, "file_sha256": "a" * 64}
    )

    assert payload == {
        "produto_id": 7,
        "estilo": "profissional",
        "orientacao": "quadrada",
        "prompt_usuario": "",
        "imagem_url": "",
        "file_sha256": "a" * 64,
    }


def test_consumo_coleta_contadores_sem_chave_prompt_ou_resposta_bruta():
    sentinel = "segredo-ficticio-nao-deve-ir-ao-extrato"
    response = SimpleNamespace(
        model="modelo-simulado",
        id="resp_simulado",
        _request_id="req_simulado",
        usage={
            "input_tokens": 100,
            "output_tokens": 20,
            "total_tokens": 120,
            "api_key": sentinel,
            "input_tokens_details": {"cached_tokens": 5, "prompt": sentinel},
        },
        output=[{"type": "web_search_call", "content": sentinel}],
        output_text=sentinel,
        api_key=sentinel,
    )
    usage = {}

    record_openai_usage(usage, response, model="fallback-simulado")

    assert usage["input_tokens"] == 100
    assert usage["output_tokens"] == 20
    assert usage["cached_tokens"] == 5
    assert usage["web_search_calls"] == 1
    assert usage["provider_cost"] is None
    assert usage["cost_status"] == "not_reconciled"
    assert sentinel not in str(usage)
    assert "api_key" not in usage
    assert "output_text" not in usage


def test_contadores_invalidos_nao_entram_no_extrato():
    usage = {}
    record_openai_usage(
        usage,
        {"usage": {"input_tokens": True, "output_tokens": -1, "total_tokens": "9"}},
        model="modelo-simulado",
    )

    assert "input_tokens" not in usage
    assert "output_tokens" not in usage
    assert "total_tokens" not in usage


@pytest.fixture
def credit_api(monkeypatch):
    """HTTP + servico real, com somente as tres tabelas de credito em memoria."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from sqlalchemy import (
        Column,
        Integer,
        MetaData,
        String,
        Table,
        create_engine,
        event,
    )
    from sqlalchemy.orm import Session, sessionmaker
    from sqlalchemy.pool import StaticPool

    from app.auth.dependencies import get_current_user_and_tenant

    # cadastro_routes importa Venda; registrar apenas suas dependencias ORM, sem
    # importar app.main nem criar tabelas de dominio na base isolada.
    import app.financeiro_models  # noqa: F401
    from app import ofertas_estudio_routes
    from app.creditos_models import CreditoLedgerEntry, CreditoOperation, CreditoWallet
    from app.db import get_session
    from app.produtos import cadastro_routes
    from app.produtos_models import Produto
    from app.routes import creditos_routes
    from app.security import permissions_decorator
    from app.services.produto_ai_enrichment import ProdutoAIRascunho
    from app.tenancy.context import clear_current_tenant, set_current_tenant

    monkeypatch.setenv("COREPET_CREDITOS_MODE", "shadow")
    monkeypatch.setenv("COREPET_CREDITOS_TENANT_ALLOWLIST", f"{TENANT_A},{TENANT_B}")
    metadata = MetaData()
    tenants = Table("tenants", metadata, Column("id", String(36), primary_key=True))
    users = Table("users", metadata, Column("id", Integer, primary_key=True))
    wallet = CreditoWallet.__table__.to_metadata(metadata)
    operations = CreditoOperation.__table__.to_metadata(metadata)
    ledger = CreditoLedgerEntry.__table__.to_metadata(metadata)
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enforce_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(tenants.insert(), [{"id": TENANT_A}, {"id": TENANT_B}])
        connection.execute(users.insert(), [{"id": 11}, {"id": 12}, {"id": 22}])

    class ProductLookup:
        """Catalogo ficticio; exige os mesmos filtros tenant/id usados pela rota."""

        def __init__(self):
            self.predicates = {}

        def filter(self, *clauses):
            self.predicates.update(
                {clause.left.key: clause.right.value for clause in clauses}
            )
            return self

        def first(self):
            if (
                str(self.predicates.get("tenant_id")) != TENANT_A
                or self.predicates.get("id") != 7
            ):
                return None
            return SimpleNamespace(id=7, nome="Produto ficticio", tenant_id=TENANT_A)

    class IsolatedSession(Session):
        def query(self, *entities, **kwargs):
            if entities == (Produto,):
                return ProductLookup()
            return super().query(*entities, **kwargs)

    sessions = sessionmaker(bind=engine, class_=IsolatedSession, expire_on_commit=False)
    actor = {"tenant": TENANT_A, "user_id": 11}
    calls = []
    behavior = {"error": None, "usage": {}}

    def principal():
        tenant = UUID(actor["tenant"])
        set_current_tenant(tenant)
        return SimpleNamespace(id=actor["user_id"], is_admin=True), tenant

    def isolated_session():
        with sessions() as session:
            yield session

    def fake_provider(**kwargs):
        calls.append(
            {"codigo_barras": kwargs["codigo_barras"], "nome": kwargs.get("nome")}
        )
        usage = kwargs.get("usage_metadata")
        if usage is not None:
            usage.update(behavior["usage"])
        if behavior["error"] is not None:
            raise behavior["error"]
        if usage is not None:
            usage.update(
                {
                    "provider": "openai",
                    "model": "modelo-falso",
                    "response_received": True,
                }
            )
        return ProdutoAIRascunho(
            descricao="Descricao de teste suficientemente longa para o rascunho comercial.",
            confianca_fiscal="baixa",
            alertas_revisao=["Dado ficticio: revisar antes de usar."],
        )

    def allow_permission(*_args, **_kwargs):
        return None

    def fake_image_provider(**kwargs):
        calls.append({"kind": "image", "produto_id": kwargs["produto_id"]})
        kwargs["usage_metadata"].update({"response_received": True, "image_count": 1})
        return "/uploads/ofertas/imagem-ficticia.png"

    monkeypatch.setattr(permissions_decorator, "check_permission", allow_permission)
    monkeypatch.setattr(creditos_routes, "check_permission", allow_permission)
    monkeypatch.setattr(
        cadastro_routes, "resolver_chave_openai_tenant", lambda *_args: "chave-ficticia"
    )
    monkeypatch.setattr(
        cadastro_routes, "gerar_rascunho_produto_por_ean", fake_provider
    )
    monkeypatch.setattr(
        ofertas_estudio_routes,
        "resolver_chave_openai_tenant",
        lambda *_args: "chave-ficticia",
    )
    monkeypatch.setattr(
        ofertas_estudio_routes, "gerar_imagem_profissional", fake_image_provider
    )
    app = FastAPI()
    app.include_router(creditos_routes.router)
    app.include_router(cadastro_routes.router, prefix="/produtos")
    app.include_router(ofertas_estudio_routes.router)
    app.dependency_overrides[get_current_user_and_tenant] = principal
    app.dependency_overrides[get_session] = isolated_session

    with TestClient(app, raise_server_exceptions=False) as client:
        yield SimpleNamespace(
            client=client,
            actor=actor,
            calls=calls,
            behavior=behavior,
            engine=engine,
            sessions=sessions,
            wallet=wallet,
            operations=operations,
            ledger=ledger,
        )
    clear_current_tenant()
    engine.dispose()


def _quote(api, *, key="quote-test-0001", payload=None):
    response = api.client.post(
        "/creditos/orcamento",
        json={
            "service_code": "produto.descricao_fiscal",
            "request_payload": payload or DESCRIPTION_PAYLOAD,
            "idempotency_key": key,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _execute(api, operation_id, *, payload=None):
    return api.client.post(
        DESCRIPTION_PATH,
        json={**(payload or DESCRIPTION_PAYLOAD), "credit_operation_id": operation_id},
    )


def test_http_orcamento_repetido_usa_mesma_operacao_e_rejeita_payload_alterado(
    credit_api,
):
    original = _quote(credit_api)
    assert _quote(credit_api)["operation_id"] == original["operation_id"]
    response = credit_api.client.post(
        "/creditos/orcamento",
        json={
            "service_code": "produto.descricao_fiscal",
            "request_payload": {**DESCRIPTION_PAYLOAD, "nome": "Outro produto"},
            "idempotency_key": "quote-test-0001",
        },
    )
    assert response.status_code == 409
    assert credit_api.calls == []


@pytest.mark.parametrize("other_tenant,other_user", [(TENANT_B, 22), (TENANT_A, 12)])
def test_http_operacao_nao_pode_ser_lida_ou_executada_por_outra_identidade(
    credit_api, other_tenant, other_user
):
    operation_id = _quote(credit_api)["operation_id"]
    credit_api.actor.update(tenant=other_tenant, user_id=other_user)

    read = credit_api.client.get(f"/creditos/operacoes/{operation_id}")
    run = _execute(credit_api, operation_id)

    assert read.status_code in {403, 404}
    assert run.status_code in {403, 404}
    assert credit_api.calls == []


def test_http_orcamento_expirado_nao_chama_fornecedor(credit_api):
    operation_id = _quote(credit_api)["operation_id"]
    with credit_api.engine.begin() as connection:
        connection.execute(
            credit_api.operations.update()
            .where(credit_api.operations.c.id == operation_id)
            .values(expires_at=datetime.now(timezone.utc) - timedelta(minutes=1))
        )

    response = _execute(credit_api, operation_id)

    assert response.status_code == 409
    assert credit_api.calls == []


def test_http_confirmacao_com_payload_trocado_nao_chama_fornecedor(credit_api):
    operation_id = _quote(credit_api)["operation_id"]
    response = _execute(
        credit_api,
        operation_id,
        payload={**DESCRIPTION_PAYLOAD, "nome": "Produto trocado"},
    )

    assert response.status_code == 409
    assert credit_api.calls == []


def test_http_orcamento_de_imagem_nao_autoriza_descricao(credit_api):
    from app.services import creditos_service
    from app.tenancy.context import set_current_tenant

    set_current_tenant(UUID(TENANT_A))
    with credit_api.sessions() as session:
        quote = creditos_service.quote(
            session,
            TENANT_A,
            11,
            "oferta.imagem",
            normalizar_credit_payload(
                "oferta.imagem", {"produto_id": 7, "file_sha256": "a" * 64}
            ),
            idempotency_key="image-quote-test-0001",
        )

    response = _execute(credit_api, quote["operation_id"])

    assert response.status_code == 409
    assert credit_api.calls == []


def test_http_retry_concluido_nao_repete_fornecedor_e_shadow_nao_debita(credit_api):
    operation_id = _quote(credit_api)["operation_id"]
    first = _execute(credit_api, operation_id)
    second = _execute(credit_api, operation_id)

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert second.json() == first.json()
    assert len(credit_api.calls) == 1
    operation = credit_api.client.get(f"/creditos/operacoes/{operation_id}").json()
    assert operation["status"] == "completed"
    assert operation["result"] == first.json()
    balance = credit_api.client.get("/creditos/carteira").json()
    assert balance["available_credits"] == 0
    assert balance["reserved_credits"] == 0
    assert balance["checkout_enabled"] is False
    with credit_api.engine.connect() as connection:
        rows = connection.execute(credit_api.ledger.select()).mappings().all()
    assert len(rows) == 1
    assert rows[0]["kind"] == "shadow_usage"
    assert rows[0]["available_delta"] == rows[0]["reserved_delta"] == 0


def test_http_timeout_fica_incerto_e_retry_nao_repete_fornecedor(credit_api):
    credit_api.behavior["error"] = TimeoutError("timeout-simulado")
    operation_id = _quote(credit_api)["operation_id"]

    first = _execute(credit_api, operation_id)
    second = _execute(credit_api, operation_id)

    assert first.status_code == 409
    assert second.status_code == 409
    assert len(credit_api.calls) == 1
    operation = credit_api.client.get(f"/creditos/operacoes/{operation_id}").json()
    assert operation["status"] == "uncertain"
    assert operation["result"] is None
    assert "timeout-simulado" not in first.text


def test_http_falha_ao_persistir_resultado_nao_repete_fornecedor(
    credit_api, monkeypatch
):
    from app.services import creditos_service

    operation_id = _quote(credit_api)["operation_id"]

    def persistence_failure(*_args, **_kwargs):
        raise RuntimeError("falha-de-banco-simulada-sem-expor-detalhes")

    monkeypatch.setattr(creditos_service, "complete_operation", persistence_failure)
    first = _execute(credit_api, operation_id)
    second = _execute(credit_api, operation_id)

    assert first.status_code == second.status_code == 409
    assert len(credit_api.calls) == 1
    assert "falha-de-banco-simulada" not in first.text
    operation = credit_api.client.get(f"/creditos/operacoes/{operation_id}").json()
    assert operation["status"] == "running"
    assert operation["result"] is None


def test_http_permissao_revogada_nao_expoe_resultado_existente(credit_api, monkeypatch):
    from app.routes import creditos_routes

    operation_id = _quote(credit_api)["operation_id"]
    assert _execute(credit_api, operation_id).status_code == 200

    def forbidden(*_args, **_kwargs):
        raise HTTPException(403, "Sem permissao")

    monkeypatch.setattr(creditos_routes, "check_permission", forbidden)
    response = credit_api.client.get(f"/creditos/operacoes/{operation_id}")
    assert response.status_code == 403
    assert "Descricao de teste" not in response.text


def test_http_extrato_nao_expoe_uso_bruto_nem_dados_de_outro_tenant(credit_api):
    sentinel = "credencial-ficticia-sem-exposicao"
    credit_api.behavior["usage"] = {
        "api_key": sentinel,
        "prompt": sentinel,
        "raw_response": {"secret": sentinel},
        "input_tokens": 30,
    }
    operation_id = _quote(credit_api)["operation_id"]
    response = _execute(credit_api, operation_id)
    assert response.status_code == 200, response.text

    ledger = credit_api.client.get("/creditos/extrato")
    operation = credit_api.client.get(f"/creditos/operacoes/{operation_id}")
    assert sentinel not in ledger.text + operation.text
    assert "raw_response" not in ledger.text + operation.text
    with credit_api.engine.connect() as connection:
        stored = (
            connection.execute(
                credit_api.operations.select().where(
                    credit_api.operations.c.id == operation_id
                )
            )
            .mappings()
            .one()
        )
    assert sentinel not in str(stored["usage_metadata"])
    assert "raw_response" not in stored["usage_metadata"]
    assert stored["usage_metadata"]["input_tokens"] == 30
    assert stored["usage_metadata"]["provider_cost_cents"] is None

    credit_api.actor.update(tenant=TENANT_B, user_id=22)
    other_ledger = credit_api.client.get("/creditos/extrato")
    assert other_ledger.status_code == 200
    assert other_ledger.json()["items"] == []


def test_http_shadow_exige_orcamento_e_off_preserva_fluxo_legado(
    credit_api, monkeypatch
):
    response = credit_api.client.post(DESCRIPTION_PATH, json=DESCRIPTION_PAYLOAD)
    assert response.status_code == 428
    assert credit_api.calls == []

    monkeypatch.setenv("COREPET_CREDITOS_MODE", "off")
    response = credit_api.client.post(DESCRIPTION_PATH, json=DESCRIPTION_PAYLOAD)
    assert response.status_code == 200, response.text
    assert len(credit_api.calls) == 1


def _test_image_bytes(color="red"):
    from PIL import Image

    output = BytesIO()
    Image.new("RGB", (2, 2), color).save(output, format="PNG")
    return output.getvalue()


def _image_quote(api, payload):
    response = api.client.post(
        "/creditos/orcamento",
        json={
            "service_code": "oferta.imagem",
            "request_payload": payload,
            "idempotency_key": "imagem-api-test-0001",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["operation_id"]


def test_http_imagem_multipart_reusa_resultado_e_rejeita_foto_adulterada(credit_api):
    image_bytes = _test_image_bytes()
    operation_id = _image_quote(
        credit_api,
        {
            "produto_id": 7,
            "file_sha256": hashlib.sha256(image_bytes).hexdigest(),
        },
    )
    data = {"produto_id": "7", "credit_operation_id": operation_id}

    def execute(content):
        return credit_api.client.post(
            "/ofertas/imagens/gerar",
            data=data,
            files={"file": ("foto.png", content, "image/png")},
        )

    first = execute(image_bytes)
    second = execute(image_bytes)
    altered = execute(_test_image_bytes("blue"))
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert second.json() == first.json()
    assert altered.status_code == 409
    assert credit_api.calls == [{"kind": "image", "produto_id": 7}]
    operation = credit_api.client.get(f"/creditos/operacoes/{operation_id}").json()
    assert operation["result"]["url"] == "/uploads/ofertas/imagem-ficticia.png"


def test_http_imagem_url_nao_autoriza_trocar_origem_para_upload(
    credit_api, monkeypatch
):
    from app import ofertas_estudio_routes

    source = "/uploads/produtos/foto-ficticia.png"
    image_bytes = _test_image_bytes()
    monkeypatch.setattr(
        ofertas_estudio_routes,
        "_ler_imagem_referencia_produto",
        lambda *_args: (image_bytes, "image/png"),
    )
    operation_id = _image_quote(credit_api, {"produto_id": 7, "imagem_url": source})
    data = {
        "produto_id": "7",
        "imagem_url": source,
        "credit_operation_id": operation_id,
    }
    tampered = credit_api.client.post(
        "/ofertas/imagens/gerar",
        data=data,
        files={"file": ("foto.png", image_bytes, "image/png")},
    )
    assert tampered.status_code == 409
    assert credit_api.calls == []
    valid = credit_api.client.post("/ofertas/imagens/gerar", data=data)
    assert valid.status_code == 200, valid.text
    assert len(credit_api.calls) == 1


def test_http_operacao_continua_consultavel_apos_desativar_modo(
    credit_api, monkeypatch
):
    operation_id = _quote(credit_api)["operation_id"]
    result = _execute(credit_api, operation_id)
    assert result.status_code == 200
    monkeypatch.setenv("COREPET_CREDITOS_MODE", "off")

    read = credit_api.client.get(f"/creditos/operacoes/{operation_id}")
    assert read.status_code == 200
    assert read.json()["status"] == "completed"
    assert read.json()["result"] == result.json()
    assert _execute(credit_api, operation_id).status_code == 409
    assert len(credit_api.calls) == 1


def test_http_mudanca_shadow_para_cobranca_exige_novo_orcamento(
    credit_api, monkeypatch
):
    operation_id = _quote(credit_api)["operation_id"]
    monkeypatch.setenv("COREPET_CREDITOS_MODE", "enforced")

    assert _execute(credit_api, operation_id).status_code == 409
    assert credit_api.calls == []


def test_http_sem_saldo_nao_chama_fornecedor(credit_api, monkeypatch):
    monkeypatch.setenv("COREPET_CREDITOS_MODE", "enforced")
    operation_id = _quote(credit_api)["operation_id"]

    response = _execute(credit_api, operation_id)
    assert response.status_code == 402
    assert credit_api.calls == []
    read = credit_api.client.get(f"/creditos/operacoes/{operation_id}")
    assert read.json()["status"] == "quoted"


@pytest.mark.parametrize("definite", [True, False])
def test_http_falha_certa_libera_saldo_e_timeout_retem_reserva(
    credit_api, monkeypatch, definite
):
    monkeypatch.setenv("COREPET_CREDITOS_MODE", "enforced")
    with credit_api.engine.begin() as connection:
        connection.execute(
            credit_api.wallet.insert().values(
                tenant_id=UUID(TENANT_A),
                available_credits=1000,
                reserved_credits=0,
                version=0,
            )
        )
    quote = _quote(credit_api)
    operation_id = quote["operation_id"]
    if definite:
        credit_api.behavior["error"] = HTTPException(502, "Falha simulada de geracao")
        credit_api.behavior["usage"] = {"response_received": True, "input_tokens": 25}
    else:
        credit_api.behavior["error"] = TimeoutError("incerteza-simulada")

    first = _execute(credit_api, operation_id)
    second = _execute(credit_api, operation_id)
    assert first.status_code == (502 if definite else 409)
    assert second.status_code == 409
    assert len(credit_api.calls) == 1
    balance = credit_api.client.get("/creditos/carteira").json()
    assert balance["available_credits"] == (
        1000 if definite else 1000 - quote["credits"]
    )
    assert balance["reserved_credits"] == (0 if definite else quote["credits"])
    read = credit_api.client.get(f"/creditos/operacoes/{operation_id}").json()
    assert read["status"] == ("failed" if definite else "uncertain")
    with credit_api.engine.connect() as connection:
        stored = (
            connection.execute(
                credit_api.operations.select().where(
                    credit_api.operations.c.id == operation_id
                )
            )
            .mappings()
            .one()
        )
    if definite:
        assert stored["usage_metadata"]["response_received"] is True
        assert stored["usage_metadata"]["input_tokens"] == 25
        assert stored["usage_metadata"]["provider_cost_cents"] is None


@pytest.mark.parametrize("service", ["description", "image"])
def test_sdks_nao_repetem_chamada_paga_automaticamente(monkeypatch, tmp_path, service):
    import openai
    from app.services import ofertas_estudio_ai, produto_ai_enrichment

    constructed = []
    calls = []

    class FakeOpenAI:
        def __init__(self, **kwargs):
            constructed.append(kwargs)
            self.responses = SimpleNamespace(create=self.create_description)
            self.images = SimpleNamespace(edit=self.create_image)

        def create_description(self, **kwargs):
            calls.append("description")
            return SimpleNamespace(
                output_text=json.dumps(
                    {
                        "descricao": "Descricao ficticia suficientemente longa para validar o rascunho.",
                        "confianca_fiscal": "baixa",
                        "alertas_revisao": [],
                    }
                )
            )

        def create_image(self, **kwargs):
            calls.append("image")
            return SimpleNamespace(
                data=[SimpleNamespace(b64_json=base64.b64encode(b"png-falso").decode())]
            )

    monkeypatch.setattr(openai, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(ofertas_estudio_ai, "UPLOAD_DIR", tmp_path)
    usage = {}
    if service == "description":
        produto_ai_enrichment.gerar_rascunho_produto_por_ean(
            api_key="chave-ficticia", **DESCRIPTION_PAYLOAD, usage_metadata=usage
        )
    else:
        ofertas_estudio_ai.gerar_imagem_profissional(
            api_key="chave-ficticia",
            tenant_id=TENANT_A,
            produto_id=7,
            produto_nome="Produto ficticio",
            file_bytes=b"imagem-ficticia",
            content_type="image/png",
            estilo="profissional",
            orientacao="quadrada",
            prompt_usuario="fundo neutro",
            usage_metadata=usage,
        )

    assert len(constructed) == 1
    assert constructed[0]["max_retries"] == 0
    assert calls == [service]
    assert usage["response_received"] is True
    assert "chave-ficticia" not in str(usage)
