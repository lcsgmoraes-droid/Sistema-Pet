"""Notas de fornecedores não consomem limites nem consultas fiscais de saída."""

from datetime import date, datetime
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
from app.tenancy.context import tenant_context
from app.vendas_models import Venda

CNPJ = "33590794000140"
FORNECEDOR = "12345678000195"
DIA = date(2026, 9, 3)


@pytest.fixture
def banco():
    tenant = uuid4()
    engine = create_engine("sqlite://")
    for model in (Tenant, Venda, BlingNotaFiscalCache):
        model.__table__.create(engine)
    with tenant_context(tenant), Session(engine, expire_on_commit=False) as db:
        db.add(
            Tenant(
                id=str(tenant),
                name="Empresa fictícia",
                name_normalized="empresa-ficticia",
                cnpj=CNPJ,
            )
        )
        db.commit()
        yield db, tenant
    engine.dispose()


def chave(cnpj, numero):
    return f"352609{cnpj}55003{numero:09d}1000000010"


def incluir(db, tenant, origem, numero, key):
    if origem == "cache_bling":
        obj = BlingNotaFiscalCache(
            tenant_id=tenant,
            bling_id=str(numero),
            provider="bling",
            modelo=55,
            status="autorizada",
            chave=key,
            data_emissao=datetime(2026, 9, 3, 12),
        )
    else:
        obj = Venda(
            tenant_id=tenant,
            numero_venda=f"V{numero}",
            vendedor_id=1,
            user_id=1,
            subtotal=1,
            total=1,
            nfe_provider="intnfe" if origem == "venda_intnfe" else "bling",
            nfe_bling_id=None if origem == "venda_intnfe" else numero,
            nfe_ambiente=1,
            nfe_modelo="55",
            nfe_status="autorizada",
            nfe_chave=key,
            nfe_data_emissao=datetime(2026, 9, 3, 12),
        )
    db.add(obj)
    return obj


def xml_saida(key):
    return f"""<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe"><NFe><infNFe Id="NFe{key}"><ide><mod>55</mod><dhEmi>2026-09-03T12:00:00-03:00</dhEmi><tpAmb>1</tpAmb><tpNF>1</tpNF></ide><emit><CNPJ>{CNPJ}</CNPJ></emit></infNFe></NFe><protNFe><infProt><chNFe>{key}</chNFe><cStat>100</cStat></infProt></protNFe></nfeProc>""".encode()


@pytest.mark.parametrize("origem", ["cache_bling", "venda_bling", "venda_intnfe"])
def test_fornecedores_excluidos_antes_dos_limites_e_consultas(
    banco, monkeypatch, origem
):
    db, tenant = banco
    for numero in range(1, 1002):
        incluir(db, tenant, origem, numero, chave(FORNECEDOR, numero))
    saidas = {
        chave(CNPJ, numero): incluir(db, tenant, origem, numero, chave(CNPJ, numero))
        for numero in range(1002, 1005)
    }
    db.commit()
    monkeypatch.setattr(individual, "MAX_MONITOR_DOCUMENTOS", 3)
    docs = documentos._listar_documentos(db, tenant, DIA, DIA)
    assert {doc.chave for doc in docs} == set(saidas)
    assert len(individual._referencias(db, tenant)) == 3
    obter_xml = Mock(side_effect=lambda _db, _tenant, doc: (xml_saida(doc.chave), {}))
    obter_eventos = Mock(return_value={})
    monkeypatch.setattr(documentos, "_obter_xml", obter_xml)
    monkeypatch.setattr(documentos, "_obter_eventos", obter_eventos)
    arquivos, notas = documentos._coletar_arquivos(db, tenant, docs, DIA, DIA)
    assert len(arquivos) == len(notas) == 3
    assert obter_xml.call_count == obter_eventos.call_count == 3


@pytest.mark.parametrize("origem", ["cache_bling", "venda_bling", "venda_intnfe"])
def test_chaves_desconhecidas_continuam_para_validacao_final(banco, origem):
    db, tenant = banco
    desconhecidas = [None, "", " ", "123", "X" * 44, chave(FORNECEDOR, 7)[:-1] + "X"]
    for numero, key in enumerate(desconhecidas, 1):
        incluir(db, tenant, origem, numero, key)
    incluir(db, tenant, origem, 20, chave(FORNECEDOR, 20))
    db.commit()
    docs = documentos._listar_documentos(db, tenant, DIA, DIA)
    assert len(docs) == len(individual._referencias(db, tenant)) == len(desconhecidas)
    assert {doc.chave for doc in docs} == {key or "" for key in desconhecidas}


def test_chave_invalida_nao_e_ocultada_como_nota_de_fornecedor(banco, monkeypatch):
    db, tenant = banco
    key = chave(FORNECEDOR, 1)[:-1] + "X"
    incluir(db, tenant, "cache_bling", 1, key)
    db.commit()
    docs = documentos._listar_documentos(db, tenant, DIA, DIA)
    monkeypatch.setattr(documentos, "_obter_xml", lambda *_: (xml_saida(key), {}))
    with pytest.raises(documentos.XmlContabilidadeError, match="chave/modelo"):
        documentos._coletar_arquivos(db, tenant, docs, DIA, DIA)
