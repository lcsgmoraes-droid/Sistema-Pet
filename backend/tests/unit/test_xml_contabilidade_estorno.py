"""XMLs de estorno próprios, isolados por empresa e sem substituir a NFC-e."""

from copy import deepcopy
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import base as _registry  # noqa: F401
from app.intnfe.estorno_models import IntNFeEstorno
from app.models import Tenant
from app.services import xml_contabilidade_documentos as documentos
from app.services import xml_contabilidade_individual as individual
from app.services import xml_contabilidade_relatorios as relatorios
from app.services import xml_contabilidade_service as service
from app.tenancy.context import tenant_context
from app.vendas_models import Venda
from app.xml_contabilidade_models import (
    XmlContabilidadeConfig,
    XmlContabilidadeEnvio,
    XmlContabilidadeEvento,
    XmlContabilidadeMonitor,
)

CNPJ = "33590794000140"
DIA = date(2026, 10, 20)
NOW = datetime(2026, 10, 20, 15, 1, tzinfo=timezone.utc)


def chave(modelo, numero):
    base = f"412610{CNPJ}{modelo}003{numero:09d}1{numero:08d}"
    soma = sum(
        int(digito) * (2 + indice % 8) for indice, digito in enumerate(reversed(base))
    )
    resto = soma % 11
    return base + str(0 if resto < 2 else 11 - resto)


ORIGINAL = chave(65, 18574)
ESTORNO = chave(55, 100)
FRASE_LEGAL = (
    "Nota Fiscal emitida de acordo com inciso VII do caput do art. 298 do RICMS"
)
INFORMACOES_FISCO = (
    f"{FRASE_LEGAL}. Estorno integral da NFC-e 18574, serie 3, chave {ORIGINAL}. "
    "Operação não realizada; mercadoria não saiu."
)


def xml_estorno():
    return f"""<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe"><NFe><infNFe Id="NFe{ESTORNO}">
<ide><mod>55</mod><nNF>100</nNF><serie>3</serie><dhEmi>2026-10-20T12:01:00-03:00</dhEmi><tpAmb>1</tpAmb><tpNF>0</tpNF><finNFe>3</finNFe><NFref><refNFe>{ORIGINAL}</refNFe></NFref></ide>
<emit><CNPJ>{CNPJ}</CNPJ><xNome>Empresa fictícia</xNome><CRT>1</CRT></emit><dest><CNPJ>{CNPJ}</CNPJ></dest>
<det nItem="1"><prod><cProd>PRD123</cProd><xProd>Produto teste</xProd><NCM>38089119</NCM><CFOP>1102</CFOP><uCom>UN</uCom><qCom>1</qCom><vUnCom>39.90</vUnCom><vProd>39.90</vProd><vDesc>2.00</vDesc></prod>
<imposto><ICMS><ICMSSN102><orig>0</orig><CSOSN>102</CSOSN></ICMSSN102></ICMS><PIS><PISOutr><CST>49</CST><vBC>0</vBC><pPIS>0</pPIS><vPIS>0</vPIS></PISOutr></PIS><COFINS><COFINSOutr><CST>49</CST><vBC>0</vBC><pCOFINS>0</pCOFINS><vCOFINS>0</vCOFINS></COFINSOutr></COFINS></imposto></det>
<total><ICMSTot><vProd>39.90</vProd><vDesc>2.00</vDesc><vNF>37.90</vNF></ICMSTot></total><pag><detPag><tPag>90</tPag><vPag>0</vPag></detPag></pag>
<infAdic><infAdFisco>{INFORMACOES_FISCO}</infAdFisco></infAdic>
</infNFe></NFe><protNFe><infProt><chNFe>{ESTORNO}</chNFe><tpAmb>1</tpAmb><cStat>100</cStat><nProt>141260000000100</nProt></infProt></protNFe></nfeProc>"""


def xml_original():
    return f"""<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe"><NFe><infNFe Id="NFe{ORIGINAL}"><ide><mod>65</mod><nNF>18574</nNF><dhEmi>2026-10-20T12:00:00-03:00</dhEmi><tpAmb>1</tpAmb><tpNF>1</tpNF></ide><emit><CNPJ>{CNPJ}</CNPJ><xNome>Empresa fictícia</xNome></emit><total><ICMSTot><vNF>37.90</vNF></ICMSTot></total></infNFe></NFe><protNFe><infProt><chNFe>{ORIGINAL}</chNFe><cStat>100</cStat></infProt></protNFe></nfeProc>"""


