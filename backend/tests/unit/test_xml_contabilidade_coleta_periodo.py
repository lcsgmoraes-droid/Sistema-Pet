"""Lotes CorePet reaproveitam consultas e excluem dados importados do Bling."""

from collections import Counter
from datetime import date, datetime, timedelta, timezone
from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import base as _registry  # noqa: F401
from app.models import Tenant
from app.nfe_cache_models import BlingNotaFiscalCache
from app.services import xml_contabilidade_documentos as documentos
from app.services import xml_contabilidade_individual as individual
from app.services import xml_contabilidade_service as service
from app.services.xml_contabilidade_common import BRASILIA
from app.tenancy.context import tenant_context
from app.vendas_models import Venda
from app.xml_contabilidade_models import (
    XmlContabilidadeConfig,
    XmlContabilidadeEnvio,
    XmlContabilidadeEvento,
    XmlContabilidadeMonitor,
    XmlContabilidadeTentativa,
)

CNPJ = "33590794000140"
NOW = datetime(2026, 10, 19, 15, 0, tzinfo=timezone.utc)


@pytest.fixture
def banco(monkeypatch):
    tenant = uuid4()
    engine = create_engine("sqlite://")
    for model in (
        Tenant,
        Venda,
        BlingNotaFiscalCache,
        XmlContabilidadeConfig,
        XmlContabilidadeEnvio,
        XmlContabilidadeTentativa,
        XmlContabilidadeEvento,
        XmlContabilidadeMonitor,
    ):
        model.__table__.create(engine)
    monkeypatch.setattr(service, "_agora", lambda: NOW)
    with tenant_context(tenant), Session(engine, expire_on_commit=False) as db:
        db.add(
            Tenant(
                id=str(tenant),
                name="Empresa fictícia",
                name_normalized="empresa",
                cnpj=CNPJ,
            )
        )
        db.commit()
        yield db, tenant
    engine.dispose()


def nota(db, tenant, numero, *, provider="intnfe", antiga=False):
    data = datetime(2026, 9 if antiga else 10, 3, 12)
    key = f"35{data:%y%m}{CNPJ}55003{numero:09d}1000000010"
    if provider == "intnfe":
        obj = Venda(
            tenant_id=tenant,
            numero_venda=f"V{numero}",
            vendedor_id=1,
            user_id=1,
            subtotal=1,
            total=1,
            nfe_provider="intnfe",
            nfe_correlation_id=f"corepet-{numero}",
            nfe_tipo="nfe",
            nfe_ambiente=1,
            nfe_modelo="55",
            nfe_status="autorizada",
            nfe_chave=key,
            nfe_data_emissao=data,
        )
    else:
        obj = BlingNotaFiscalCache(
            tenant_id=tenant,
            bling_id=str(numero),
            provider="bling",
            modelo=55,
            status="autorizada",
            chave=key,
            data_emissao=data,
        )
    db.add(obj)
    db.commit()
    return obj, key, data


def xml_nota(key, data):
    return f"""<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe"><NFe><infNFe Id="NFe{key}"><ide><mod>55</mod><dhEmi>{data.replace(tzinfo=BRASILIA).isoformat()}</dhEmi><tpAmb>1</tpAmb><tpNF>1</tpNF></ide><emit><CNPJ>{CNPJ}</CNPJ></emit></infNFe></NFe><protNFe><infProt><chNFe>{key}</chNFe><cStat>100</cStat></infProt></protNFe></nfeProc>""".encode()


def evento(key, *, seq=1, data="2026-10-19T12:01:00-03:00", cnpj=CNPJ):
    tipo, protocolo = "110110", f"1352600000000{seq:02d}"
    identidade = f"ID{tipo}{key}{seq:02d}"
    xml = f"""<?xml version="1.0"?><procEventoNFe xmlns="http://www.portalfiscal.inf.br/nfe"><evento><infEvento Id="{identidade}"><tpAmb>1</tpAmb><CNPJ>{cnpj}</CNPJ><chNFe>{key}</chNFe><tpEvento>{tipo}</tpEvento><nSeqEvento>{seq}</nSeqEvento></infEvento></evento><retEvento><infEvento><tpAmb>1</tpAmb><chNFe>{key}</chNFe><tpEvento>{tipo}</tpEvento><nSeqEvento>{seq}</nSeqEvento><cStat>135</cStat><nProt>{protocolo}</nProt><dhRegEvento>{data}</dhRegEvento></infEvento></retEvento></procEventoNFe>""".encode()
    return {
        "row": {
            "autorizado": True,
            "tipoEventoCodigo": tipo,
            "protocolo": protocolo,
            "xmlEvento": xml,
        },
        "xml": xml,
        "identidade": identidade,
        "protocolo": protocolo,
        "nome": f"{identidade}.xml",
        "data": datetime.fromisoformat(data),
    }


