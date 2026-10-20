from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import base as _registry  # noqa: F401
from app.nfe_cache_models import BlingNotaFiscalCache
from app.services import xml_contabilidade_documentos as documentos
from app.services import xml_contabilidade_individual as individual
from app.services import xml_contabilidade_service as service
from app.services import xml_contabilidade_eventos as eventos_service
from app.tenancy.context import tenant_context
from app.vendas_models import Venda
from app.xml_contabilidade_models import (
    XmlContabilidadeConfig,
    XmlContabilidadeEnvio,
    XmlContabilidadeEvento,
    XmlContabilidadeMonitor,
)

CHAVE = "35261033590794000140650030000000441241595909"
CNPJ = "33590794000140"
NOW = datetime(2026, 10, 19, 15, 0, tzinfo=timezone.utc)
OBTER_EVENTOS_REAL = documentos._obter_eventos


def xml_nota(data="2026-09-03T12:00:00-03:00"):
    return f"""<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe"><NFe><infNFe Id="NFe{CHAVE}"><ide><mod>65</mod><dhEmi>{data}</dhEmi><tpAmb>1</tpAmb><tpNF>1</tpNF></ide><emit><CNPJ>{CNPJ}</CNPJ><xNome>Loja teste</xNome></emit></infNFe></NFe><protNFe><infProt><chNFe>{CHAVE}</chNFe><cStat>100</cStat></infProt></protNFe></nfeProc>""".encode()


def xml_evento(tipo="110110", seq=1, data="2026-10-19T12:01:00-03:00"):
    protocolo = f"1352600000000{seq:02d}"
    xml = f"""<?xml version="1.0"?><procEventoNFe xmlns="http://www.portalfiscal.inf.br/nfe"><evento><infEvento Id="ID{tipo}{CHAVE}{seq:02d}"><tpAmb>1</tpAmb><CNPJ>{CNPJ}</CNPJ><chNFe>{CHAVE}</chNFe><tpEvento>{tipo}</tpEvento><nSeqEvento>{seq}</nSeqEvento></infEvento><Signature xmlns="http://www.w3.org/2000/09/xmldsig#"><SignatureValue>inviolado</SignatureValue></Signature></evento><retEvento><infEvento><tpAmb>1</tpAmb><chNFe>{CHAVE}</chNFe><tpEvento>{tipo}</tpEvento><nSeqEvento>{seq}</nSeqEvento><cStat>135</cStat><nProt>{protocolo}</nProt><dhRegEvento>{data}</dhRegEvento></infEvento></retEvento></procEventoNFe>""".encode()
    return {
        "autorizado": True,
        "tipoEventoCodigo": tipo,
        "protocolo": protocolo,
        "xmlEvento": xml.decode(),
    }


@pytest.fixture
def contexto(monkeypatch):
    tenant = uuid4()
    engine = create_engine("sqlite://")
    for model in (
        XmlContabilidadeConfig,
        XmlContabilidadeEnvio,
        XmlContabilidadeEvento,
        XmlContabilidadeMonitor,
        Venda,
        BlingNotaFiscalCache,
    ):
        model.__table__.create(engine)
    monkeypatch.setattr(documentos, "_cnpj_empresa", lambda *_: CNPJ)
    monkeypatch.setattr(service, "_agora", lambda: NOW)
    eventos = []
    monkeypatch.setattr(
        documentos, "_obter_eventos", lambda *_: {"_eventos_intnfe": list(eventos)}
    )
    with tenant_context(tenant), Session(engine, expire_on_commit=False) as db:
        yield db, tenant, eventos
    engine.dispose()