def snapshot():
    return {
        "ambiente_codigo": 1,
        "serie": 3,
        "original_chave": ORIGINAL,
        "emitente_cnpj": CNPJ,
        "total": "37.90",
        "destinatario": {"cnpj": CNPJ},
        "informacoes_fisco": INFORMACOES_FISCO,
        "itens": [
            {
                "codigo_produto": "PRD123",
                "descricao": "Produto teste",
                "ncm": "38089119",
                "cest": "",
                "unidade": "UN",
                "cfop": "1102",
                "quantidade": "1",
                "valor_unitario": "39.90",
                "valor_produtos": "39.90",
                "desconto": "2.00",
                "origem": "0",
            }
        ],
    }


@pytest.fixture
def contexto(monkeypatch):
    from app.intnfe import client, emission

    tenant = uuid4()
    engine = create_engine("sqlite://")
    for model in (
        Tenant,
        Venda,
        IntNFeEstorno,
        XmlContabilidadeConfig,
        XmlContabilidadeEnvio,
        XmlContabilidadeEvento,
        XmlContabilidadeMonitor,
    ):
        model.__table__.create(engine)
    consultas = []
    api = SimpleNamespace(
        document_events=lambda _token, tipo, correlation: (
            consultas.append((tipo, correlation)) or []
        ),
        close=lambda: None,
    )
    monkeypatch.setattr(client, "IntNFeClient", lambda: api)
    monkeypatch.setattr(emission, "_connection", lambda *_a, **_kw: object())
    monkeypatch.setattr(emission, "_access_token", lambda *_a: "token-ficticio")
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
        venda = Venda(
            tenant_id=tenant,
            numero_venda="V1",
            vendedor_id=1,
            user_id=1,
            subtotal=39.9,
            total=37.9,
            status="cancelada",
            nfe_provider="intnfe",
            nfe_correlation_id="correlacao-original",
            nfe_ambiente=1,
            nfe_modelo="65",
            nfe_tipo="nfce",
            nfe_status="autorizada",
            nfe_chave=ORIGINAL,
            nfe_numero=18574,
            nfe_data_emissao=datetime(2026, 10, 20, 12),
            nfe_xml=xml_original(),
        )
        db.add(venda)
        db.flush()
        estorno = IntNFeEstorno(
            tenant_id=tenant,
            venda_id=venda.id,
            ambiente_codigo=1,
            original_chave=ORIGINAL,
            original_xml_hash="a" * 64,
            payload={},
            payload_hash="b" * 64,
            snapshot=snapshot(),
            idempotency_key="teste-estorno",
            status="autorizado",
            motivo_operacao="Operação não realizada",
            declarado_nao_realizada=True,
            tentativa_em=NOW,
            correlation_id="correlacao-estorno",
            numero=100,
            serie=3,
            chave=ESTORNO,
            protocolo="141260000000100",
            xml=xml_estorno(),
            xml_validado=True,
            autorizado_em=NOW,
        )
        db.add(estorno)
        db.commit()
        yield SimpleNamespace(
            db=db,
            tenant=tenant,
            venda=venda,
            estorno=estorno,
            consultas=consultas,
            api=api,
        )
    engine.dispose()


def test_estorno_e_original_no_mesmo_lote_sem_colisao_de_id(contexto):
    c = contexto
    assert c.venda.id == c.estorno.id
    docs = documentos._listar_documentos(c.db, c.tenant, DIA, DIA)
    arquivos, notas = documentos._coletar_arquivos(c.db, c.tenant, docs, DIA, DIA)
    assert {n["documento_id"] for n in notas} == {
        str(c.venda.id),
        f"estorno:{c.estorno.id}",
    }
    assert dict(arquivos) == {
        f"{ORIGINAL}-nfe.xml": xml_original().encode(),
        f"{ESTORNO}-nfe.xml": xml_estorno().encode(),
    }
    assert set(c.consultas) == {
        ("nfce", "correlacao-original"),
        ("nfe", "correlacao-estorno"),
    }
    estorno = next(n for n in notas if n["documento_id"].startswith("estorno:"))
    assert estorno["venda_id"] == c.venda.id and estorno["chave_original"] == ORIGINAL
    assert c.venda.nfe_xml == xml_original() and c.venda.nfe_status == "autorizada"
    assert c.venda.status == "cancelada"


