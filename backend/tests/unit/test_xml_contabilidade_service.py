import json
from datetime import date, datetime, timedelta, timezone
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4
from zipfile import ZipFile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import base as _registry  # noqa: F401
from app.nfe_cache_models import BlingNotaFiscalCache
from app.services import xml_contabilidade_service as service
from app.services import xml_contabilidade_documentos as documentos
from app.tenancy.context import tenant_context
from app.vendas_models import Venda
from app.xml_contabilidade_models import XmlContabilidadeConfig, XmlContabilidadeEnvio

CHAVE = "35261033590794000140650030000000441241595909"
CNPJ = "33590794000140"
NOW = datetime(2026, 10, 19, 15, 0, tzinfo=timezone.utc)


def xml_nota(
    chave=CHAVE,
    emissao="2026-10-19T12:00:00-03:00",
    ambiente="1",
    saida="1",
    cnpj=CNPJ,
    status="100",
):
    return f"""<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe"><NFe><infNFe Id="NFe{chave}"><ide><mod>65</mod><dhEmi>{emissao}</dhEmi><tpAmb>{ambiente}</tpAmb><tpNF>{saida}</tpNF></ide><emit><CNPJ>{cnpj}</CNPJ><xNome>Empresa teste</xNome></emit></infNFe></NFe><protNFe><infProt><chNFe>{chave}</chNFe><cStat>{status}</cStat></infProt></protNFe></nfeProc>""".encode()


def documento(xml=None, chave=CHAVE, status="autorizada", identificador="1"):
    return service.Documento(
        "intnfe",
        identificador,
        chave,
        65,
        status,
        datetime(2026, 10, 19, 12),
        venda=SimpleNamespace(
            nfe_xml=xml if xml is not None else xml_nota(chave), nfe_tipo="nfce"
        ),
    )


@pytest.fixture
def xml_context(monkeypatch):
    monkeypatch.setattr(service, "_cnpj_empresa", lambda *_: CNPJ)
    monkeypatch.setattr(documentos, "_cnpj_empresa", lambda *_: CNPJ)
    monkeypatch.setattr(service, "_agora", lambda: NOW)


@pytest.fixture
def fila(monkeypatch):
    tenant = uuid4()
    engine = create_engine("sqlite://")
    XmlContabilidadeConfig.__table__.create(engine)
    XmlContabilidadeEnvio.__table__.create(engine)
    Venda.__table__.create(engine)
    BlingNotaFiscalCache.__table__.create(engine)
    monkeypatch.setattr(service, "_agora", lambda: NOW)
    with tenant_context(tenant), Session(engine, expire_on_commit=False) as session:
        yield session, tenant
    engine.dispose()


def test_xml_data_civil_e_limites_brasilia():
    _, dia = documentos.validar_xml_saida(
        xml_nota(emissao="2026-10-20T02:59:59+00:00"), CHAVE, 65
    )
    assert dia == date(2026, 10, 19)
    _, proximo = documentos.validar_xml_saida(
        xml_nota(emissao="2026-10-20T03:00:00+00:00"), CHAVE, 65
    )
    assert proximo == date(2026, 10, 20)


@pytest.mark.parametrize("ambiente,saida", [("2", "1"), ("1", "0")])
def test_homologacao_ou_entrada_excluidas(ambiente, saida):
    assert (
        documentos.validar_xml_saida(
            xml_nota(ambiente=ambiente, saida=saida), CHAVE, 65
        )
        is None
    )


@pytest.mark.parametrize(
    "xml,chave,modelo",
    [
        (b"<invalid", CHAVE, 65),
        (xml_nota(), "0" * 44, 65),
        (xml_nota(), CHAVE, 55),
        (xml_nota(status="204"), CHAVE, 65),
    ],
)
def test_xml_invalido_chave_modelo_ou_sem_protocolo_bloqueia(xml, chave, modelo):
    with pytest.raises(service.XmlContabilidadeError):
        documentos.validar_xml_saida(xml, chave, modelo)


