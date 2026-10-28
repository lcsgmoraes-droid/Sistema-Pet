"""API de clonagem: rotas estáticas, isolamento e documentos preservados."""

from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID
from xml.etree.ElementTree import ParseError

import pytest
import requests
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import nfe_routes
from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.intnfe.client import IntNFeError
from app.nfe import clone_routes
from app.nfe.clone_models import NotaFiscalClone
from app.tenancy.context import tenant_context

TENANT = UUID("11111111-1111-1111-1111-111111111111")
OTHER_TENANT = UUID("22222222-2222-2222-2222-222222222222")
XML = '<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe"><NFe /></nfeProc>'


@pytest.fixture
def clone_api():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    NotaFiscalClone.__table__.create(engine)
    data = {
        "serie": "1",
        "ambienteCodigo": 1,
        "produtos": [{"valorTotal": 145}],
        "pagamentos": [{"formaPagamento": "17", "valor": 145}],
    }
    with engine.begin() as conn:
        for clone_id, tenant in ((1, TENANT), (2, OTHER_TENANT)):
            conn.execute(
                NotaFiscalClone.__table__.insert().values(
                    id=clone_id,
                    tenant_id=tenant,
                    origem={"provedor": "bling", "numero": "1648"},
                    dados=data,
                    xml_origem=XML,
                    xml=XML,
                    modelo=55,
                    status="autorizada",
                    numero="1651",
                    correlation_id=f"correlacao-{clone_id}",
                )
            )
    api = Mock()
    app = FastAPI()
    app.include_router(nfe_routes.router, prefix="/api")

    def session():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_session] = session
    app.dependency_overrides[get_current_user_and_tenant] = lambda: (
        SimpleNamespace(id=74),
        TENANT,
    )
    app.dependency_overrides[clone_routes.client] = lambda: api
    with tenant_context(TENANT), TestClient(app) as client:
        yield SimpleNamespace(client=client, app=app, api=api, engine=engine)
    engine.dispose()


def test_lista_clones_usa_rota_estatica_e_so_mostra_empresa_autenticada(clone_api):
    response = clone_api.client.get("/api/nfe/clones")

    assert response.status_code == 200
    assert [row["id"] for row in response.json()["rascunhos"]] == [1]
    clone_api.api.issue_document.assert_not_called()


def test_clones_exigem_autenticacao(clone_api):
    del clone_api.app.dependency_overrides[get_current_user_and_tenant]

    response = clone_api.client.get("/api/nfe/clones")

    assert response.status_code in {401, 403}
    assert "rascunhos" not in response.json()


