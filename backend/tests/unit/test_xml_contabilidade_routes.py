from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.security import permissions_decorator
from app import xml_contabilidade_routes as routes


@pytest.fixture
def contexto(monkeypatch):
    tenant = uuid4()
    db = Mock()
    app = FastAPI()
    app.include_router(routes.router)
    app.dependency_overrides[get_session] = lambda: db
    app.dependency_overrides[get_current_user_and_tenant] = lambda: (
        SimpleNamespace(id=7),
        tenant,
    )
    permissao = Mock()
    monkeypatch.setattr(permissions_decorator, "check_permission", permissao)
    monkeypatch.setattr(routes, "log_action", Mock())
    with TestClient(app) as client:
        yield client, db, tenant, permissao


def test_download_transmite_zip_com_tenant_e_sem_cache(contexto, monkeypatch):
    client, db, tenant, permissao = contexto
    gerar = Mock(return_value=(b"PK-xml", "xmls_2026-10.zip", 2))
    monkeypatch.setattr(routes.service, "gerar_zip_periodo", gerar)
    response = client.post(
        "/contabilidade/xml/lotes/download",
        json={
            "data_inicio": "2026-10-01",
            "data_fim": "2026-10-19",
        },
    )
    assert response.status_code == 200
    assert response.content == b"PK-xml"
    assert response.headers["content-type"] == "application/zip"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-quantidade-notas"] == "2"
    gerar.assert_called_once_with(db, tenant, date(2026, 10, 1), date(2026, 10, 19))
    assert permissao.call_args.args[2:4] == ("configuracoes.editar", tenant)


def test_usuario_sem_permissao_nao_exporta_xml(contexto, monkeypatch):
    client, _, _, permissao = contexto
    permissao.side_effect = HTTPException(403, "Sem permissão")
    gerar = Mock()
    monkeypatch.setattr(routes.service, "gerar_zip_periodo", gerar)
    response = client.post(
        "/contabilidade/xml/lotes/download",
        json={
            "data_inicio": "2026-10-01",
            "data_fim": "2026-10-19",
        },
    )
    assert response.status_code == 403
    gerar.assert_not_called()


def test_erro_negocio_retorna_mensagem_e_codigo_ao_usuario(contexto, monkeypatch):
    client, *_ = contexto
    monkeypatch.setattr(
        routes.service,
        "cancelar_envio",
        Mock(
            side_effect=routes.service.XmlContabilidadeError(
                "Envio não encontrado nesta empresa.", 404
            )
        ),
    )
    response = client.post("/contabilidade/xml/envios/99/cancelar")
    assert response.status_code == 404
    assert response.json()["detail"] == "Envio não encontrado nesta empresa."


@pytest.mark.parametrize(
    "inicio,fim", [("2026-10-19", "2026-10-01"), ("2025-01-01", "2026-10-01")]
)
def test_periodos_invalidos_nao_geram_lote(contexto, monkeypatch, inicio, fim):
    client, *_ = contexto
    gerar = Mock()
    monkeypatch.setattr(routes.service, "gerar_zip_periodo", gerar)
    assert (
        client.post(
            "/contabilidade/xml/lotes/download",
            json={
                "data_inicio": inicio,
                "data_fim": fim,
            },
        ).status_code
        == 422
    )
    gerar.assert_not_called()


@pytest.mark.parametrize(
    "agendado_para", ["2026-11-01T08:00:00", "2026-11-01T08:00:00-03:00"]
)
def test_agendamento_avulso_nao_e_aceito(contexto, monkeypatch, agendado_para):
    client, *_ = contexto
    criar = Mock()
    monkeypatch.setattr(routes.service, "criar_envio", criar)
    response = client.post(
        "/contabilidade/xml/envios",
        json={
            "data_inicio": "2026-10-01",
            "data_fim": "2026-10-19",
            "agendado_para": agendado_para,
        },
    )
    assert response.status_code == 422
    assert "mensal" in response.json()["detail"][0]["msg"]
    criar.assert_not_called()


def test_salvar_config_validacao_email_e_destinatario(contexto, monkeypatch):
    client, *_ = contexto
    salvar = Mock()
    monkeypatch.setattr(routes.service, "salvar_config", salvar)
    for payload in (
        {"email_contador": "invalido"},
        {"envio_automatico": True},
        {"envio_mensal": True},
    ):
        assert client.put("/contabilidade/xml/config", json=payload).status_code == 422
    salvar.assert_not_called()


def test_criar_envio_apenas_enfileira_e_repassa_tenant(contexto, monkeypatch):
    client, db, tenant, _ = contexto
    criar = Mock(return_value={"id": 9, "status": "pendente"})
    monkeypatch.setattr(routes.service, "criar_envio", criar)
    response = client.post(
        "/contabilidade/xml/envios",
        json={
            "data_inicio": "2026-10-01",
            "data_fim": "2026-10-19",
        },
    )
    assert response.status_code == 201
    assert response.json()["status"] == "pendente"
    assert criar.call_args.args[:2] == (db, tenant)
    assert criar.call_args.kwargs["agendado_para"] is None