def test_periodo_inclusivo_xml_preservado_e_deduplicado(xml_context):
    xml = xml_nota(emissao="2026-10-20T02:59:59Z")
    doc = documento(xml)
    arquivos, notas = service._coletar_arquivos(
        Mock(), uuid4(), [doc, doc], date(2026, 10, 19), date(2026, 10, 19)
    )
    content, filename, quantidade = documentos._zip(
        arquivos, notas, date(2026, 10, 19), date(2026, 10, 19)
    )
    assert quantidade == 1
    assert filename == "xml-saida-20261019-20261019.zip"
    with ZipFile(BytesIO(content)) as zipped:
        assert zipped.read(f"{CHAVE}-nfe.xml") == xml
        manifesto = json.loads(zipped.read("manifesto.json"))
        assert manifesto["quantidade_notas"] == 1
        assert manifesto["emitente_cnpj"] == CNPJ


def test_saida_fornecedor_nao_e_saida_da_empresa(xml_context):
    arquivos, notas = service._coletar_arquivos(
        Mock(),
        uuid4(),
        [documento(xml_nota(cnpj="11111111000111"))],
        date(2026, 10, 19),
        date(2026, 10, 19),
    )
    assert not arquivos and not notas
    with pytest.raises(service.XmlContabilidadeError, match="Nenhuma"):
        documentos._zip(arquivos, notas, date(2026, 10, 19), date(2026, 10, 19))


def test_xml_ausente_nunca_gera_zip_parcial(xml_context, monkeypatch):
    original = documentos._obter_xml

    def obter(db, tenant, doc):
        if doc.documento_id == "2":
            raise RuntimeError("token-secret-nao-expor")
        return original(db, tenant, doc)

    monkeypatch.setattr(documentos, "_obter_xml", obter)
    with pytest.raises(service.XmlContabilidadeError) as exc:
        service._coletar_arquivos(
            Mock(),
            uuid4(),
            [documento(), documento(chave="9" * 44, identificador="2")],
            date(2026, 10, 19),
            date(2026, 10, 19),
        )
    assert "parcial" in str(exc.value)
    assert "secret" not in str(exc.value)


def test_cancelada_sem_evento_informa_manifesto(xml_context):
    arquivos, notas = service._coletar_arquivos(
        Mock(),
        uuid4(),
        [documento(status="cancelada")],
        date(2026, 10, 19),
        date(2026, 10, 19),
    )
    assert arquivos[0][1] == xml_nota()
    assert "evento de cancelamento" in notas[0]["aviso"]


def test_evento_embutido_preserva_assinatura_sem_reserializar(xml_context):
    evento = f"""<procEventoNFe><evento><infEvento Id="ID110111{CHAVE}01"><tpAmb>1</tpAmb><chNFe>{CHAVE}</chNFe><tpEvento>110111</tpEvento></infEvento></evento></procEventoNFe>""".encode()
    xml = xml_nota().replace(b"</nfeProc>", evento + b"</nfeProc>")
    arquivos, notas = service._coletar_arquivos(
        Mock(),
        uuid4(),
        [documento(xml, status="cancelada")],
        date(2026, 10, 19),
        date(2026, 10, 19),
    )
    assert arquivos == [(f"{CHAVE}-nfe.xml", xml)]
    assert notas[0]["eventos_incluidos"] == 1
    assert "aviso" not in notas[0]


def test_limite_tamanho_impede_pacote(xml_context, monkeypatch):
    monkeypatch.setattr(documentos, "MAX_TOTAL_BYTES", 10)
    with pytest.raises(service.XmlContabilidadeError, match="30 MB"):
        service._coletar_arquivos(
            Mock(), uuid4(), [documento()], date(2026, 10, 19), date(2026, 10, 19)
        )


def test_mensal_ultimo_dia_do_mes_e_fuso():
    inicio = datetime(2026, 1, 31, 12, tzinfo=timezone.utc)
    assert service.proxima_data_mensal(31, "08:00", inicio) == datetime(
        2026, 2, 28, 11, tzinfo=timezone.utc
    )


def test_config_ativa_sem_varrer_historico_e_cancelar_pendentes(fila):
    db, tenant = fila
    result = service.salvar_config(
        db,
        tenant,
        {
            "email_contador": "contador@example.com",
            "envio_automatico": True,
            "envio_mensal": True,
        },
    )
    assert result["envio_automatico"] is True
    assert service.listar_envios(db, tenant) == []
    auto = XmlContabilidadeEnvio(
        tenant_id=tenant,
        origem="automatico",
        status="pendente",
        email_destino="contador@example.com",
        data_inicio=date(2026, 10, 19),
        data_fim=date(2026, 10, 19),
        proxima_tentativa_em=NOW,
    )
    db.add(auto)
    db.commit()
    service.salvar_config(db, tenant, {"email_contador": "contador@example.com"})
    assert auto.status == "cancelado"