def venda(db, tenant, *, recente=False):
    data = datetime(2026, 10, 19, 12, 1) if recente else datetime(2026, 9, 3, 12)
    obj = Venda(
        tenant_id=tenant,
        numero_venda="V1",
        vendedor_id=1,
        user_id=1,
        subtotal=1,
        total=1,
        nfe_provider="intnfe",
        nfe_ambiente=1,
        nfe_status="autorizada",
        nfe_correlation_id="correlacao-1",
        nfe_tipo="nfce",
        nfe_modelo="65",
        nfe_chave=CHAVE,
        nfe_data_emissao=data,
        nfe_xml=xml_nota(data.isoformat() + "-03:00").decode(),
    )
    db.add(obj)
    db.commit()
    return obj


def ativar(db, tenant):
    service.salvar_config(
        db, tenant, {"email_contador": "contador@example.com", "envio_automatico": True}
    )


def test_ativacao_nao_envia_historico_mas_evento_novo_de_nota_antiga_sim(contexto):
    db, tenant, eventos = contexto
    obj = venda(db, tenant)
    ativar(db, tenant)
    eventos.append(xml_evento(data="2026-10-19T11:59:59-03:00"))
    individual.consultar_documento(db, tenant, "intnfe", obj.id, NOW)
    db.commit()
    assert service.listar_envios(db, tenant) == []
    assert db.query(XmlContabilidadeEvento).count() == 1
    # Mesmo status da nota; a segunda CC-e cria outro registro e outro e-mail.
    eventos.append(xml_evento(seq=2))
    individual.consultar_documento(db, tenant, "intnfe", obj.id, NOW)
    individual.consultar_documento(db, tenant, "intnfe", obj.id, NOW)
    db.commit()
    envios = db.query(XmlContabilidadeEnvio).all()
    assert len(envios) == 1 and envios[0].documento_status == "evento"
    assert ":135260000000002" in envios[0].idempotency_key
    assert db.query(XmlContabilidadeEvento).count() == 2
    anexos, nome, quantidade = individual.preparar_anexos_individual(
        db, tenant, envios[0]
    )
    assert quantidade == 1 and nome.endswith("02.xml")
    assert anexos[0]["content"] == eventos[1]["xmlEvento"].encode()
    assert anexos[0]["mime_subtype"] == "xml"


def test_nota_nova_cancelamento_e_todos_eventos_cada_um_tem_identidade(contexto):
    db, tenant, eventos = contexto
    obj = venda(db, tenant, recente=True)
    ativar(db, tenant)
    eventos.extend([xml_evento(), xml_evento("110111"), xml_evento("210210")])
    original = service.enfileirar_documento(db, tenant, "intnfe", obj.id)
    assert original.idempotency_key == f"nota:{CHAVE}"
    individual.consultar_documento(db, tenant, "intnfe", obj.id, NOW)
    individual.consultar_documento(db, tenant, "intnfe", obj.id, NOW)
    db.commit()
    envios = db.query(XmlContabilidadeEnvio).all()
    assert len(envios) == 4
    assert [row.documento_status for row in envios].count("nota") == 1
    assert len({row.idempotency_key for row in envios}) == 4
    anexos, _, _ = individual.preparar_anexos_individual(db, tenant, original)
    assert anexos[0]["content"] == obj.nfe_xml.encode()


def test_hook_usa_xml_oficial_para_nao_enviar_historico_utc_naive(contexto):
    db, tenant, _ = contexto
    obj = venda(db, tenant, recente=True)
    ativar(db, tenant)
    # 14:59 UTC foi gravado sem fuso na coluna, mas é 11:59 em Brasília:
    # aconteceu antes da ativação às 15:00 UTC, mesmo no mesmo dia.
    obj.nfe_data_emissao = datetime(2026, 10, 19, 14, 59)
    obj.nfe_xml = xml_nota("2026-10-19T14:59:00+00:00").decode()
    db.commit()
    assert service.enfileirar_documento(db, tenant, "intnfe", obj.id) is None
    assert db.query(XmlContabilidadeEnvio).count() == 0
    assert db.query(XmlContabilidadeMonitor).count() == 1


