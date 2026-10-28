"""Somente emissões CorePet em produção são elegíveis à contabilidade."""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import base as _registry  # noqa: F401
from app.nfe_cache_models import BlingNotaFiscalCache
from app.services import xml_contabilidade_documentos as documentos
from app.services import xml_contabilidade_eventos as eventos
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


def _venda(db, tenant, **campos):
    dados = {
        "tenant_id": tenant,
        "numero_venda": "V1",
        "vendedor_id": 1,
        "user_id": 1,
        "subtotal": 1,
        "total": 1,
        "nfe_bling_id": 123,
        "nfe_modelo": "55",
        "nfe_chave": CHAVE,
        "nfe_data_emissao": datetime(2026, 9, 3, 12),
        "nfe_provider": "intnfe",
        "nfe_status": "autorizada",
        "nfe_ambiente": 1,
        "nfe_correlation_id": "emissao-corepet-1",
    }
    dados.update(campos)
    with tenant_context(tenant):
        obj = Venda(**dados)
        db.add(obj)
        db.commit()
        return obj


@pytest.mark.parametrize("provider", [None, "bling"])
@pytest.mark.parametrize("status", ["autorizada", "cancelada", "cancelado"])
def test_venda_bling_ou_legada_mesmo_cnpj_nao_e_emissao_corepet(
    banco, provider, status
):
    tenant = uuid4()
    obj = _venda(banco, tenant, nfe_provider=provider, nfe_status=status)
    with tenant_context(tenant):
        assert _documento(banco, tenant, "bling", "123") is None
        assert _documento(banco, tenant, "intnfe", str(obj.id)) is None


@pytest.mark.parametrize("provider", [None, "bling", "intnfe"])
def test_cache_importado_mesmo_cnpj_nunca_e_origem_de_emissao_corepet(banco, provider):
    tenant = uuid4()
    with tenant_context(tenant):
        banco.add(
            BlingNotaFiscalCache(
                tenant_id=tenant,
                bling_id="123",
                provider=provider,
                chave=CHAVE,
                modelo=55,
                status="autorizada",
                data_emissao=datetime(2026, 9, 3, 12),
            )
        )
        banco.commit()
        assert _documento(banco, tenant, "bling", "123") is None
        assert _documento(banco, tenant, "intnfe", "123") is None


@pytest.mark.parametrize("status", ["autorizada", "cancelada", "cancelado"])
def test_emissao_corepet_legal_em_producao_e_encontrada(banco, status):
    tenant = uuid4()
    obj = _venda(banco, tenant, nfe_status=status)
    with tenant_context(tenant):
        documento = _documento(banco, tenant, "intnfe", str(obj.id))
    assert documento.venda is obj
    assert documento.provider == "intnfe"
    assert documento.documento_id == str(obj.id)
    assert documento.chave == CHAVE
    assert documento.status == ("cancelada" if status == "cancelado" else status)


@pytest.mark.parametrize(
    "campos",
    [
        {"nfe_status": "processando"},
        {"nfe_status": "rejeitada"},
        {"nfe_ambiente": 2},
        {"nfe_data_emissao": None},
    ],
)
def test_documento_sem_emissao_corepet_confirmada_nao_e_elegivel(banco, campos):
    tenant = uuid4()
    obj = _venda(banco, tenant, **campos)
    with tenant_context(tenant):
        assert _documento(banco, tenant, "intnfe", str(obj.id)) is None


@pytest.mark.parametrize("correlacao", [None, "", " "])
def test_corepet_sem_correlacao_permanece_candidato_mas_bloqueia_eventos(
    banco, monkeypatch, correlacao
):
    from app.intnfe import client

    tenant = uuid4()
    obj = _venda(banco, tenant, nfe_correlation_id=correlacao)
    rede = Mock(side_effect=AssertionError("Referência incompleta não usa rede"))
    monkeypatch.setattr(client, "IntNFeClient", rede)
    with tenant_context(tenant):
        documento = _documento(banco, tenant, "intnfe", str(obj.id))
        assert documento.venda is obj
        with pytest.raises(documentos.XmlContabilidadeError):
            eventos.obter_eventos_intnfe(banco, tenant, documento)
    rede.assert_not_called()


def test_documento_corepet_respeita_empresa_da_venda(banco):
    tenant_a, tenant_b = uuid4(), uuid4()
    obj = _venda(banco, tenant_a)
    with tenant_context(tenant_a):
        assert _documento(banco, tenant_a, "intnfe", str(obj.id)).venda is obj
    with tenant_context(tenant_b):
        assert _documento(banco, tenant_b, "intnfe", str(obj.id)) is None


@pytest.mark.parametrize("provider", [None, "bling"])
def test_fila_individual_legada_nao_consulta_xml_nem_prepara_anexo(
    banco, monkeypatch, provider
):
    tenant = uuid4()
    obj = _venda(banco, tenant, nfe_provider=provider)
    obter_xml = Mock(side_effect=AssertionError("Não consultar XML importado"))
    monkeypatch.setattr(documentos, "_obter_xml", obter_xml)
    envio = SimpleNamespace(
        idempotency_key=f"nota:{CHAVE}", provider=provider, documento_id=str(obj.id)
    )
    with tenant_context(tenant), pytest.raises(documentos.XmlContabilidadeError):
        preparar_anexos_individual(banco, tenant, envio)
    obter_xml.assert_not_called()
