"""Revisão fiscal manual: acesso por empresa e imutabilidade após o envio."""

from types import SimpleNamespace
from uuid import UUID
from datetime import datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, noload
from sqlalchemy.pool import StaticPool

from app import caixa_models  # noqa: F401 - registra a FK vendas.caixa_id
from app import nfe_routes
from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.models import AuditLog
from app.tenancy.context import tenant_context
from app.vendas_models import Venda

TENANT = UUID("11111111-1111-1111-1111-111111111111")
OTHER_TENANT = UUID("22222222-2222-2222-2222-222222222222")
ENDPOINT = "/api/nfe/vendas/1/dados-adicionais"
AMAZON = {
    "canal": "amazon",
    "numero_pedido": "701-8373817-8649038",
    "codigo_rastreamento": "AA123456789BR",
    "informacoes_complementares": "Entregar na portaria",
    "intermediador_cnpj": "11.444.777/0001-61",
    "intermediador_identificacao": "CADASTRO-VENDEDOR-123",
}


@pytest.fixture
def commercial_api():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Venda.__table__.create(engine)
    AuditLog.__table__.create(engine)
    with engine.begin() as conn:
        for sale_id, tenant in ((1, TENANT), (2, OTHER_TENANT)):
            conn.execute(
                Venda.__table__.insert().values(
                    id=sale_id,
                    tenant_id=tenant,
                    numero_venda=f"20261026000{sale_id}",
                    user_id=74,
                    vendedor_id=74,
                    subtotal=145,
                    total=145,
                    status="finalizada",
                    canal="loja_fisica",
                    observacoes="Observação original da venda",
                )
            )
    app = FastAPI()
    app.include_router(nfe_routes.router, prefix="/api")

    def session():
        with Session(engine) as db:
            # Estes testes verificam o documento e a empresa; não carregam
            # pagamentos, estoque ou outros agregados comerciais da venda.
            @event.listens_for(db, "do_orm_execute")
            def no_related_aggregates(state):
                if state.is_select:
                    state.statement = state.statement.options(noload("*"))

            yield db

    app.dependency_overrides[get_session] = session
    app.dependency_overrides[get_current_user_and_tenant] = lambda: (
        SimpleNamespace(id=74),
        TENANT,
    )
    with tenant_context(TENANT), TestClient(app) as client:
        yield SimpleNamespace(client=client, app=app, engine=engine)
    engine.dispose()


def update_sale(context, **values):
    with context.engine.begin() as conn:
        conn.execute(Venda.__table__.update().where(Venda.id == 1).values(**values))


def test_dados_adicionais_exigem_autenticacao(commercial_api):
    del commercial_api.app.dependency_overrides[get_current_user_and_tenant]

    response = commercial_api.client.get(ENDPOINT)

    assert response.status_code in {401, 403}


@pytest.mark.parametrize("method", ["get", "put"])
def test_venda_de_outra_empresa_nao_pode_ser_lida_ou_alterada(commercial_api, method):
    kwargs = {"json": {"dados": AMAZON}} if method == "put" else {}

    response = getattr(commercial_api.client, method)(
        "/api/nfe/vendas/2/dados-adicionais", **kwargs
    )

    assert response.status_code == 404
    assert "Observação original" not in response.text
    with commercial_api.engine.connect() as conn:
        saved = (
            conn.execute(Venda.__table__.select().where(Venda.id == 2)).mappings().one()
        )
    assert saved["nfe_contexto_comercial"] is None


def test_nova_venda_manual_pode_revisar_contexto_antes_da_emissao(commercial_api):
    response = commercial_api.client.get(ENDPOINT)

    assert response.status_code == 200
    body = response.json()
    assert body["pode_editar"] is True
    assert body["dados"]["canal"] == "loja_fisica"
    assert "202610260001" in body["informacoes_adicionais"]