def test_hook_sem_xml_local_apenas_prioriza_consulta_sem_http(contexto, monkeypatch):
    db, tenant, _ = contexto
    obj = venda(db, tenant, recente=True)
    ativar(db, tenant)
    obj.nfe_xml = None
    db.commit()
    consultar = Mock(side_effect=AssertionError("Hook nunca pode usar HTTP"))
    monkeypatch.setattr(documentos, "_obter_xml", consultar)
    assert service.enfileirar_documento(db, tenant, "intnfe", obj.id) is None
    consultar.assert_not_called()
    assert db.query(XmlContabilidadeMonitor).count() == 1


def test_desligar_cancela_pendentes_preserva_historico_e_religar_nao_reenvia(
    contexto, monkeypatch
):
    db, tenant, eventos = contexto
    obj = venda(db, tenant, recente=True)
    ativar(db, tenant)
    eventos.append(xml_evento())
    individual.consultar_documento(db, tenant, "intnfe", obj.id, NOW)
    db.commit()
    rows = db.query(XmlContabilidadeEnvio).order_by(XmlContabilidadeEnvio.id).all()
    rows[0].status = "enviado"
    db.commit()
    service.salvar_config(db, tenant, {"email_contador": "contador@example.com"})
    assert [row.status for row in rows] == ["enviado", "cancelado"]
    monkeypatch.setattr(service, "_agora", lambda: NOW + timedelta(hours=1))
    ativar(db, tenant)
    individual.consultar_documento(
        db, tenant, "intnfe", obj.id, NOW + timedelta(hours=1)
    )
    db.commit()
    assert db.query(XmlContabilidadeEnvio).count() == 2


def test_monitor_persistente_consulta_nota_antiga_sem_mudanca_de_status(contexto):
    db, tenant, eventos = contexto
    venda(db, tenant)
    ativar(db, tenant)
    assert individual.capturar_novos_eventos(db, tenant, NOW) == 1
    assert (
        service._utc(db.query(XmlContabilidadeMonitor).one().ultima_consulta_em) == NOW
    )
    eventos.append(xml_evento())
    assert (
        individual.capturar_novos_eventos(db, tenant, NOW + timedelta(minutes=1)) == 0
    )
    assert (
        individual.capturar_novos_eventos(db, tenant, NOW + timedelta(minutes=11)) == 1
    )
    assert db.query(XmlContabilidadeEnvio).one().documento_status == "evento"


def test_periodo_inclui_eventos_de_nota_antiga_com_individual_desativado(contexto):
    db, tenant, eventos = contexto
    venda(db, tenant)
    eventos.extend(
        [
            xml_evento(data="2026-09-30T23:59:59-03:00"),
            xml_evento(seq=2, data="2026-10-01T00:00:00-03:00"),
        ]
    )
    arquivos, notas = individual.coletar_eventos_periodo(
        db, tenant, date(2026, 10, 1), date(2026, 10, 31)
    )
    assert len(arquivos) == len(notas) == 1
    assert arquivos[0][1] == eventos[1]["xmlEvento"].encode()
    assert notas[0]["data_emissao"] == "2026-09-03"
    assert notas[0]["somente_eventos_periodo"] is True
    assert notas[0]["eventos"][0]["sequencia"] == 2
    assert db.query(XmlContabilidadeEnvio).count() == 0


def test_cancelamento_de_nota_antiga_e_detectado_independente_status_local(contexto):
    db, tenant, eventos = contexto
    obj = venda(db, tenant)
    ativar(db, tenant)
    eventos.append(xml_evento("110111"))
    individual.consultar_documento(db, tenant, "intnfe", obj.id, NOW)
    db.commit()
    envio = db.query(XmlContabilidadeEnvio).one()
    assert envio.documento_status == "evento" and obj.nfe_status == "autorizada"
    assert "evento:ID110111" in envio.idempotency_key
    arquivos, notas = individual.coletar_eventos_periodo(
        db, tenant, date(2026, 10, 1), date(2026, 10, 31)
    )
    assert len(arquivos) == 1 and notas[0]["status"] == "cancelada"
    assert db.query(XmlContabilidadeEnvio).count() == 1


