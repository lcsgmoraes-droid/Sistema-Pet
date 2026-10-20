"""Vendas Bling anteriores ao cache continuam acessíveis ao monitor contábil."""

from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import base as _registry  # noqa: F401
from app.nfe_cache_models import BlingNotaFiscalCache
from app.services import xml_contabilidade_documentos as documentos
from app.services.xml_contabilidade_documentos import _documento
from app.services.xml_contabilidade_individual import preparar_anexos_individual
from app.tenancy.context import tenant_context
from app.vendas_models import Venda

CHAVE = "35261033590794000140550030000000441241595909"


@pytest.fixture
def banco():
    engine = create_engine("sqlite://")
    Venda.__table__.create(engine)
    BlingNotaFiscalCache.__table__.create(engine)
    with Session(engine, expire_on_commit=False) as db:
        yield db
    engine.dispose()


def _venda(db, tenant, *, chave=CHAVE, **campos):
    with tenant_context(tenant):
        obj = Venda(
            tenant_id=tenant,
            numero_venda="V1",
            vendedor_id=1,
            user_id=1,
            subtotal=1,
            total=1,
            nfe_bling_id=123,
            nfe_modelo="55",
            nfe_chave=chave,
            nfe_data_emissao=datetime(2026, 9, 3, 12),
            **campos,
        )
        db.add(obj)
        db.commit()
        return obj


@pytest.mark.parametrize("provider", [None, "bling"])
@pytest.mark.parametrize("status", ["autorizada", "cancelada", "cancelado"])
def test_nota_bling_sem_cache_e_encontrada_para_monitorar_eventos(
    banco, provider, status
):
    tenant = uuid4()
    obj = _venda(banco, tenant, nfe_provider=provider, nfe_status=status)
    with tenant_context(tenant):
        documento = _documento(banco, tenant, "bling", "123")
    assert documento is not None
    assert documento.venda is obj
    assert documento.cache is None
    assert documento.provider == "bling"
    assert documento.documento_id == "123"
    assert documento.chave == obj.nfe_chave
    assert documento.status == ("cancelada" if status == "cancelado" else status)


@pytest.mark.parametrize(
    "provider,status",
    [("intnfe", "autorizada"), ("bling", "processando"), ("bling", "rejeitada")],
)
def test_fallback_nao_inclui_outro_provedor_ou_status_invalido(banco, provider, status):
    tenant = uuid4()
    _venda(banco, tenant, nfe_provider=provider, nfe_status=status)
    with tenant_context(tenant):
        assert _documento(banco, tenant, "bling", "123") is None


def test_fallback_bling_respeita_empresa_mesmo_com_id_compartilhado(banco):
    tenant_a, tenant_b, tenant_sem_nota = uuid4(), uuid4(), uuid4()
    nota_a = _venda(banco, tenant_a, nfe_provider="bling", nfe_status="autorizada")
    nota_b = _venda(banco, tenant_b, nfe_provider="bling", nfe_status="cancelada")
    for tenant, esperada in [(tenant_a, nota_a), (tenant_b, nota_b)]:
        with tenant_context(tenant):
            assert _documento(banco, tenant, "bling", "123").venda is esperada
    with tenant_context(tenant_sem_nota):
        assert _documento(banco, tenant_sem_nota, "bling", "123") is None


def test_envio_individual_resolve_chave_bling_ausente_antes_de_validar_identidade(
    banco, monkeypatch
):
    tenant = uuid4()
    nota = _venda(
        banco, tenant, chave=None, nfe_provider="bling", nfe_status="autorizada"
    )
    cnpj = CHAVE[6:20]
    xml = f"""<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe"><NFe><infNFe Id="NFe{CHAVE}"><ide><mod>55</mod><dhEmi>2026-09-03T12:00:00-03:00</dhEmi><tpAmb>1</tpAmb><tpNF>1</tpNF></ide><emit><CNPJ>{cnpj}</CNPJ></emit></infNFe></NFe><protNFe><infProt><chNFe>{CHAVE}</chNFe><cStat>100</cStat></infProt></protNFe></nfeProc>""".encode()

    def obter_xml(_db, _tenant, doc):
        # O provedor retorna a chave no detalhe quando o registro antigo não a
        # possui. É o mesmo preenchimento feito por _obter_xml em produção.
        doc.chave = CHAVE
        return xml, {}

    monkeypatch.setattr(documentos, "_obter_xml", obter_xml)
    monkeypatch.setattr(documentos, "_cnpj_empresa", lambda *_: cnpj)
    envio = SimpleNamespace(
        idempotency_key=f"nota:{CHAVE}", provider="bling", documento_id="123"
    )
    with tenant_context(tenant):
        anexos, nome, quantidade = preparar_anexos_individual(banco, tenant, envio)
    assert anexos[0]["content"] == xml
    assert nome == f"{CHAVE}-nfe.xml"
    assert quantidade == 1
    assert nota.nfe_chave is None
