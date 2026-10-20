"""Tentativas reais em SQLite, sem SMTP/IntNFe externos e sem reescrever passado."""

from datetime import date, datetime, timedelta, timezone
from io import BytesIO
import json
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4
from zipfile import ZipFile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import base as _registry  # noqa: F401
from app.models import Tenant
from app.services import xml_contabilidade_documentos as documentos
from app.services import xml_contabilidade_relatorios as relatorios
from app.services import xml_contabilidade_service as service
from app.services import xml_contabilidade_reconciliation as reconciliacao
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
NOW = datetime(2026, 10, 19, 18, tzinfo=timezone.utc)


def xml_nota(chave, *, valor="100.50", data="2026-10-18T12:00:00-03:00"):
    total = (
        f"<total><ICMSTot><vNF>{valor}</vNF></ICMSTot></total>"
        if valor is not None
        else ""
    )
    return f'<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe"><NFe><infNFe Id="NFe{chave}"><ide><nNF>123</nNF><mod>55</mod><dhEmi>{data}</dhEmi><tpAmb>1</tpAmb><tpNF>1</tpNF></ide><emit><CNPJ>{CNPJ}</CNPJ></emit>{total}</infNFe></NFe><protNFe><infProt><chNFe>{chave}</chNFe><cStat>100</cStat></infProt></protNFe></nfeProc>'


def evento(chave, tipo="110110", seq=1):
    protocolo = f"1352600000000{seq:02d}"
    xml = f'<procEventoNFe xmlns="http://www.portalfiscal.inf.br/nfe"><evento><infEvento Id="ID{tipo}{chave}{seq:02d}"><tpAmb>1</tpAmb><CNPJ>{CNPJ}</CNPJ><chNFe>{chave}</chNFe><tpEvento>{tipo}</tpEvento><nSeqEvento>{seq}</nSeqEvento></infEvento></evento><retEvento><infEvento><tpAmb>1</tpAmb><chNFe>{chave}</chNFe><tpEvento>{tipo}</tpEvento><nSeqEvento>{seq}</nSeqEvento><cStat>135</cStat><nProt>{protocolo}</nProt><dhRegEvento>2026-10-18T13:00:00-03:00</dhRegEvento></infEvento></retEvento></procEventoNFe>'
    return {
        "autorizado": True,
        "tipoEventoCodigo": tipo,
        "protocolo": protocolo,
        "xmlEvento": xml,
    }


@pytest.fixture
def banco(monkeypatch):
    engine = create_engine("sqlite://")
    for model in (
        Tenant,
        Venda,
        XmlContabilidadeConfig,
        XmlContabilidadeEnvio,
        XmlContabilidadeEvento,
        XmlContabilidadeMonitor,
        XmlContabilidadeTentativa,
    ):
        model.__table__.create(engine)
    tenant = uuid4()
    enviar = Mock(return_value=True)
    monkeypatch.setattr(service, "_agora", lambda: NOW)
    monkeypatch.setattr(service.email_service, "is_email_configured", lambda: True)
    monkeypatch.setattr(service.email_service, "send_email", enviar)
    monkeypatch.setattr(reconciliacao, "reconciliar_pendentes", lambda *_: 0)
    monkeypatch.setattr(
        documentos, "_obter_eventos", lambda *_: {"_eventos_intnfe": []}
    )
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
        service.salvar_config(db, tenant, {"email_contador": "contador@example.com"})
        yield db, tenant, enviar
    engine.dispose()


def nota(
    db,
    tenant,
    numero=1,
    *,
    status="autorizada",
    valor="100.50",
    provider="intnfe",
    antiga=False,
):
    chave = f"352610{CNPJ}55003{numero:09d}1000000010"
    data = "2026-09-18T12:00:00-03:00" if antiga else "2026-10-18T12:00:00-03:00"
    venda = Venda(
        tenant_id=tenant,
        numero_venda=f"V{numero}",
        vendedor_id=1,
        user_id=1,
        subtotal=1,
        total=9999,
        nfe_provider=provider,
        nfe_status=status,
        nfe_ambiente=1,
        nfe_correlation_id=f"corr-{numero}",
        nfe_modelo="55",
        nfe_tipo="nfe",
        nfe_numero=str(numero),
        nfe_chave=chave,
        nfe_data_emissao=datetime.fromisoformat(data).replace(tzinfo=None),
        nfe_xml=None
        if status == "processando"
        else xml_nota(chave, valor=valor, data=data),
    )
    db.add(venda)
    db.commit()
    return venda