def test_salvar_contexto_amazon_persiste_numero_e_preview_sem_mudar_venda(
    commercial_api,
):
    response = commercial_api.client.put(ENDPOINT, json={"dados": AMAZON})

    assert response.status_code == 200
    body = response.json()
    assert body["dados"]["canal"] == "amazon"
    assert body["dados"]["intermediador_cnpj"] == "11444777000161"
    assert AMAZON["numero_pedido"] in body["informacoes_adicionais"]
    assert AMAZON["codigo_rastreamento"] in body["informacoes_adicionais"]
    assert AMAZON["informacoes_complementares"] in body["informacoes_adicionais"]
    reread = commercial_api.client.get(ENDPOINT)
    assert reread.status_code == 200
    assert reread.json()["dados"] == body["dados"]
    with commercial_api.engine.connect() as conn:
        saved = (
            conn.execute(Venda.__table__.select().where(Venda.id == 1)).mappings().one()
        )
    assert saved["canal"] == "loja_fisica"
    assert saved["status"] == "finalizada"
    assert saved["total"] == 145
    assert saved["observacoes"] == "Observação original da venda"
    assert saved["nfe_numero"] is None
    assert saved["nfe_correlation_id"] is None
    assert saved["nfe_contexto_comercial"]["numero_pedido"] == AMAZON["numero_pedido"]
    with commercial_api.engine.connect() as conn:
        audit = conn.execute(AuditLog.__table__.select()).mappings().one()
    assert audit["tenant_id"] == TENANT
    assert audit["user_id"] == 74
    assert audit["entity_id"] == 1
    assert AMAZON["numero_pedido"] in audit["new_value"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("intermediador_cnpj", "11444777000162"),
        ("intermediador_cnpj", "11111111111111"),
        ("intermediador_cnpj", "x11.444.777/0001-61"),
        ("intermediador_cnpj", ""),
        ("intermediador_identificacao", ""),
        ("intermediador_identificacao", AMAZON["numero_pedido"]),
        ("numero_pedido", ""),
        ("canal", "shopee"),
        ("informacoes_complementares", "x" * 4001),
    ],
)
def test_contexto_invalido_nao_e_salvo(commercial_api, field, value):
    response = commercial_api.client.put(
        ENDPOINT, json={"dados": {**AMAZON, field: value}}
    )

    assert response.status_code == 422
    with commercial_api.engine.connect() as conn:
        saved = (
            conn.execute(Venda.__table__.select().where(Venda.id == 1)).mappings().one()
        )
    assert saved["nfe_contexto_comercial"] is None


@pytest.mark.parametrize(
    "fiscal_state",
    [
        {"nfe_status": "autorizada"},
        {"nfe_status": "inconclusiva"},
        {"nfe_status": "processando"},
        {"nfe_status": "cancelada"},
        {"nfe_status": "denegada"},
        {"nfe_correlation_id": "correlacao-existente"},
        {"nfe_idempotency_key": "envio-existente"},
        {"nfe_bling_id": 123456},
        {"nfe_numero": 1648},
        {"nfe_chave": "1" * 44},
        {"nfe_protocolo": "135260000001648"},
        {"nfe_payload_hash": "hash-do-payload-enviado"},
        {"nfe_xml": "<xml>documento-original-preservado</xml>"},
        {"nfe_data_emissao": datetime(2026, 10, 26, 10, 30)},
        {"nfe_data_autorizacao": datetime(2026, 10, 26, 10, 31)},
        {"status": "cancelada"},
        {"nfe_status": "rejeitada", "nfe_correlation_id": "correlacao-rejeitada"},
    ],
)
def test_documento_ja_enviado_nao_pode_ter_contexto_reescrito(
    commercial_api, fiscal_state
):
    update_sale(commercial_api, **fiscal_state)

    before = commercial_api.client.get(ENDPOINT)
    response = commercial_api.client.put(ENDPOINT, json={"dados": AMAZON})

    assert before.status_code == 200
    assert before.json()["pode_editar"] is False
    assert response.status_code == 409
    with commercial_api.engine.connect() as conn:
        saved = (
            conn.execute(Venda.__table__.select().where(Venda.id == 1)).mappings().one()
        )
    assert saved["nfe_contexto_comercial"] is None
    assert all(saved[key] == value for key, value in fiscal_state.items())


def test_complemento_excedendo_limite_total_nao_e_truncado_ou_salvo(commercial_api):
    update_sale(commercial_api, observacoes="observação original " * 100)

    response = commercial_api.client.put(
        ENDPOINT,
        json={"dados": {**AMAZON, "informacoes_complementares": "x" * 4000}},
    )

    assert response.status_code == 422
    assert "5000" in str(response.json()["detail"])
    with commercial_api.engine.connect() as conn:
        saved = (
            conn.execute(Venda.__table__.select().where(Venda.id == 1)).mappings().one()
        )
    assert saved["nfe_contexto_comercial"] is None