def guardar_evento(db, tenant, key, ev, *, documento_id="999", seq=1, provider="bling"):
    db.add(
        XmlContabilidadeEvento(
            tenant_id=tenant,
            provider=provider,
            documento_id=documento_id,
            chave=key,
            identidade=ev["identidade"],
            tipo="110110",
            sequencia=seq,
            protocolo=ev["protocolo"],
            registrado_em=ev["data"].astimezone(timezone.utc),
            nome_arquivo=ev["nome"],
            xml=ev["xml"],
        )
    )
    db.commit()


def test_periodo_consulta_cada_documento_uma_vez_e_inclui_evento_intnfe_antigo(
    banco, monkeypatch
):
    db, tenant = banco
    modelos = [
        nota(db, tenant, 1),
        nota(db, tenant, 2),
        nota(db, tenant, 3),
        nota(db, tenant, 4, antiga=True),
    ]
    _, key_alheio, _ = nota(db, tenant, 5, provider="bling", antiga=True)
    _, key_alheio_atual, _ = nota(db, tenant, 6, provider="bling")
    xmls = {key: xml_nota(key, data) for _, key, data in modelos}
    eventos = {
        modelos[0][1]: evento(modelos[0][1]),
        modelos[3][1]: evento(modelos[3][1]),
    }
    xml_calls, event_calls = [], []

    def obter_xml(_db, _tenant, doc):
        xml_calls.append(doc.chave)
        return xmls[doc.chave], {}

    def obter_eventos(_db, _tenant, doc):
        event_calls.append(doc.chave)
        return {
            "_eventos_intnfe": [eventos[doc.chave]["row"]]
            if doc.chave in eventos
            else []
        }

    monkeypatch.setattr(documentos, "_obter_xml", obter_xml)
    monkeypatch.setattr(documentos, "_obter_eventos", obter_eventos)
    arquivos, notas = documentos._preparar_periodo(
        db, tenant, date(2026, 10, 1), date(2026, 10, 31)
    )
    assert (
        Counter(xml_calls) == Counter(event_calls) == Counter({key: 1 for key in xmls})
    )
    assert key_alheio not in xml_calls and key_alheio_atual not in xml_calls
    assert {n["chave"] for n in notas} == set(xmls)
    assert (
        dict(arquivos)[eventos[modelos[3][1]]["nome"]] == eventos[modelos[3][1]]["xml"]
    )
    assert f"{modelos[3][1]}-nfe.xml" not in dict(arquivos)
    assert db.query(XmlContabilidadeEvento).count() == 2


def test_bling_antigo_recebido_mesmo_cnpj_fica_fora_do_lote_sem_http(
    banco, monkeypatch
):
    db, tenant = banco
    key = f"352608{CNPJ}550030000009991000000010"
    antes = evento(key, data="2026-08-31T12:00:00-03:00")
    fim_mes = evento(key, seq=2, data="2026-09-30T23:59:59-03:00")
    guardar_evento(db, tenant, key, antes)
    guardar_evento(db, tenant, key, fim_mes, seq=2)
    http = Mock(side_effect=AssertionError("Não consultar legado alheio por HTTP"))
    monkeypatch.setattr(documentos, "_obter_xml", http)
    monkeypatch.setattr(documentos, "_obter_eventos", http)
    arquivos, notas = individual.coletar_eventos_periodo(
        db, tenant, date(2026, 9, 1), date(2026, 9, 30)
    )
    assert arquivos == notas == []
    http.assert_not_called()


@pytest.mark.parametrize("provider", ["bling", "intnfe"])
def test_evento_importado_ou_sem_venda_corepet_nao_e_incluido_no_lote(banco, provider):
    db, tenant = banco
    key = "35260912345678000195550030000009991000000010"
    ev = evento(key, data="2026-09-03T12:00:00-03:00", cnpj="12345678000195")
    guardar_evento(db, tenant, key, ev, provider=provider)
    assert individual.coletar_eventos_periodo(
        db, tenant, date(2026, 9, 1), date(2026, 9, 30)
    ) == ([], [])