def executar(db, tenant):
    envio = service.criar_envio(db, tenant, date(2026, 10, 1), date(2026, 10, 19))
    assert service.processar_fila_tenant(db, tenant, limite=1) == 1
    return service.listar_envios(db, tenant)[0], relatorios.listar(
        db, tenant, envio["id"]
    )["relatorios"][0]


def detalhe(db, tenant, resumo):
    return relatorios.obter(db, tenant, resumo["envio_id"], resumo["id"])


def test_envia_autorizada_e_informa_pendente_sem_bloquear_ou_inventar_valor(banco):
    db, tenant, enviar = banco
    autorizada = nota(db, tenant)
    pendente = nota(db, tenant, 2, status="processando")
    envio, resumo = executar(db, tenant)
    assert envio["status"] == "enviado"
    assert envio["ultimo_relatorio"]["resultado"] == "enviado_com_pendencias"
    assert resumo["contagens"] | {} == {
        "notas_encontradas": 2,
        "notas_preparadas": 1,
        "notas_enviadas": 1,
        "notas_nao_enviadas": 1,
        "notas_pendentes": 1,
        "notas_canceladas": 0,
        "eventos_encontrados": 0,
        "eventos_preparados": 0,
        "eventos_enviados": 0,
        "eventos_por_tipo": [],
    }
    assert resumo["valores"]["total_notas"] is None
    assert resumo["valores"]["total_enviadas"] == "100.50"
    assert resumo["valores"]["total_nao_enviadas"] is None
    assert resumo["valores"]["cobertura"]["nao_enviadas"] == {
        "com_valor": 0,
        "sem_valor": 1,
    }
    snapshot = detalhe(db, tenant, resumo)
    assert snapshot["pendencias"][0]["documento_id"] == str(pendente.id)
    assert "novo lote" in snapshot["pendencias"][0]["acao_recomendada"]
    kwargs = enviar.call_args.kwargs
    assert "1 nota(s) pendente(s)" in kwargs["text_body"]
    with ZipFile(BytesIO(kwargs["attachments"][0]["content"])) as zipado:
        assert (
            zipado.read(f"{autorizada.nfe_chave}-nfe.xml").decode()
            == autorizada.nfe_xml
        )
        preparacao = json.loads(zipado.read("relatorio.json"))
        assert (
            preparacao["etapa"] == "preparacao" and preparacao["notas_pendentes"] == 1
        )
        assert "notas_enviadas" not in preparacao
    assert relatorios.atual() is None


def test_apenas_pendentes_nao_envia_nem_afirma_sem_notas(banco):
    db, tenant, enviar = banco
    nota(db, tenant, status="processando")
    envio, resumo = executar(db, tenant)
    assert envio["status"] == "pendencias" and resumo["resultado"] == "pendencias"
    assert resumo["contagens"]["notas_enviadas"] == 0
    assert resumo["contagens"]["notas_pendentes"] == 1
    enviar.assert_not_called()
    assert service.reenviar_envio(db, tenant, envio["id"])["status"] == "pendente"


