"""Emissões e cache fiscal não disparam mais envios individuais ao contador."""

from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pytest

import app.financeiro_models  # noqa: F401 - relacionamentos da Venda usada nas rotas
from app.intnfe import emission
from app.nfe import operacional_routes
from app.services import email_service, nfe_cache_service, xml_contabilidade_service


@pytest.mark.parametrize("status", [3, 5, 7, 4])
def test_intnfe_nao_dispara_envio_individual(monkeypatch, status):
    fila = Mock()
    smtp = Mock()
    monkeypatch.setattr(xml_contabilidade_service, "enfileirar_documento", fila)
    monkeypatch.setattr(email_service, "send_email", smtp)
    monkeypatch.setattr(emission, "_remember_sequence_start", lambda *_args: None)
    venda = SimpleNamespace(
        id=87,
        tenant_id="empresa-a",
        nfe_correlation_id="correlation-87",
        nfe_tipo="nfce",
        nfe_numero=None,
        nfe_serie=None,
        nfe_chave=None,
        nfe_protocolo=None,
        nfe_xml="<xml />",
        nfe_ambiente=1,
    )
    db = SimpleNamespace(commit=Mock())
    api = SimpleNamespace(document_status=Mock(return_value={"status": status}))

    emission.reconcile(db, venda, api, connection=object(), token="test-token")

    fila.assert_not_called()
    smtp.assert_not_called()
    db.commit.assert_called_once()


@pytest.mark.parametrize(
    "provider,status",
    [
        (None, "Autorizada"),
        ("bling", "Cancelada"),
        ("bling", "Pendente"),
        ("intnfe", "autorizada"),
    ],
)
def test_cache_nao_dispara_envio_individual(monkeypatch, provider, status):
    fila = Mock()
    smtp = Mock()
    monkeypatch.setattr(xml_contabilidade_service, "enfileirar_documento", fila)
    monkeypatch.setattr(email_service, "send_email", smtp)
    consulta = SimpleNamespace(filter=lambda *_args: consulta, first=lambda: None)
    db = SimpleNamespace(new=set(), query=lambda *_args: consulta)
    db.add = db.new.add

    nfe_cache_service.upsert_nota_cache(
        db,
        "empresa-a",
        {"id": "1234", "modelo": 55, "status": status, "provedor": provider},
        source="bling_api",
    )

    fila.assert_not_called()
    smtp.assert_not_called()


@pytest.mark.parametrize(
    "status,esperado", [("Autorizada", True), ("Cancelada", True), ("Pendente", False)]
)
def test_fluxo_legado_bling_preserva_status_no_cache(monkeypatch, status, esperado):
    upsert = Mock()
    fachada = SimpleNamespace(
        _status_nota_bling=lambda _dados: status,
        _venda_usa_nfce=lambda _venda: True,
        _normalizar_nota_bling=lambda dados, modelo: {**dados, "modelo": modelo},
        upsert_nota_cache=upsert,
    )
    monkeypatch.setattr(operacional_routes, "_nfe_routes", lambda: fachada)
    db = MagicMock()
    venda = SimpleNamespace(nfe_bling_id=1234)
    dados = {"situacao": 5, "numero": 123}

    operacional_routes._registrar_status_contabil_bling(db, "empresa-a", venda, dados)

    assert upsert.call_count == int(esperado)
    if esperado:
        assert upsert.call_args.args[2]["id"] == 1234
        assert upsert.call_args.args[2]["modelo"] == 65
    db.commit.assert_not_called()


def test_falha_cache_contabil_nao_bloqueia_status_legado_bling(monkeypatch):
    fachada = SimpleNamespace(
        _status_nota_bling=lambda _dados: "Autorizada",
        _venda_usa_nfce=lambda _venda: False,
        _normalizar_nota_bling=lambda dados, modelo: dados,
        upsert_nota_cache=Mock(side_effect=RuntimeError("cache indisponivel")),
    )
    monkeypatch.setattr(operacional_routes, "_nfe_routes", lambda: fachada)

    operacional_routes._registrar_status_contabil_bling(
        MagicMock(), "empresa-a", SimpleNamespace(nfe_bling_id=1234), {"situacao": 5}
    )