@pytest.mark.parametrize(
    "campos",
    [
        {"ambiente_codigo": 2},
        {"status": "processando"},
        {"status": "recusado"},
        {"xml_validado": False},
        {"autorizado_em": None},
    ],
)
def test_estorno_nao_confirmado_nao_entra_no_lote_ou_monitor(contexto, campos):
    c = contexto
    for campo, valor in campos.items():
        setattr(c.estorno, campo, valor)
    c.db.commit()
    assert (
        documentos._documento(c.db, c.tenant, "intnfe", f"estorno:{c.estorno.id}")
        is None
    )
    assert len(documentos._listar_documentos(c.db, c.tenant, DIA, DIA)) == 1
    assert individual._referencias(c.db, c.tenant) == [("intnfe", str(c.venda.id))]


@pytest.mark.parametrize(
    "referencia", ["estorno:0", "estorno:-1", "estorno:01", "estorno:1:x", "outro:1"]
)
def test_namespace_invalido_nao_vira_venda_nem_estorno(contexto, referencia):
    assert (
        documentos._documento(contexto.db, contexto.tenant, "intnfe", referencia)
        is None
    )


def test_estorno_de_outra_empresa_e_vinculo_cruzado_nao_sao_resolvidos(contexto):
    c, outro = contexto, uuid4()
    with tenant_context(outro):
        assert (
            documentos._documento(c.db, outro, "intnfe", f"estorno:{c.estorno.id}")
            is None
        )
        assert (
            individual.priorizar_documento(
                c.db, outro, "intnfe", f"estorno:{c.estorno.id}", NOW
            )
            is None
        )
    # Nem uma linha com tenant adulterado pode usar a venda de outro tenant.
    c.estorno.tenant_id = outro
    c.db.commit()
    with tenant_context(outro):
        assert (
            documentos._documento(c.db, outro, "intnfe", f"estorno:{c.estorno.id}")
            is None
        )


def test_estorno_nao_pode_trocar_referencia_da_venda_original(contexto):
    c = contexto
    c.estorno.original_chave = chave(65, 18575)
    c.db.commit()
    assert (
        documentos._documento(c.db, c.tenant, "intnfe", f"estorno:{c.estorno.id}")
        is None
    )
    assert len(documentos._listar_documentos(c.db, c.tenant, DIA, DIA)) == 1


@pytest.mark.parametrize(
    "antes,depois",
    [
        ("<tpNF>0</tpNF>", "<tpNF>1</tpNF>"),
        ("<finNFe>3</finNFe>", "<finNFe>1</finNFe>"),
        ("<tpAmb>1</tpAmb>", "<tpAmb>2</tpAmb>"),
        (f"<refNFe>{ORIGINAL}</refNFe>", f"<refNFe>{ESTORNO}</refNFe>"),
        ("<vNF>37.90</vNF>", "<vNF>39.90</vNF>"),
        ("<cStat>100</cStat>", "<cStat>301</cStat>"),
    ],
)
def test_xml_divergente_bloqueia_lote_inteiro(contexto, antes, depois):
    c = contexto
    c.estorno.xml = c.estorno.xml.replace(antes, depois)
    c.db.commit()
    with pytest.raises(documentos.XmlContabilidadeError, match="XML do estorno"):
        documentos._coletar_arquivos(
            c.db,
            c.tenant,
            documentos._listar_documentos(c.db, c.tenant, DIA, DIA),
            DIA,
            DIA,
        )


def test_entrada_nao_vinculada_continua_excluida(contexto):
    c = contexto
    assert documentos.validar_xml_saida(xml_estorno(), ESTORNO, 55) is None
    entrada = documentos.Documento(
        "intnfe", str(c.venda.id), ESTORNO, 55, "autorizada", NOW, venda=c.venda
    )
    obter_xml = Mock(return_value=(xml_estorno().encode(), {}))
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(documentos, "_obter_xml", obter_xml)
        assert documentos._coletar_arquivos(c.db, c.tenant, [entrada], DIA, DIA) == (
            [],
            [],
        )
    assert c.consultas == []


def test_snapshot_de_outro_emitente_nao_libera_entrada(contexto):
    c = contexto
    alterado = deepcopy(c.estorno.snapshot)
    alterado["emitente_cnpj"] = "12345678000195"
    c.estorno.snapshot = alterado
    c.db.commit()
    doc = documentos._documento(c.db, c.tenant, "intnfe", f"estorno:{c.estorno.id}")
    with pytest.raises(documentos.XmlContabilidadeError, match="origem fiscal própria"):
        documentos.validar_xml_documento(c.estorno.xml, doc, c.tenant, CNPJ)