@pytest.mark.parametrize("com_pendente", [False, True])
def test_smtp_falha_preserva_preparadas_e_tentativa_anterior_apos_retry(
    banco, monkeypatch, com_pendente
):
    db, tenant, enviar = banco
    nota(db, tenant)
    if com_pendente:
        nota(db, tenant, 2, status="processando")
    enviar.return_value = False
    envio, primeira = executar(db, tenant)
    assert primeira["resultado"] == "falha_smtp"
    assert "e-mail" in primeira["acao_recomendada"]
    assert primeira["contagens"]["notas_preparadas"] == 1
    assert primeira["contagens"]["notas_enviadas"] == 0
    copia = detalhe(db, tenant, primeira)
    if com_pendente:
        assert copia["pendencias"][0]["acao_recomendada"] == relatorios.ACOES_PENDENTES
    enviar.return_value = True
    monkeypatch.setattr(service, "_agora", lambda: NOW + timedelta(hours=1))
    assert service.processar_fila_tenant(db, tenant, limite=1) == 1
    lista = relatorios.listar(db, tenant, envio["id"])["relatorios"]
    assert [r["numero_tentativa"] for r in lista] == [2, 1]
    assert lista[0]["contagens"]["notas_enviadas"] == 1
    assert detalhe(db, tenant, primeira) == copia
    registro = db.get(XmlContabilidadeTentativa, primeira["id"])
    registro.resultado = "reescrever"
    with pytest.raises(ValueError, match="imutáveis"):
        db.commit()
    db.rollback()


def test_xml_autorizado_invalido_ainda_bloqueia_todo_lote_com_motivo(banco):
    db, tenant, enviar = banco
    nota(db, tenant)
    invalida = nota(db, tenant, 2)
    invalida.nfe_xml = invalida.nfe_xml.replace(
        "<cStat>100</cStat>", "<cStat>999</cStat>"
    )
    db.commit()
    _, resumo = executar(db, tenant)
    assert resumo["resultado"] == "bloqueado"
    assert resumo["contagens"]["notas_preparadas"] == 1
    assert resumo["contagens"]["notas_enviadas"] == 0
    assert "protocolo" in resumo["motivo"]
    assert "protocolo" in detalhe(db, tenant, resumo)["documentos"][1]["motivo"]
    enviar.assert_not_called()


def test_cancelada_com_cce_multipla_nao_duplica_notas_valores_ou_eventos(
    banco, monkeypatch
):
    db, tenant, _ = banco
    venda = nota(db, tenant, status="cancelada", valor="75.25")
    rows = [
        evento(venda.nfe_chave),
        evento(venda.nfe_chave, seq=2),
        evento(venda.nfe_chave, "110111"),
    ]
    monkeypatch.setattr(
        documentos, "_obter_eventos", lambda *_: {"_eventos_intnfe": rows + rows}
    )
    _, resumo = executar(db, tenant)
    assert resumo["contagens"]["notas_enviadas"] == 1
    assert resumo["contagens"]["notas_canceladas"] == 1
    assert resumo["contagens"]["eventos_enviados"] == 3
    assert (
        resumo["valores"]["total_enviadas"]
        == resumo["valores"]["total_canceladas_enviadas"]
        == "75.25"
    )
    assert resumo["valores"]["total_liquido"] == "0.00"
    assert {
        g["tipo"]: g["enviados"] for g in resumo["contagens"]["eventos_por_tipo"]
    } == {"110110": 2, "110111": 1}


def test_evento_de_nota_antiga_nao_infla_volume_financeiro(banco, monkeypatch):
    db, tenant, _ = banco
    venda = nota(db, tenant, antiga=True)
    monkeypatch.setattr(
        documentos,
        "_obter_eventos",
        lambda *_: {"_eventos_intnfe": [evento(venda.nfe_chave)]},
    )
    _, resumo = executar(db, tenant)
    assert (
        resumo["contagens"]["notas_encontradas"]
        == resumo["contagens"]["notas_enviadas"]
        == 0
    )
    assert resumo["contagens"]["eventos_enviados"] == 1
    assert resumo["valores"]["total_notas"] == "0.00"
    assert detalhe(db, tenant, resumo)["documentos"][0]["estado"] == "somente_eventos"


