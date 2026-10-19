"""A fila contábil acompanha a nota sem tornar a emissão dependente dela."""

import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

import app.financeiro_models  # noqa: F401 - relacionamentos da Venda usada nas rotas
from app.intnfe import emission
from app.nfe import operacional_routes
from app.services import nfe_cache_service, xml_contabilidade_hook


@pytest.mark.parametrize("status,esperado", [(3, True), (5, True), (7, False), (4, False)])
def test_intnfe_enfileira_apenas_autorizacao_e_cancelamento(monkeypatch, status, esperado):
    fila = Mock()
    monkeypatch.setattr(emission, "tentar_enfileirar_documento", fila)
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

    if esperado:
        fila.assert_called_once_with(db, "empresa-a", "intnfe", 87)
    else:
        fila.assert_not_called()
    db.commit.assert_called_once()


@pytest.mark.parametrize(
    "provider,status,esperado",
    [
        (None, "Autorizada", True),
        ("bling", "Cancelada", True),
        ("bling", "Pendente", False),
        ("intnfe", "autorizada", False),
    ],
)
def test_cache_enfileira_notas_bling_sem_duplicar_intnfe(
    monkeypatch, provider, status, esperado
):
    fila = Mock()
    monkeypatch.setattr(nfe_cache_service, "tentar_enfileirar_documento", fila)
    consulta = SimpleNamespace(filter=lambda *_args: consulta, first=lambda: None)
    db = SimpleNamespace(new=set(), query=lambda *_args: consulta)
    db.add = db.new.add

    nfe_cache_service.upsert_nota_cache(
        db,
        "empresa-a",
        {"id": "1234", "modelo": 55, "status": status, "provedor": provider},
        source="bling_api",
    )

    if esperado:
        fila.assert_called_once_with(db, "empresa-a", "bling", "1234")
    else:
        fila.assert_not_called()


@pytest.mark.parametrize("falha_sql", [False, True])
def test_falha_fila_preserva_nota_e_sessao(monkeypatch, caplog, falha_sql):
    engine = create_engine("sqlite://")
    with Session(engine) as db:
        db.execute(text("CREATE TABLE notas (id INTEGER PRIMARY KEY)"))
        db.execute(text("CREATE TABLE fila (id INTEGER PRIMARY KEY)"))
        db.commit()
        db.execute(text("INSERT INTO notas (id) VALUES (1)"))

        def enfileirar(*_args):
            db.execute(text("INSERT INTO fila (id) VALUES (1)"))
            if falha_sql:
                db.execute(text("SELECT * FROM tabela_migration_ainda_nao_instalada"))
            raise RuntimeError("credencial-privada-nao-deve-aparecer")

        monkeypatch.setitem(
            sys.modules,
            "app.services.xml_contabilidade_service",
            SimpleNamespace(enfileirar_documento=enfileirar),
        )
        xml_contabilidade_hook.tentar_enfileirar_documento(db, "empresa-a", "intnfe", 1)
        db.commit()

        assert db.execute(text("SELECT count(*) FROM notas")).scalar_one() == 1
        assert db.execute(text("SELECT count(*) FROM fila")).scalar_one() == 0
        assert "credencial-privada" not in caplog.text
        assert "Falha ao enfileirar XML contábil" in caplog.text
    engine.dispose()


@pytest.mark.parametrize("status,esperado", [("Autorizada", True), ("Cancelada", True), ("Pendente", False)])
def test_fluxo_legado_bling_usa_mesma_fila_por_meio_do_cache(monkeypatch, status, esperado):
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