def test_evento_incompleto_bloqueia_lote_sem_persistir_xml_parcial(contexto):
    db, tenant, eventos = contexto
    venda(db, tenant)
    eventos.append(xml_evento(seq=2))
    with pytest.raises(service.XmlContabilidadeError, match="sequência 1"):
        individual.coletar_eventos_periodo(
            db, tenant, date(2026, 10, 1), date(2026, 10, 31)
        )
    assert db.query(XmlContabilidadeEvento).count() == 0


def test_evento_de_outra_empresa_nao_pode_ser_enviado(contexto):
    db, tenant, eventos = contexto
    obj = venda(db, tenant)
    ativar(db, tenant)
    eventos.append(xml_evento())
    individual.consultar_documento(db, tenant, "intnfe", obj.id, NOW)
    db.commit()
    envio = db.query(XmlContabilidadeEnvio).one()
    with tenant_context(uuid4()):
        with pytest.raises(
            service.XmlContabilidadeError, match="CorePet|não está disponível"
        ):
            individual.preparar_anexos_individual(db, uuid4(), envio)


@pytest.mark.parametrize(
    "origem_invalida",
    ["evento_bling", "evento_orfao", "chave_divergente", "venda_bling", "envio_bling"],
)
def test_evento_individual_exige_origem_e_vinculo_com_emissao_corepet(
    contexto, origem_invalida
):
    db, tenant, _ = contexto
    obj = venda(db, tenant)
    dado = xml_evento()
    identidade = f"ID110110{CHAVE}01"
    if origem_invalida == "venda_bling":
        obj.nfe_provider = "bling"
    evento = XmlContabilidadeEvento(
        tenant_id=tenant,
        provider="bling" if origem_invalida == "evento_bling" else "intnfe",
        documento_id="999999" if origem_invalida == "evento_orfao" else str(obj.id),
        chave="9" * 44 if origem_invalida == "chave_divergente" else CHAVE,
        identidade=identidade,
        tipo="110110",
        sequencia=1,
        protocolo=dado["protocolo"],
        registrado_em=NOW,
        nome_arquivo=f"{identidade}.xml",
        xml=dado["xmlEvento"].encode(),
    )
    db.add(evento)
    db.commit()
    envio = SimpleNamespace(
        provider="bling" if origem_invalida == "envio_bling" else "intnfe",
        documento_id=str(obj.id),
        idempotency_key=f"evento:{identidade}:{dado['protocolo']}",
    )
    with pytest.raises(service.XmlContabilidadeError):
        individual.preparar_anexos_individual(db, tenant, envio)


def test_evento_importado_com_mesma_chave_corepet_nao_entra_no_lote(
    contexto, monkeypatch
):
    db, tenant, _ = contexto
    obj = venda(db, tenant)
    dado = xml_evento()
    identidade = f"ID110110{CHAVE}01"
    db.add(
        XmlContabilidadeEvento(
            tenant_id=tenant,
            provider="bling",
            documento_id=str(obj.id),
            chave=CHAVE,
            identidade=identidade,
            tipo="110110",
            sequencia=1,
            protocolo=dado["protocolo"],
            registrado_em=NOW,
            nome_arquivo=f"{identidade}.xml",
            xml=dado["xmlEvento"].encode(),
        )
    )
    db.commit()
    monkeypatch.setattr(documentos, "_obter_eventos", OBTER_EVENTOS_REAL)
    monkeypatch.setattr(eventos_service, "obter_eventos_intnfe", lambda *_: [])
    assert individual.coletar_eventos_periodo(
        db, tenant, date(2026, 10, 1), date(2026, 10, 31)
    ) == ([], [])