def test_monitor_e_referencias_excluem_bling_mesmo_cnpj(banco, monkeypatch):
    db, tenant = banco
    bling_obj, _, _ = nota(db, tenant, 1, provider="bling", antiga=True)
    int_obj, _, _ = nota(db, tenant, 2, antiga=True)
    service.salvar_config(
        db, tenant, {"email_contador": "contador@example.com", "envio_automatico": True}
    )
    assert (
        individual.priorizar_documento(
            db, tenant, "bling", bling_obj.bling_id, NOW - timedelta(days=1)
        )
        is None
    )
    db.add(
        XmlContabilidadeMonitor(
            tenant_id=tenant,
            provider="bling",
            documento_id=str(bling_obj.bling_id),
            proxima_consulta_em=NOW - timedelta(days=1),
        )
    )
    db.commit()
    consultar = Mock(return_value=([], []))
    monkeypatch.setattr(individual, "consultar_documento", consultar)
    assert individual._referencias(db, tenant) == [("intnfe", str(int_obj.id))]
    assert individual.capturar_novos_eventos(db, tenant, NOW, limite=50) == 1
    consultar.assert_called_once()
    assert consultar.call_args.args[2:4] == ("intnfe", str(int_obj.id))


def test_seed_preserva_persistencia_e_idempotencia_individual_sem_reconsulta(
    banco, monkeypatch
):
    db, tenant = banco
    obj, key, _ = nota(db, tenant, 1)
    instante = NOW.astimezone(BRASILIA).replace(tzinfo=None)
    obj.nfe_data_emissao = instante
    db.commit()
    service.salvar_config(
        db, tenant, {"email_contador": "contador@example.com", "envio_automatico": True}
    )
    ev = evento(key, data=NOW.astimezone(BRASILIA).isoformat())
    xml = Mock(return_value=(xml_nota(key, instante), {}))
    eventos = Mock(return_value={"_eventos_intnfe": [ev["row"]]})
    monkeypatch.setattr(documentos, "_obter_xml", xml)
    monkeypatch.setattr(documentos, "_obter_eventos", eventos)
    for _ in range(2):
        documentos._preparar_periodo(db, tenant, date(2026, 10, 1), date(2026, 10, 31))
    assert xml.call_count == eventos.call_count == 2
    assert db.query(XmlContabilidadeEvento).count() == 1
    assert db.query(XmlContabilidadeEnvio).count() == 2


def test_falha_intnfe_antiga_continua_bloqueando_lote(banco, monkeypatch):
    db, tenant = banco
    obj, key, data = nota(db, tenant, 1, antiga=True)
    monkeypatch.setattr(documentos, "_obter_xml", lambda *_: (xml_nota(key, data), {}))
    monkeypatch.setattr(
        documentos,
        "_obter_eventos",
        Mock(
            side_effect=documentos.XmlContabilidadeError("Consulta remota falhou", 409)
        ),
    )
    with pytest.raises(documentos.XmlContabilidadeError, match="remota falhou"):
        individual.coletar_eventos_periodo(
            db, tenant, date(2026, 10, 1), date(2026, 10, 31)
        )


@pytest.mark.parametrize("provider", ["bling", "intnfe"])
def test_hook_fornecedor_sem_xml_nao_cria_monitor_nem_fila(
    banco, monkeypatch, provider
):
    db, tenant = banco
    obj, _, _ = nota(db, tenant, 1, provider=provider)
    key_fornecedor = "35260912345678000195550030000009991000000010"
    if provider == "bling":
        obj.chave = key_fornecedor
        documento_id = obj.bling_id
    else:
        obj.nfe_chave = key_fornecedor
        documento_id = obj.id
    db.commit()
    service.salvar_config(
        db, tenant, {"email_contador": "contador@example.com", "envio_automatico": True}
    )
    http = Mock(side_effect=AssertionError("Hook de fornecedor nunca consulta HTTP"))
    monkeypatch.setattr(documentos, "_obter_xml", http)
    assert service.enfileirar_documento(db, tenant, provider, documento_id) is None
    db.commit()
    assert db.query(XmlContabilidadeMonitor).count() == 0
    assert db.query(XmlContabilidadeEnvio).count() == 0
    http.assert_not_called()
