from datetime import date
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.services import xml_contabilidade_bling as bling
from app.services.xml_contabilidade_service import XmlContabilidadeError


@pytest.fixture
def contexto(monkeypatch):
    monkeypatch.setattr(bling, "get_bling_connection", lambda *_a, **_k: object())
    monkeypatch.setattr(bling, "tenant_pode_usar_bling_global", lambda *_: False)
    monkeypatch.setattr(bling, "_normalizar_nota_bling", lambda row, **_: row)
    upsert = Mock()
    monkeypatch.setattr(bling, "upsert_nota_cache", upsert)
    return Mock(), uuid4(), upsert


def test_consulta_todas_paginas_dos_dois_modelos(contexto, monkeypatch):
    db, tenant, upsert = contexto
    api = Mock()
    calls = []

    def request(_method, endpoint, data):
        calls.append((endpoint, data))
        if endpoint == "/nfe" and data["pagina"] == 1:
            return {"data": [{"id": i} for i in range(1, 101)]}
        if endpoint == "/nfe" and data["pagina"] == 2:
            return {"data": [{"id": 101}]}
        return {"data": []}

    api._request.side_effect = request
    construir = Mock(return_value=api)
    monkeypatch.setattr(bling, "BlingAPI", construir)
    bling.sincronizar_periodo_bling(db, tenant, date(2026, 10, 1), date(2026, 10, 19))
    construir.assert_called_once_with(tenant_id=tenant)
    assert upsert.call_count == 101
    assert [(ep, params["pagina"]) for ep, params in calls] == [
        ("/nfe", 1),
        ("/nfe", 2),
        ("/nfce", 1),
    ]
    assert calls[0][1]["dataEmissaoInicial"] == "2026-10-01 00:00:00"
    assert calls[0][1]["dataEmissaoFinal"] == "2026-10-19 23:59:59"


def test_falha_api_nao_utiliza_cache_parcial(contexto, monkeypatch):
    db, tenant, _ = contexto
    api = Mock()
    api._request.side_effect = RuntimeError("segredo-privado")
    monkeypatch.setattr(bling, "BlingAPI", lambda **_: api)
    with pytest.raises(XmlContabilidadeError, match="Nenhum ZIP parcial") as exc:
        bling.sincronizar_periodo_bling(
            db, tenant, date(2026, 10, 1), date(2026, 10, 19)
        )
    assert "segredo" not in str(exc.value)


def test_pagina_repetida_ou_malformada_nao_perde_notas(contexto, monkeypatch):
    db, tenant, _ = contexto
    api = Mock()
    api._request.return_value = {"data": [{"id": i} for i in range(1, 101)]}
    monkeypatch.setattr(bling, "BlingAPI", lambda **_: api)
    with pytest.raises(XmlContabilidadeError, match="paginação"):
        bling.sincronizar_periodo_bling(
            db, tenant, date(2026, 10, 1), date(2026, 10, 19)
        )


def test_tenant_sem_conexao_nao_consulta_bling(contexto, monkeypatch):
    db, tenant, _ = contexto
    monkeypatch.setattr(bling, "get_bling_connection", lambda *_a, **_k: None)
    api = Mock()
    monkeypatch.setattr(bling, "BlingAPI", api)
    bling.sincronizar_periodo_bling(db, tenant, date(2026, 10, 1), date(2026, 10, 19))
    api.assert_not_called()