@pytest.mark.parametrize("suffix", ["", "/xml", "/danfe"])
def test_nota_de_outra_empresa_nao_pode_ser_aberta_ou_baixada(clone_api, suffix):
    response = clone_api.client.get(f"/api/nfe/clones/2{suffix}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Nota clonada não encontrada nesta empresa."
    assert "1648" not in response.text
    clone_api.api.document_danfe.assert_not_called()


def test_preparar_usa_tenant_da_autenticacao_e_nao_emite_nota(clone_api, monkeypatch):
    prepare = Mock(return_value=({"numeracao_automatica": True}, XML))
    monkeypatch.setattr(clone_routes.service, "prepare", prepare)

    response = clone_api.client.post(
        "/api/nfe/clones/preparar",
        json={"provedor": "bling", "id": 1648, "tenant_id": str(OTHER_TENANT)},
    )

    assert response.status_code == 200
    assert prepare.call_args.args[1] == TENANT
    assert "tenant_id" not in prepare.call_args.args[3]
    clone_api.api.issue_document.assert_not_called()


def test_xml_baixado_e_o_documento_armazenado_com_nome_de_nova_nota(clone_api):
    response = clone_api.client.get("/api/nfe/clones/1/xml")

    assert response.status_code == 200
    assert response.text == XML
    assert response.headers["content-type"] == "application/xml"
    assert 'filename="nota-clonada-1651.xml"' in response.headers["content-disposition"]


@pytest.mark.parametrize("suffix", ["xml", "danfe"])
def test_documento_sem_autorizacao_exibe_aviso_util(clone_api, suffix):
    with clone_api.engine.begin() as conn:
        conn.execute(
            NotaFiscalClone.__table__.update()
            .where(NotaFiscalClone.id == 1)
            .values(status="rascunho", xml=None)
        )

    response = clone_api.client.get(f"/api/nfe/clones/1/{suffix}")

    assert response.status_code == 409
    assert "autorização" in response.json()["detail"]
    clone_api.api.document_danfe.assert_not_called()


def test_danfe_nfe_usa_ambiente_e_correlacao_do_clone(clone_api, monkeypatch):
    connection = object()
    access_token = Mock(return_value="token-emitente")
    monkeypatch.setattr(clone_routes, "_connection", lambda *_a, **_kw: connection)
    monkeypatch.setattr(clone_routes, "_access_token", access_token)
    clone_api.api.document_danfe.return_value = b"%PDF-documento-novo"

    response = clone_api.client.get("/api/nfe/clones/1/danfe")

    assert response.status_code == 200
    assert response.content == b"%PDF-documento-novo"
    assert response.headers["content-type"] == "application/pdf"
    assert (
        'filename="danfe-clonada-1651.pdf"' in response.headers["content-disposition"]
    )
    clone_api.api.document_danfe.assert_called_once_with(
        "token-emitente", "nfe", "correlacao-1"
    )
    access_token.assert_called_once_with(clone_api.api, connection, 1)


def test_danfe_nfce_e_gerado_a_partir_do_xml_do_clone(clone_api, monkeypatch):
    with clone_api.engine.begin() as conn:
        conn.execute(
            NotaFiscalClone.__table__.update()
            .where(NotaFiscalClone.id == 1)
            .values(modelo=65, chave="1" * 44)
        )
    render = Mock(return_value=b"%PDF-cupom-novo")
    monkeypatch.setattr(clone_routes, "gerar_danfe_nfce", render)

    response = clone_api.client.get("/api/nfe/clones/1/danfe")

    assert response.status_code == 200
    render.assert_called_once_with(XML.encode("utf-8"), "1" * 44)
    clone_api.api.document_danfe.assert_not_called()


def test_danfe_invalido_do_emissor_nao_e_entregue_como_pdf(clone_api, monkeypatch):
    monkeypatch.setattr(clone_routes, "_connection", lambda *_a, **_kw: object())
    monkeypatch.setattr(clone_routes, "_access_token", lambda *_a: "token")
    clone_api.api.document_danfe.return_value = b"<html>502 Bad Gateway</html>"

    response = clone_api.client.get("/api/nfe/clones/1/danfe")

    assert response.status_code == 502
    assert "DANFE válido" in response.json()["detail"]
    assert "<html>" not in response.text


@pytest.mark.parametrize(
    "failure,status,fragment",
    [
        (IntNFeError("EmissorIndisponivel"), 503, "emissor"),
        (ParseError("xml-secreto-invalido"), 422, "inválidos"),
        (requests.Timeout("url-documento-privada"), 502, "documento original"),
    ],
)
def test_preparacao_falha_com_mensagem_util_sem_corpo_externo(
    clone_api, monkeypatch, failure, status, fragment
):
    monkeypatch.setattr(clone_routes.service, "prepare", Mock(side_effect=failure))

    response = clone_api.client.post(
        "/api/nfe/clones/preparar", json={"provedor": "bling", "id": 1648}
    )

    assert response.status_code == status
    assert fragment in response.json()["detail"]
    assert "xml-secreto" not in response.text
    assert "url-documento-privada" not in response.text


def test_integracao_indisponivel_nao_vira_erro_interno(clone_api, monkeypatch):
    del clone_api.app.dependency_overrides[clone_routes.client]
    monkeypatch.setattr(
        clone_routes,
        "IntNFeClient",
        Mock(side_effect=IntNFeError("IntegracaoNaoConfigurada")),
    )

    response = clone_api.client.post(
        "/api/nfe/clones/preparar", json={"provedor": "bling", "id": 1648}
    )

    assert response.status_code == 503
    assert "emissor" in response.json()["detail"].lower()


@pytest.mark.parametrize(
    "failure,status",
    [
        (Exception("Erro na API Bling: <html>502 Bad Gateway</html>"), 502),
        (HTTPException(404, "Detalhes: <html>502 Bad Gateway</html>"), 404),
    ],
)
def test_falha_bling_encapsulada_nao_vaza_html_nem_vira_erro_interno(
    clone_api, monkeypatch, failure, status
):
    monkeypatch.setattr(
        clone_routes.service,
        "get_tenant",
        lambda *_args: SimpleNamespace(cnpj="33590794000140"),
    )
    monkeypatch.setattr(
        clone_routes.service,
        "_connection",
        lambda *_args: SimpleNamespace(emission_environment=1),
    )
    monkeypatch.setattr(
        clone_routes.service,
        "obter_nota_documento",
        Mock(side_effect=failure),
    )

    response = clone_api.client.post(
        "/api/nfe/clones/preparar", json={"provedor": "bling", "id": 1648}
    )

    assert response.status_code == status
    assert "documento" in response.json()["detail"].lower()
    assert "<html>" not in response.text