def test_legado_nao_reconstroi_relatorio_e_gets_nao_usam_http(banco, monkeypatch):
    db, tenant, _ = banco
    envio = service.criar_envio(db, tenant, date(2026, 10, 1), date(2026, 10, 19))
    rede = Mock(side_effect=AssertionError("GET não consulta documentos externos"))
    monkeypatch.setattr(documentos, "_obter_xml", rede)
    assert relatorios.listar(db, tenant, envio["id"])["disponivel"] is False
    assert service.listar_envios(db, tenant)[0]["ultimo_relatorio"] is None
    rede.assert_not_called()


def test_snapshots_isolados_por_empresa_sem_bling_e_sem_segredos(banco, monkeypatch):
    db, tenant, _ = banco
    nota(db, tenant, provider="bling")
    nota(db, tenant, 2)
    monkeypatch.setattr(
        documentos,
        "_obter_xml",
        Mock(side_effect=RuntimeError("<xml>token-secret-privado</xml>")),
    )
    envio, resumo = executar(db, tenant)
    snapshot = detalhe(db, tenant, resumo)
    assert len(snapshot["documentos"]) == 1
    assert snapshot["documentos"][0]["provider"] == "intnfe"
    serialized = json.dumps(snapshot)
    assert "token-secret" not in serialized and "<xml>" not in serialized
    with tenant_context(uuid4()), pytest.raises(service.XmlContabilidadeError) as erro:
        relatorios.obter(db, uuid4(), envio["id"], resumo["id"])
    assert erro.value.status_code == 404


def test_contextos_nao_misturam_tentativas_ou_empresas(banco):
    db, tenant, _ = banco
    envio = SimpleNamespace(
        id=1,
        origem="manual",
        email_destino="contador@example.com",
        data_inicio=date(2026, 10, 1),
        data_fim=date(2026, 10, 19),
        idempotency_key=None,
    )
    primeiro = relatorios.RelatorioTentativa(db, tenant, envio, inventariar=False)
    segundo = relatorios.RelatorioTentativa(db, uuid4(), envio, inventariar=False)
    token = relatorios.ativar(primeiro)
    outro = relatorios.ativar(segundo)
    assert relatorios.atual() is segundo
    relatorios.desativar(outro)
    assert relatorios.atual() is primeiro
    relatorios.desativar(token)
    assert relatorios.atual() is None


def test_interrompida_nao_inventa_contagens_historicas(banco):
    db, tenant, _ = banco
    envio = SimpleNamespace(
        id=1,
        origem="manual",
        email_destino="contador@example.com",
        data_inicio=date(2026, 10, 1),
        data_fim=date(2026, 10, 19),
        idempotency_key=None,
    )
    snapshot = relatorios.RelatorioTentativa(
        db, tenant, envio, inventariar=False
    ).snapshot("interrompido")
    assert snapshot["contagens_verificadas"] is False
    assert snapshot["contagens"]["notas_enviadas"] is None
    assert snapshot["documentos"] == []
    assert snapshot["confirmacao_envio"] == "indeterminada"


@pytest.mark.parametrize(
    "falha", ["persistir_uma_vez", "persistir_sempre", "commit_uma_vez"]
)
@pytest.mark.parametrize("com_pendente", [False, True])
def test_smtp_aceito_com_falha_historico_nunca_repete_automaticamente(
    banco, monkeypatch, falha, com_pendente
):
    db, tenant, enviar = banco
    nota(db, tenant)
    if com_pendente:
        nota(db, tenant, 2, status="processando")
    envio = service.criar_envio(db, tenant, date(2026, 10, 1), date(2026, 10, 19))
    if falha.startswith("persistir"):
        original = relatorios.persistir
        chamadas = 0

        def persistir(*args, **kwargs):
            nonlocal chamadas
            chamadas += 1
            if chamadas == 1 or falha == "persistir_sempre":
                raise RuntimeError("falha do banco depois do SMTP")
            return original(*args, **kwargs)

        monkeypatch.setattr(relatorios, "persistir", persistir)
    else:
        original = db.commit
        falhou = False

        def commit():
            nonlocal falhou
            if enviar.called and not falhou:
                falhou = True
                raise RuntimeError("commit sem confirmação depois do SMTP")
            return original()

        monkeypatch.setattr(db, "commit", commit)
    assert service.processar_fila_tenant(db, tenant, limite=1) == 1
    estado = service.listar_envios(db, tenant)[0]
    assert estado["id"] == envio["id"]
    assert estado["status"] == "falhou" and estado["tentativas"] == 1
    assert "contador" in estado["ultimo_erro"]
    monkeypatch.setattr(service, "_agora", lambda: NOW + timedelta(days=1))
    assert service.processar_fila_tenant(db, tenant, limite=5) == 0
    assert enviar.call_count == 1
    if falha != "persistir_sempre":
        assert (
            relatorios.listar(db, tenant, envio["id"])["relatorios"][0]["resultado"]
            == "interrompido"
        )