def test_automatico_deduplica_e_ignora_nota_anterior_a_ativacao(fila, monkeypatch):
    db, tenant = fila
    service.salvar_config(
        db, tenant, {"email_contador": "contador@example.com", "envio_automatico": True}
    )
    doc = documento()
    doc.data_emissao = datetime(2026, 10, 19, 12, 1)
    monkeypatch.setattr(service, "_documento", lambda *_: doc)
    primeiro = service.enfileirar_documento(db, tenant, "intnfe", "1")
    segundo = service.enfileirar_documento(db, tenant, "intnfe", "1")
    assert primeiro.id == segundo.id
    doc.data_emissao -= timedelta(days=1)
    assert service.enfileirar_documento(db, tenant, "intnfe", "2") is None
    db.commit()
    assert len(service.listar_envios(db, tenant)) == 1


def test_agendamento_cancelamento_e_isolamento(fila):
    db, tenant = fila
    service.salvar_config(db, tenant, {"email_contador": "contador@example.com"})
    envio = service.criar_envio(
        db, tenant, date(2026, 10, 1), date(2026, 10, 18), NOW + timedelta(days=1)
    )
    assert envio["status"] == "agendado"
    outro = uuid4()
    with tenant_context(outro):
        assert service.listar_envios(db, outro) == []
        with pytest.raises(service.XmlContabilidadeError) as error:
            service.cancelar_envio(db, outro, envio["id"])
        assert error.value.status_code == 404
    assert service.cancelar_envio(db, tenant, envio["id"])["status"] == "cancelado"


def test_fila_retry_persistente_e_falha_real_sem_smtp(fila, monkeypatch):
    db, tenant = fila
    service.salvar_config(db, tenant, {"email_contador": "contador@example.com"})
    envio = service.criar_envio(db, tenant, date(2026, 10, 1), date(2026, 10, 18))
    enviar = Mock()
    monkeypatch.setattr(service.email_service, "is_email_configured", lambda: False)
    monkeypatch.setattr(service.email_service, "send_email", enviar)
    for tentativa in range(1, 4):
        now = NOW + timedelta(hours=tentativa)
        monkeypatch.setattr(service, "_agora", lambda: now)
        assert service.processar_fila_tenant(db, tenant, limite=1) == 1
        atual = service.listar_envios(db, tenant)[0]
        assert atual["tentativas"] == tentativa
    assert atual["status"] == "falhou"
    assert atual["enviado_em"] is None
    enviar.assert_not_called()
    service.salvar_config(db, tenant, {"email_contador": "novo@example.com"})
    novo = service.reenviar_envio(db, tenant, envio["id"])
    assert novo["status"] == "pendente" and novo["email_destino"] == "novo@example.com"


def test_mensal_apenas_um_envio_por_competencia(fila, monkeypatch):
    db, tenant = fila
    config = XmlContabilidadeConfig(
        tenant_id=tenant,
        email_contador="contador@example.com",
        envio_mensal=True,
        dia_envio_mensal=19,
        hora_envio_mensal="11:00",
        proximo_envio_mensal=NOW - timedelta(hours=1),
    )
    db.add(config)
    db.commit()
    service._criar_mensal_devido(db, tenant, NOW)
    service._criar_mensal_devido(db, tenant, NOW)
    envios = service.listar_envios(db, tenant)
    assert len(envios) == 1
    assert envios[0]["data_inicio"] == "2026-09-01"
    assert envios[0]["data_fim"] == "2026-09-30"