@pytest.mark.parametrize(
    "ausencia", ["snapshot", "campo_snapshot", "frase_legal", "motivo"]
)
def test_estorno_sem_snapshot_ou_justificativa_fiscal_equivalente_bloqueia_lote(
    contexto, ausencia
):
    c = contexto
    if ausencia == "snapshot":
        c.estorno.snapshot = None
    elif ausencia == "campo_snapshot":
        incompleto = deepcopy(c.estorno.snapshot)
        incompleto.pop("informacoes_fisco")
        c.estorno.snapshot = incompleto
    elif ausencia == "frase_legal":
        sem_frase = INFORMACOES_FISCO.replace(FRASE_LEGAL, "")
        c.estorno.xml = c.estorno.xml.replace(INFORMACOES_FISCO, sem_frase)
        alterado = deepcopy(c.estorno.snapshot)
        alterado["informacoes_fisco"] = sem_frase
        c.estorno.snapshot = alterado
    else:
        c.estorno.xml = c.estorno.xml.replace(
            "Operação não realizada; mercadoria não saiu.", "Motivo diferente do envio."
        )
    c.db.commit()
    docs = documentos._listar_documentos(c.db, c.tenant, DIA, DIA)
    with pytest.raises(documentos.XmlContabilidadeError):
        documentos._coletar_arquivos(c.db, c.tenant, docs, DIA, DIA)


def evento_estorno(tipo="110110"):
    identidade = f"ID{tipo}{ESTORNO}01"
    protocolo = "135260000000001"
    xml_evento = f'<procEventoNFe xmlns="http://www.portalfiscal.inf.br/nfe"><evento><infEvento Id="{identidade}"><tpAmb>1</tpAmb><CNPJ>{CNPJ}</CNPJ><chNFe>{ESTORNO}</chNFe><tpEvento>{tipo}</tpEvento><nSeqEvento>1</nSeqEvento></infEvento></evento><retEvento><infEvento><tpAmb>1</tpAmb><chNFe>{ESTORNO}</chNFe><tpEvento>{tipo}</tpEvento><nSeqEvento>1</nSeqEvento><cStat>135</cStat><nProt>{protocolo}</nProt><dhRegEvento>2026-10-20T12:02:00-03:00</dhRegEvento></infEvento></retEvento></procEventoNFe>'
    return identidade, {
        "autorizado": True,
        "tipoEventoCodigo": tipo,
        "protocolo": protocolo,
        "xmlEvento": xml_evento,
    }


def test_evento_do_estorno_e_persistido_com_namespace_e_chave_proprios(contexto):
    c = contexto
    identidade, retorno = evento_estorno()
    c.api.document_events = Mock(return_value=[retorno])
    ref = f"estorno:{c.estorno.id}"
    arquivos, notas = individual.consultar_documento(c.db, c.tenant, "intnfe", ref, NOW)
    c.db.commit()
    c.api.document_events.assert_called_once_with(
        "token-ficticio", "nfe", "correlacao-estorno"
    )
    evento = c.db.query(XmlContabilidadeEvento).one()
    assert evento.documento_id == ref and evento.chave == ESTORNO
    assert dict(arquivos)[f"{identidade}.xml"] == retorno["xmlEvento"].encode()
    assert notas[0]["chave_original"] == ORIGINAL
    assert (
        c.venda.nfe_xml == xml_original()
        and c.venda.nfe_correlation_id == "correlacao-original"
    )