def test_evento_ja_recebido_permanece_no_lote_se_lista_remota_agora_omite(
    contexto, monkeypatch
):
    db, tenant, eventos = contexto
    obj = venda(db, tenant)
    monkeypatch.setattr(documentos, "_obter_eventos", OBTER_EVENTOS_REAL)
    monkeypatch.setattr(
        eventos_service, "obter_eventos_intnfe", lambda *_: list(eventos)
    )
    eventos.append(xml_evento("110111"))
    individual.consultar_documento(db, tenant, "intnfe", obj.id, NOW)
    db.commit()
    original = eventos[0]["xmlEvento"].encode()
    eventos.clear()
    arquivos, notas = individual.coletar_eventos_periodo(
        db, tenant, date(2026, 10, 1), date(2026, 10, 31)
    )
    assert len(arquivos) == 1 and arquivos[0][1] == original
    assert notas[0]["status"] == "cancelada"


def test_persistido_nao_oculta_falha_de_consulta_remota(contexto, monkeypatch):
    db, tenant, eventos = contexto
    obj = venda(db, tenant)
    monkeypatch.setattr(documentos, "_obter_eventos", OBTER_EVENTOS_REAL)
    monkeypatch.setattr(
        eventos_service, "obter_eventos_intnfe", lambda *_: list(eventos)
    )
    eventos.append(xml_evento())
    individual.consultar_documento(db, tenant, "intnfe", obj.id, NOW)
    db.commit()
    monkeypatch.setattr(
        eventos_service,
        "obter_eventos_intnfe",
        Mock(side_effect=service.XmlContabilidadeError("Consulta remota falhou", 409)),
    )
    with pytest.raises(service.XmlContabilidadeError, match="remota falhou"):
        individual.coletar_eventos_periodo(
            db, tenant, date(2026, 10, 1), date(2026, 10, 31)
        )


def test_evento_embutido_persistido_revalida_fonte_original_sem_reserializar(
    contexto, monkeypatch
):
    db, tenant, _ = contexto
    obj = venda(db, tenant)
    monkeypatch.setattr(documentos, "_obter_eventos", OBTER_EVENTOS_REAL)
    monkeypatch.setattr(eventos_service, "obter_eventos_intnfe", lambda *_: [])
    evento = (
        xml_evento("110111")["xmlEvento"].replace('<?xml version="1.0"?>', "").encode()
    )
    original = xml_nota().replace(b"</nfeProc>", evento + b"</nfeProc>")
    obj.nfe_xml = original.decode()
    db.commit()
    individual.consultar_documento(db, tenant, "intnfe", obj.id, NOW)
    db.commit()
    obj.nfe_xml = xml_nota().decode()
    db.commit()
    arquivos, notas = individual.coletar_eventos_periodo(
        db, tenant, date(2026, 10, 1), date(2026, 10, 31)
    )
    assert len(arquivos) == 1 and arquivos[0][1] == original
    assert notas[0]["status"] == "cancelada"


def test_individual_anexa_xml_sem_zip_e_sem_simular_smtp(monkeypatch):
    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(
        name="Loja", razao_social=None
    )
    monkeypatch.setattr(service, "_cnpj_empresa", lambda *_: CNPJ)
    monkeypatch.setattr(service.email_service, "is_email_configured", lambda: True)
    enviar = Mock(return_value=True)
    monkeypatch.setattr(service.email_service, "send_email", enviar)
    anexos = [
        {"filename": "evento.xml", "content": b"xml-original", "mime_subtype": "xml"}
    ]
    monkeypatch.setattr(
        individual, "preparar_anexos_individual", lambda *_: (anexos, "evento.xml", 1)
    )
    envio = SimpleNamespace(
        origem="automatico",
        provider="intnfe",
        idempotency_key="evento:ID:135260000000001",
        email_destino="contador@example.com",
    )
    service._processar_envio(db, uuid4(), envio)
    assert enviar.call_args.kwargs["attachments"] == anexos
    assert enviar.call_args.kwargs["simulate_if_unconfigured"] is False
    assert envio.status == "enviado"
