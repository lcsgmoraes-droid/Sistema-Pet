"""Emissões e eventos priorizam a fila local sem bloquear o fluxo fiscal."""

from types import SimpleNamespace
from contextlib import nullcontext
from unittest.mock import MagicMock, Mock

import pytest

import app.financeiro_models  # noqa: F401 - relacionamentos da Venda usada nas rotas
from app.intnfe import emission
from app.services import (
    email_service,
    nfe_cache_service,
    xml_contabilidade_service,
    xml_contabilidade_hook,
)


@pytest.mark.parametrize("status", [3, 5, 7, 4])
def test_intnfe_autorizada_e_cancelada_priorizam_fila_sem_smtp(monkeypatch, status):
    fila = Mock()
    smtp = Mock()
    monkeypatch.setattr(emission, "tentar_enfileirar_documento", fila)
    monkeypatch.setattr(email_service, "send_email", smtp)
    monkeypatch.setattr(emission, "_remember_sequence_start", lambda *_args: None)
    venda = SimpleNamespace(
        id=87,
        tenant_id="empresa-a",
        status="cancelada",
        nfe_status=None,
        nfe_correlation_id="correlation-87",
        nfe_tipo="nfce",
        nfe_numero=None,
        nfe_serie=None,
        nfe_chave=None,
        nfe_protocolo=None,
        nfe_xml="<xml />",
        nfe_ambiente=1,
    )
    db = SimpleNamespace(commit=Mock(), no_autoflush=nullcontext(), refresh=Mock())
    api = SimpleNamespace(
        document_status=Mock(return_value={"status": status}),
        document_events=Mock(return_value=[]),
    )

    emission.reconcile(db, venda, api, connection=object(), token="test-token")

    assert fila.call_count == int(status in {3, 5})
    if status in {3, 5}:
        fila.assert_called_once_with(db, "empresa-a", "intnfe", 87)
    smtp.assert_not_called()
    assert venda.status == "cancelada"
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
def test_cache_importado_nao_prioriza_fila_contabil_nem_envia_email(
    monkeypatch, provider, status
):
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


@pytest.mark.parametrize("provider", [None, "bling", "outro"])
def test_hook_recusa_origem_importada_antes_de_tocar_transacao(monkeypatch, provider):
    enfileirar = Mock()
    monkeypatch.setattr(xml_contabilidade_service, "enfileirar_documento", enfileirar)
    db = MagicMock()
    xml_contabilidade_hook.tentar_enfileirar_documento(db, "empresa-a", provider, 87)
    enfileirar.assert_not_called()
    db.begin_nested.assert_not_called()
    db.flush.assert_not_called()


def test_hook_savepoint_preserva_transacao_fiscal_se_fila_falha(monkeypatch):
    enfileirar = Mock(side_effect=RuntimeError("token-nao-expor"))
    monkeypatch.setattr(xml_contabilidade_service, "enfileirar_documento", enfileirar)
    db = MagicMock()
    xml_contabilidade_hook.tentar_enfileirar_documento(db, "empresa-a", "intnfe", 87)
    db.begin_nested.assert_called_once()
    db.rollback.assert_not_called()
    db.commit.assert_not_called()


def test_hook_enfileira_e_flush_sem_commit_ou_smtp(monkeypatch):
    enfileirar = Mock()
    monkeypatch.setattr(xml_contabilidade_service, "enfileirar_documento", enfileirar)
    db = MagicMock()
    xml_contabilidade_hook.tentar_enfileirar_documento(db, "empresa-a", "intnfe", 87)
    enfileirar.assert_called_once_with(db, "empresa-a", "intnfe", 87)
    db.flush.assert_called_once()
    db.commit.assert_not_called()