def test_duas_vendas_mesma_chave_contam_uma_nota_e_um_valor(banco):
    db, tenant, _ = banco
    primeira = nota(db, tenant)
    segunda = nota(db, tenant, 2)
    segunda.nfe_chave, segunda.nfe_xml = primeira.nfe_chave, primeira.nfe_xml
    db.commit()
    _, resumo = executar(db, tenant)
    assert resumo["contagens"]["notas_encontradas"] == 1
    assert resumo["contagens"]["notas_preparadas"] == 1
    assert resumo["contagens"]["notas_enviadas"] == 1
    assert resumo["valores"]["total_enviadas"] == "100.50"


@pytest.mark.parametrize(
    "data_xml", ["2026-09-30T23:00:00-03:00", "2026-10-01T01:00:00+00:00"]
)
def test_data_oficial_fora_do_periodo_nao_infla_notas_encontradas(banco, data_xml):
    db, tenant, enviar = banco
    venda = nota(db, tenant)
    venda.nfe_xml = xml_nota(venda.nfe_chave, data=data_xml)
    db.commit()
    _, resumo = executar(db, tenant)
    assert resumo["resultado"] == "sem_notas"
    assert resumo["contagens"]["notas_encontradas"] == 0
    assert detalhe(db, tenant, resumo)["documentos"][0]["estado"] == "excluida"
    enviar.assert_not_called()


def test_cce_incompleta_informa_evento_encontrado_mas_nao_preparado(banco, monkeypatch):
    db, tenant, enviar = banco
    venda = nota(db, tenant)
    monkeypatch.setattr(
        documentos,
        "_obter_eventos",
        lambda *_: {"_eventos_intnfe": [evento(venda.nfe_chave, seq=3)]},
    )
    _, resumo = executar(db, tenant)
    assert resumo["resultado"] == "bloqueado"
    assert resumo["contagens"]["eventos_encontrados"] == 1
    assert resumo["contagens"]["eventos_preparados"] == 0
    assert resumo["contagens"]["eventos_enviados"] == 0
    assert "sequência" in resumo["motivo"]
    enviar.assert_not_called()


@pytest.mark.parametrize("valor,esperado", [("0.00", "0.00"), (None, None)])
def test_zero_oficial_e_valor_indisponivel_sao_diferentes(banco, valor, esperado):
    db, tenant, _ = banco
    nota(db, tenant, valor=valor)
    _, resumo = executar(db, tenant)
    assert resumo["valores"]["total_enviadas"] == esperado
    assert resumo["valores"]["cobertura"]["enviadas"]["sem_valor"] == int(valor is None)


def test_reconciliacao_para_rejeitada_nao_finge_que_ainda_esta_pendente(
    banco, monkeypatch
):
    db, tenant, enviar = banco
    venda = nota(db, tenant, status="processando")

    def rejeitar(*_):
        venda.nfe_status = "rejeitada"
        db.commit()

    monkeypatch.setattr(reconciliacao, "reconciliar_pendentes", rejeitar)
    _, resumo = executar(db, tenant)
    assert resumo["contagens"]["notas_pendentes"] == 0
    doc = detalhe(db, tenant, resumo)["documentos"][0]
    assert doc["status_fiscal"] == "rejeitada"
    assert doc["estado"] == "nao_preparada"
    assert "rejeitada" in doc["motivo"]
    enviar.assert_not_called()