def test_auto_anexa_xml_identifica_empresa_e_nunca_simula(xml_context, monkeypatch):
    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(
        name="Minha loja", razao_social="Minha loja Ltda"
    )
    monkeypatch.setattr(service, "_documento", lambda *_: documento())
    monkeypatch.setattr(service.email_service, "is_email_configured", lambda: True)
    enviar = Mock(return_value=True)
    monkeypatch.setattr(service.email_service, "send_email", enviar)
    envio = SimpleNamespace(
        origem="automatico",
        provider="intnfe",
        documento_id="1",
        data_inicio=date(2026, 10, 19),
        data_fim=date(2026, 10, 19),
        email_destino="contador@example.com",
    )
    service._processar_envio(db, uuid4(), envio)
    kwargs = enviar.call_args.kwargs
    assert kwargs["simulate_if_unconfigured"] is False
    assert kwargs["attachments"][0]["filename"].endswith(".xml")
    assert kwargs["attachments"][0]["content"] == xml_nota()
    assert CNPJ in kwargs["subject"] and "Minha loja Ltda" in kwargs["text_body"]
    assert envio.status == "enviado"


def _venda(tenant, numero="V1", **kwargs):
    return Venda(
        tenant_id=tenant,
        numero_venda=numero,
        vendedor_id=1,
        user_id=1,
        subtotal=1,
        total=1,
        nfe_tipo="nfce",
        nfe_modelo="65",
        nfe_chave=CHAVE,
        nfe_data_emissao=datetime(2026, 10, 19, 12),
        nfe_xml=xml_nota().decode(),
        **kwargs,
    )


def test_busca_documentos_aplica_tenant_status_e_ambiente(fila):
    db, tenant = fila
    db.add(
        _venda(tenant, nfe_provider="intnfe", nfe_ambiente=1, nfe_status="autorizada")
    )
    db.add(
        _venda(
            tenant, "V2", nfe_provider="intnfe", nfe_ambiente=2, nfe_status="autorizada"
        )
    )
    db.add(
        _venda(
            tenant, "V3", nfe_provider="intnfe", nfe_ambiente=1, nfe_status="rejeitada"
        )
    )
    db.add(
        _venda(
            tenant, "V4", nfe_provider="bling", nfe_bling_id=200, nfe_status="cancelada"
        )
    )
    db.commit()
    outro = uuid4()
    with tenant_context(outro):
        db.add(
            _venda(
                outro, nfe_provider="intnfe", nfe_ambiente=1, nfe_status="autorizada"
            )
        )
        db.commit()
    docs = documentos._listar_documentos(
        db, tenant, date(2026, 10, 19), date(2026, 10, 19)
    )
    assert len(docs) == 2
    assert {doc.provider for doc in docs} == {"intnfe", "bling"}
    assert {doc.status for doc in docs} == {"autorizada", "cancelada"}


def test_nota_processando_impede_zip_incompleto(fila, monkeypatch):
    from app.services import xml_contabilidade_reconciliation as reconciliacao

    db, tenant = fila
    db.add(
        _venda(tenant, nfe_provider="intnfe", nfe_ambiente=1, nfe_status="processando")
    )
    db.commit()
    consultar = Mock()
    monkeypatch.setattr(reconciliacao, "reconciliar_pendentes", consultar)
    with pytest.raises(service.XmlContabilidadeError, match="sem confirmação"):
        documentos._confirmar_emissoes_periodo(
            db, tenant, date(2026, 10, 1), date(2026, 10, 19)
        )
    consultar.assert_called_once()


def test_pendente_confirmada_passa_guard_do_periodo(fila, monkeypatch):
    from app.services import xml_contabilidade_reconciliation as reconciliacao

    db, tenant = fila
    venda = _venda(
        tenant, nfe_provider="intnfe", nfe_ambiente=1, nfe_status="processando"
    )
    db.add(venda)
    db.commit()

    def confirmar(*_):
        venda.nfe_status = "autorizada"
        db.commit()

    monkeypatch.setattr(reconciliacao, "reconciliar_pendentes", confirmar)
    documentos._confirmar_emissoes_periodo(
        db, tenant, date(2026, 10, 1), date(2026, 10, 19)
    )


def test_xml_local_e_cache_mesma_chave_so_um_arquivo_e_ultimo_status(xml_context):
    primeira = documento()
    outra = documento(status="cancelada")
    arquivos, notas = service._coletar_arquivos(
        Mock(), uuid4(), [primeira, outra], date(2026, 10, 19), date(2026, 10, 19)
    )
    assert len(arquivos) == 1
    assert notas[0]["status"] == "cancelada"