@pytest.mark.parametrize("com_comprovante", [True, False])
def test_estorno_cancelado_preserva_xml_e_exige_evento_oficial(
    contexto, com_comprovante
):
    c = contexto
    c.estorno.status = "cancelado"
    c.db.commit()
    identidade, retorno = evento_estorno("110111")
    c.api.document_events = Mock(
        side_effect=lambda _token, _tipo, correlation: (
            [retorno] if correlation == "correlacao-estorno" and com_comprovante else []
        )
    )
    docs = documentos._listar_documentos(c.db, c.tenant, DIA, DIA)
    assert len(docs) == 2
    assert next(d for d in docs if d.estorno is not None).status == "cancelada"
    if not com_comprovante:
        with pytest.raises(documentos.XmlContabilidadeError, match="cancelamento"):
            documentos._coletar_arquivos(c.db, c.tenant, docs, DIA, DIA)
        return
    arquivos, notas = documentos._coletar_arquivos(c.db, c.tenant, docs, DIA, DIA)
    assert dict(arquivos)[f"{ESTORNO}-nfe.xml"] == xml_estorno().encode()
    assert dict(arquivos)[f"{ORIGINAL}-nfe.xml"] == xml_original().encode()
    assert dict(arquivos)[f"{identidade}.xml"] == retorno["xmlEvento"].encode()
    assert next(n for n in notas if n["chave"] == ESTORNO)["status"] == "cancelada"
    assert c.venda.nfe_status == "autorizada" and c.venda.status == "cancelada"


def test_data_oficial_xml_decide_periodo_do_estorno(contexto):
    c = contexto
    c.estorno.xml = c.estorno.xml.replace(
        "2026-10-20T12:01:00-03:00", "2026-10-21T12:01:00-03:00"
    )
    c.db.commit()
    docs = documentos._listar_documentos(c.db, c.tenant, DIA, DIA)
    arquivos, notas = documentos._coletar_arquivos(c.db, c.tenant, docs, DIA, DIA)
    assert len(arquivos) == len(notas) == 1 and notas[0]["chave"] == ORIGINAL


def test_envio_individual_deduplica_estorno_preservando_original_e_relatorio(contexto):
    c = contexto
    config = XmlContabilidadeConfig(
        tenant_id=c.tenant,
        email_contador="contador@example.com",
        envio_automatico=True,
        envio_automatico_desde=datetime(2026, 10, 20, 14, tzinfo=timezone.utc),
    )
    c.db.add(config)
    c.db.commit()
    ref = f"estorno:{c.estorno.id}"
    envio = service.enfileirar_documento(c.db, c.tenant, "intnfe", ref)
    assert service.enfileirar_documento(c.db, c.tenant, "intnfe", ref) is envio
    original = service.enfileirar_documento(c.db, c.tenant, "intnfe", str(c.venda.id))
    c.db.commit()
    assert (
        envio.idempotency_key == f"nota:{ESTORNO}"
        and original.idempotency_key == f"nota:{ORIGINAL}"
    )
    assert c.db.query(XmlContabilidadeEnvio).count() == 2
    assert c.db.query(XmlContabilidadeMonitor).count() == 2
    assert set(individual._referencias(c.db, c.tenant)) == {
        ("intnfe", ref),
        ("intnfe", str(c.venda.id)),
    }
    relatorio = relatorios.RelatorioTentativa(c.db, c.tenant, envio)
    token = relatorios.ativar(relatorio)
    try:
        anexos, nome, quantidade = individual.preparar_anexos_individual(
            c.db, c.tenant, envio
        )
    finally:
        relatorios.desativar(token)
    assert nome == f"{ESTORNO}-nfe.xml" and quantidade == 1
    assert anexos[0]["content"] == xml_estorno().encode()
    registro = relatorio.documentos[ref]
    assert (
        registro["venda_id"] == c.venda.id and registro["tipo_documento"] == "estorno"
    )
    assert f"venda_id={c.venda.id}" in registro["link_corepet"]
    assert "%3A" not in registro["link_corepet"]


def test_relatorio_lote_preserva_identidades_original_e_estorno(contexto):
    c = contexto
    envio = SimpleNamespace(
        id=1,
        origem="manual",
        email_destino="contador@example.com",
        data_inicio=DIA,
        data_fim=DIA,
        idempotency_key=None,
    )
    relatorio = relatorios.RelatorioTentativa(c.db, c.tenant, envio)
    token = relatorios.ativar(relatorio)
    try:
        documentos._coletar_arquivos(
            c.db,
            c.tenant,
            documentos._listar_documentos(c.db, c.tenant, DIA, DIA),
            DIA,
            DIA,
        )
    finally:
        relatorios.desativar(token)
    assert set(relatorio.documentos) == {str(c.venda.id), f"estorno:{c.estorno.id}"}
    assert all(row["_preparada"] for row in relatorio.documentos.values())
    assert relatorio.documentos[str(c.venda.id)]["chave"] == ORIGINAL
    assert relatorio.documentos[f"estorno:{c.estorno.id}"]["chave"] == ESTORNO
