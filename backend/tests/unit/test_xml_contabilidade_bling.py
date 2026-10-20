from datetime import date
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.services import xml_contabilidade_bling as bling
from app.services.xml_contabilidade_service import XmlContabilidadeError

CNPJ = "33590794000140"
CHAVE = f"352610{CNPJ}550030000000441241595909"


@pytest.fixture
def contexto(monkeypatch):
    monkeypatch.setattr(bling, "get_bling_connection", lambda *_a, **_k: object())
    monkeypatch.setattr(bling, "tenant_pode_usar_bling_global", lambda *_: False)
    monkeypatch.setattr(bling, "_normalizar_nota_bling", lambda row, **_: row)
    monkeypatch.setattr(bling, "_cnpj_empresa", lambda *_: CNPJ)
    upsert = Mock()
    monkeypatch.setattr(bling, "upsert_nota_cache", upsert)
    return Mock(), uuid4(), upsert


def test_consulta_todas_paginas_dos_dois_modelos(contexto, monkeypatch):
    db, tenant, upsert = contexto
    api = Mock()
    calls = []

    def request(_method, endpoint, data):
        calls.append((endpoint, data))
        if endpoint == "/nfe" and data["pagina"] == 1 and "situacao" not in data:
            return {"data": [{"id": i} for i in range(1, 101)]}
        if endpoint == "/nfe" and data["pagina"] == 2 and "situacao" not in data:
            return {"data": [{"id": 101}]}
        return {"data": []}

    api._request.side_effect = request
    construir = Mock(return_value=api)
    monkeypatch.setattr(bling, "BlingAPI", construir)
    bling.sincronizar_periodo_bling(db, tenant, date(2026, 10, 1), date(2026, 10, 19))
    construir.assert_called_once_with(tenant_id=tenant)
    assert upsert.call_count == 101
    assert [(ep, params["pagina"], params.get("situacao")) for ep, params in calls] == [
        ("/nfe", 1, None),
        ("/nfe", 2, None),
        ("/nfe", 1, 2),
        ("/nfce", 1, None),
        ("/nfce", 1, 2),
    ]
    assert calls[0][1]["dataEmissaoInicial"] == "2026-10-01 00:00:00"
    assert calls[0][1]["dataEmissaoFinal"] == "2026-10-19 23:59:59"
    assert all(params["tipo"] == 1 for ep, params in calls if ep == "/nfe")
    assert all("tipo" not in params for ep, params in calls if ep == "/nfce")


def test_canceladas_dos_dois_modelos_sao_buscadas_mesmo_fora_da_lista_padrao(
    contexto, monkeypatch
):
    db, tenant, upsert = contexto
    api = Mock()

    def request(_method, endpoint, data):
        documento_id = (100 if endpoint == "/nfe" else 200) + (
            2 if data.get("situacao") == 2 else 1
        )
        return {"data": [{"id": documento_id, "situacao": data.get("situacao", 5)}]}

    api._request.side_effect = request
    monkeypatch.setattr(bling, "BlingAPI", lambda **_: api)
    bling.sincronizar_periodo_bling(db, tenant, date(2026, 10, 1), date(2026, 10, 19))
    assert {call.args[2]["id"] for call in upsert.call_args_list} == {
        101,
        102,
        201,
        202,
    }
    assert sum(call.args[2]["situacao"] == 2 for call in upsert.call_args_list) == 2


def test_cancelada_presente_nas_duas_consultas_nao_duplica_nem_estoura_limite(
    contexto, monkeypatch
):
    db, tenant, upsert = contexto
    api = Mock()
    api._request.return_value = {"data": [{"id": 123, "situacao": 2}]}
    monkeypatch.setattr(bling, "BlingAPI", lambda **_: api)
    # Mesmo ID nos dois modelos são documentos distintos; repetição entre a
    # consulta padrão e situacao=2 do mesmo modelo é a mesma nota.
    monkeypatch.setattr("app.services.xml_contabilidade_service.MAX_DOCUMENTOS", 2)
    bling.sincronizar_periodo_bling(db, tenant, date(2026, 10, 1), date(2026, 10, 19))
    assert upsert.call_count == 2


def test_cache_preserva_payload_original_da_lista(contexto, monkeypatch):
    db, tenant, upsert = contexto
    raw = {"id": 123, "situacao": 5, "tipo": 1, "xml": "campo-futuro"}
    api = Mock()
    api._request.side_effect = [
        {"data": [raw]},
        {"data": []},
        {"data": []},
        {"data": []},
    ]
    monkeypatch.setattr(bling, "BlingAPI", lambda **_: api)
    monkeypatch.setattr(bling, "_normalizar_nota_bling", lambda *_a, **_k: {"id": 123})
    bling.sincronizar_periodo_bling(db, tenant, date(2026, 10, 1), date(2026, 10, 19))
    assert upsert.call_args.kwargs["resumo_payload"] is raw


def test_cancelada_entre_consultas_atualiza_status_sem_contar_duas_notas(
    contexto, monkeypatch
):
    db, tenant, upsert = contexto
    api = Mock()
    api._request.side_effect = [
        {"data": [{"id": 123, "situacao": 5}]},
        {"data": [{"id": 123, "situacao": 2}]},
        {"data": []},
        {"data": []},
    ]
    monkeypatch.setattr(bling, "BlingAPI", lambda **_: api)
    monkeypatch.setattr("app.services.xml_contabilidade_service.MAX_DOCUMENTOS", 1)
    bling.sincronizar_periodo_bling(db, tenant, date(2026, 10, 1), date(2026, 10, 19))
    assert [call.args[2]["situacao"] for call in upsert.call_args_list] == [5, 2]


def test_fornecedores_e_entradas_ficam_fora_antes_do_limite(contexto, monkeypatch):
    db, tenant, upsert = contexto
    api = Mock()
    chave_fornecedor = CHAVE[:6] + "12345678000195" + CHAVE[20:]
    assert len(CHAVE) == len(chave_fornecedor) == 44
    api._request.side_effect = [
        {
            "data": [
                {"id": 1, "tipo": 0, "chaveAcesso": CHAVE},
                {"id": 2, "tipo": 1, "chaveAcesso": chave_fornecedor},
                {"id": 3, "tipo": 1, "chaveAcesso": CHAVE},
            ]
        },
        {"data": []},
        {"data": []},
        {"data": []},
    ]
    monkeypatch.setattr(bling, "BlingAPI", lambda **_: api)
    monkeypatch.setattr("app.services.xml_contabilidade_service.MAX_DOCUMENTOS", 1)
    bling.sincronizar_periodo_bling(db, tenant, date(2026, 10, 1), date(2026, 10, 19))
    assert [call.args[2]["id"] for call in upsert.call_args_list] == [3]


@pytest.mark.parametrize("chave", [None, "chave-inválida"])
def test_chave_incompleta_nao_descarta_nota_sem_validacao_xml(
    contexto, monkeypatch, chave
):
    db, tenant, upsert = contexto
    api = Mock()
    api._request.side_effect = [
        {"data": [{"id": 1, "tipo": 1, "chaveAcesso": chave}]},
        {"data": []},
        {"data": []},
        {"data": []},
    ]
    monkeypatch.setattr(bling, "BlingAPI", lambda **_: api)
    bling.sincronizar_periodo_bling(db, tenant, date(2026, 10, 1), date(2026, 10, 19))
    assert upsert.call_count == 1


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
