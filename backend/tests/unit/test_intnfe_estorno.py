"""Documento separado, uma transmissão e confirmação fiscal por XML equivalente."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from app.intnfe import estorno_service as service
from app.intnfe.client import IntNFeError
from app.intnfe.estorno_builder import (
    FRASE_LEGAL_ESTORNO,
    EstornoError,
    build,
    destinatario_proprio,
)
from app.intnfe.estorno_models import IntNFeEstorno
from app.intnfe.estorno_routes import EstornoRequest, _venda
from app.intnfe.estorno_xml import validate_xml
from app.produtos_models import EstoqueMovimentacao
from app.vendas_models import VendaPagamento
from tests.unit import test_venda_cancelamento_comercial_fiscal as commercial

cenario = commercial.cenario
cancelamento = commercial.cancelamento
venda_com_nota = commercial.venda_com_nota
CHAVE = "41261052028931000100650020000185741818261720"
CNPJ = "52028931000100"
MOTIVO = "Venda não realizada; mercadoria não saiu."


def xml_original():
    return f"""<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe"><NFe><infNFe Id="NFe{CHAVE}">
<ide><mod>65</mod><tpAmb>1</tpAmb><nNF>18574</nNF><serie>2</serie><tpNF>1</tpNF><finNFe>1</finNFe><dhEmi>2026-10-20T13:21:24-03:00</dhEmi></ide>
<emit><CNPJ>{CNPJ}</CNPJ><xNome>LOJA TESTE</xNome><IE>1234567890</IE><CRT>1</CRT>
<enderEmit><xLgr>Rua Teste</xLgr><nro>1</nro><xBairro>Centro</xBairro><xMun>Curitiba</xMun><cMun>4106902</cMun><UF>PR</UF><CEP>80000000</CEP></enderEmit></emit>
<det nItem="1"><prod><cProd>PROVA</cProd><xProd>PRODUTO TESTE</xProd><NCM>38089119</NCM><CFOP>5102</CFOP><uCom>UN</uCom><qCom>1.0000</qCom><vUnCom>39.9000000000</vUnCom><vProd>39.90</vProd><vDesc>2.00</vDesc></prod>
<imposto><ICMS><ICMSSN102><orig>0</orig><CSOSN>102</CSOSN></ICMSSN102></ICMS><PIS><PISOutr><CST>49</CST><vBC>0.00</vBC><pPIS>0.00</pPIS><vPIS>0.00</vPIS></PISOutr></PIS><COFINS><COFINSOutr><CST>49</CST><vBC>0.00</vBC><pCOFINS>0.00</pCOFINS><vCOFINS>0.00</vCOFINS></COFINSOutr></COFINS></imposto></det>
<total><ICMSTot><vProd>39.90</vProd><vDesc>2.00</vDesc><vNF>37.90</vNF></ICMSTot></total><pag><detPag><tPag>04</tPag><vPag>37.90</vPag></detPag></pag></infNFe></NFe><protNFe><infProt><tpAmb>1</tpAmb><dhRecbto>2026-10-20T16:22:00Z</dhRecbto><cStat>100</cStat><chNFe>{CHAVE}</chNFe><nProt>141261734844045</nProt></infProt></protNFe></nfeProc>"""


def xml_estorno(environment=1):
    original = xml_original()
    chave = "41261052028931000100550030000000011000000010"
    dest = f"<dest><CNPJ>{CNPJ}</CNPJ><xNome>LOJA TESTE</xNome><indIEDest>1</indIEDest><IE>1234567890</IE></dest>"
    return (
        original.replace(CHAVE, chave)
        .replace("<mod>65</mod>", "<mod>55</mod>")
        .replace("<tpAmb>1</tpAmb>", f"<tpAmb>{environment}</tpAmb>")
        .replace("<nNF>18574</nNF>", "<nNF>1</nNF>")
        .replace("<serie>2</serie>", "<serie>3</serie>")
        .replace("<tpNF>1</tpNF>", "<tpNF>0</tpNF>")
        .replace(
            "<finNFe>1</finNFe>",
            f"<finNFe>3</finNFe><NFref><refNFe>{CHAVE}</refNFe></NFref>",
        )
        .replace("</emit>", "</emit>" + dest)
        .replace("<CFOP>5102</CFOP>", "<CFOP>1102</CFOP>")
        .replace(
            "<tPag>04</tPag><vPag>37.90</vPag>", "<tPag>90</tPag><vPag>0.00</vPag>"
        )
        .replace(
            "</pag>",
            f"</pag><infAdic><infAdFisco>{FRASE_LEGAL_ESTORNO}. Estorno integral da NFC-e 18574, serie 2, chave {CHAVE}. {MOTIVO}</infAdFisco></infAdic>",
        )
        .encode()
    )


@pytest.fixture
def context(venda_com_nota, monkeypatch):
    c = venda_com_nota
    IntNFeEstorno.__table__.create(c.db.bind)
    c.venda.status = "cancelada"
    c.venda.total = 37.90
    c.venda.nfe_chave = CHAVE
    c.venda.nfe_xml = xml_original()
    c.venda.nfe_protocolo = "141261734844045"
    c.venda.nfe_serie = 2
    c.db.commit()
    c.connection = SimpleNamespace(
        cnpj=CNPJ,
        nfe_series="3",
        emission_environment=1,
        emission_enabled=True,
        nome_fantasia="FANTASIA DO VINCULO",
    )
    monkeypatch.setattr(service, "_connection", lambda *a, **kw: c.connection)
    monkeypatch.setattr(service, "_access_token", lambda *a, **kw: "token-qa")
    monkeypatch.setattr(service, "log_action", MagicMock())
    monkeypatch.setattr(service, "tentar_enfileirar_documento", MagicMock())
    c.api = MagicMock()
    c.api.issue_document.return_value = {"correlationId": "estorno-qa"}
    c.api.document_status.return_value = {"status": 3}
    c.api.document_xml.return_value = xml_estorno()
    return c


def create(c, **overrides):
    return service.create(
        c.db,
        c.venda,
        c.api,
        motivo=MOTIVO,
        declaracao_operacao_nao_realizada=True,
        user_id=1,
        destinatario_proprio_emitente=True,
        **overrides,
    )


def original_fields(venda):
    return {
        key: getattr(venda, key)
        for key in (
            "status",
            "nfe_chave",
            "nfe_xml",
            "nfe_status",
            "nfe_numero",
            "nfe_serie",
            "nfe_protocolo",
            "nfe_correlation_id",
        )
    }


def test_previa_anonima_exige_escolha_humana_e_preserva_pagamento_zero(context):
    c = context
    blocked = service.preview(c.db, c.venda)
    assert (
        not blocked["elegivel"]
        and blocked["destinatario_anonimo"]
        and blocked["requer_destinatario"]
    )
    result = service.preview(c.db, c.venda, destinatario_proprio_emitente=True)
    assert result["elegivel"] and not result["requer_destinatario"]
    assert result["previa"]["totais"] == {
        "produtos": 39.90,
        "desconto": 2,
        "total": 37.90,
    }
    assert result["previa"]["destinatario"]["cnpj"] == CNPJ
    payload, _, _, _ = build(
        c.venda,
        c.connection,
        ambiente_codigo=1,
        destinatario=destinatario_proprio(c.venda),
    )
    assert payload["tipoOperacao"] == "0" and payload["finalidade"] == "3"
    assert payload["emitente"]["nomeFantasia"] == "FANTASIA DO VINCULO"
    assert payload["pagamentos"] == [{"formaPagamento": "90", "valor": 0}]
    assert payload["documentosReferenciados"] == [CHAVE]
    assert not any(
        key in repr(payload).lower() for key in ("email", "webhook", "secret")
    )
    c.api.issue_document.assert_not_called()


def test_tentativa_commita_payload_antes_unico_post_e_repeticao_nao_reenvia(context):
    c = context
    original = original_fields(c.venda)
    counts = (
        c.db.query(EstoqueMovimentacao).count(),
        c.db.query(VendaPagamento).count(),
    )

    def post(*args):
        with c.db.bind.connect() as conn:
            row = (
                conn.execute(
                    text(
                        "SELECT status,payload_hash,idempotency_key FROM intnfe_estornos"
                    )
                )
                .mappings()
                .one()
            )
            assert row["status"] == "enviando" and len(row["payload_hash"]) == 64
            assert row["idempotency_key"] == args[3]
        return {"correlationId": "estorno-qa"}

    c.api.issue_document.side_effect = post
    result = create(c)
    assert result["estorno"]["status"] == "processando" and not result["success"]
    assert create(c)["estorno"]["id"] == result["estorno"]["id"]
    assert c.api.issue_document.call_count == 1
    assert original_fields(c.venda) == original
    assert (
        c.db.query(EstoqueMovimentacao).count(),
        c.db.query(VendaPagamento).count(),
    ) == counts


@pytest.mark.parametrize(
    "error,state",
    [
        (IntNFeError("EmissorIndisponivel", uncertain=True), "incerto"),
        (
            IntNFeError(
                "DadosInvalidos",
                status=422,
                validation_errors=["Pagamentos devem somar o total"],
            ),
            "rejeitado",
        ),
    ],
)
def test_timeout_ou_recusa_preserva_tentativa_e_nao_muda_pagamento(
    context, error, state
):
    c = context
    c.api.issue_document.side_effect = error
    result = create(c)
    assert result["estorno"]["status"] == state
    record = c.db.query(IntNFeEstorno).one()
    assert record.payload["pagamentos"] == [{"formaPagamento": "90", "valor": 0}]
    create(c)
    assert c.api.issue_document.call_count == 1


def test_autorizacao_so_depois_xml_validado_sem_mudar_nota_ou_venda(context):
    c = context
    original = original_fields(c.venda)
    create(c)
    result = service.reconcile(c.db, c.venda, c.api, user_id=1)
    assert result["success"] and result["estorno"]["xml_validado"]
    assert result["estorno"]["status"] == "autorizado"
    assert result["estorno"]["numero"] == 1
    assert original_fields(c.venda) == original
    assert c.venda.nfe_estorno_status == "autorizado"
    assert c.api.issue_document.call_count == 1


@pytest.mark.parametrize(
    "before,after",
    [
        (b"<tpNF>0</tpNF>", b"<tpNF>1</tpNF>"),
        (b"<finNFe>3</finNFe>", b"<finNFe>1</finNFe>"),
        (b"<vPag>0.00</vPag>", b"<vPag>37.90</vPag>"),
        (b"<vDesc>2.00</vDesc>", b"<vDesc>0.00</vDesc>"),
        (b"<vPIS>0.00</vPIS>", b"<vPIS>1.00</vPIS>"),
        (b"<CFOP>1102</CFOP>", b"<CFOP>5102</CFOP>"),
        (b"<infProt><tpAmb>1</tpAmb>", b"<infProt><tpAmb>2</tpAmb>"),
        (b"<nProt>141261734844045</nProt>", b"<nProt>123</nProt>"),
        (b"<CRT>1</CRT>", b"<CRT>3</CRT>"),
        (
            b"Nota Fiscal emitida de acordo com inciso VII do caput do art. 298 do RICMS",
            b"Texto sem expressao legal",
        ),
        (
            "Venda não realizada; mercadoria não saiu.".encode(),
            "Motivo divergente do declarado.".encode(),
        ),
        (b"<nNF>1</nNF>", b"<nNF>0</nNF>"),
        (
            b"41261052028931000100550030000000011000000010",
            b"41261052028931000100650030000000011000000010",
        ),
        (b"<vNF>37.90</vNF>", b"<vNF>37.90</vNF><vICMS>1.00</vICMS>"),
    ],
)
def test_http_autorizada_com_xml_divergente_nao_regulariza(context, before, after):
    c = context
    create(c)
    c.api.document_xml.return_value = xml_estorno().replace(before, after)
    result = service.reconcile(c.db, c.venda, c.api)
    assert not result["success"] and result["estorno"]["status"] == "divergente"
    assert c.venda.nfe_estorno_status != "autorizado"


def test_homologacao_nao_regulariza_nota_de_producao(context):
    c = context
    create(c, environment_override=2)
    c.api.document_xml.return_value = xml_estorno(2)
    result = service.reconcile(c.db, c.venda, c.api, environment_override=2)
    assert result["success"] and result["estorno"]["ambiente_codigo"] == 2
    assert c.venda.nfe_estorno_status is None
    assert (
        service.preview(c.db, c.venda, destinatario_proprio_emitente=True)["estorno"]
        is None
    )


def test_cenario_nao_suportado_bloqueia_antes_autenticacao_e_post(context, monkeypatch):
    c = context
    c.venda.nfe_xml = c.venda.nfe_xml.replace("<CFOP>5102</CFOP>", "<CFOP>5405</CFOP>")
    token = MagicMock()
    monkeypatch.setattr(service, "_access_token", token)
    with pytest.raises(EstornoError):
        create(c)
    token.assert_not_called()
    c.api.issue_document.assert_not_called()
    assert c.db.query(IntNFeEstorno).count() == 0


def test_original_cancelado_no_emissor_bloqueia_antes_post(context):
    c = context
    c.api.document_status.return_value = {"status": 5}
    with pytest.raises(EstornoError):
        create(c)
    c.api.issue_document.assert_not_called()


def test_route_exige_admin_e_nao_revela_venda_de_outro_tenant(context):
    from uuid import uuid4

    c = context
    with pytest.raises(HTTPException) as failure:
        _venda(c.db, c.venda.id, (SimpleNamespace(is_admin=False), c.tenant))
    assert failure.value.status_code == 403
    with pytest.raises(HTTPException) as failure:
        _venda(c.db, c.venda.id, (SimpleNamespace(is_admin=True), uuid4()))
    assert failure.value.status_code == 404


def test_request_nao_aceita_string_true_ou_campos_extras():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        EstornoRequest(
            motivo="Motivo suficientemente longo",
            declaracao_operacao_nao_realizada="true",
        )
    with pytest.raises(ValidationError):
        EstornoRequest(
            motivo="Motivo suficientemente longo",
            declaracao_operacao_nao_realizada=True,
            ambiente_codigo=1,
        )


def test_validador_rejeita_protocolo_sem_autorizacao(context):
    c = context
    _, snapshot, _, _ = build(
        c.venda,
        c.connection,
        ambiente_codigo=1,
        destinatario=destinatario_proprio(c.venda),
        motivo=MOTIVO,
    )
    with pytest.raises(EstornoError):
        validate_xml(
            xml_estorno().replace(b"<cStat>100</cStat>", b"<cStat>225</cStat>"),
            snapshot,
        )


def test_falha_commit_antes_post_nao_transmite(context, monkeypatch):
    c = context

    def fail():
        raise RuntimeError("Falha de persistencia simulada")

    monkeypatch.setattr(c.db, "commit", fail)
    with pytest.raises(RuntimeError):
        create(c)
    c.db.rollback()
    c.api.issue_document.assert_not_called()
    assert c.db.query(IntNFeEstorno).count() == 0


def test_queda_de_processo_apos_tentativa_duravel_nao_reenvia(context):
    c = context
    c.api.issue_document.side_effect = RuntimeError(
        "Processo interrompido depois do envio"
    )
    with pytest.raises(RuntimeError):
        create(c)
    c.db.rollback()
    record = c.db.query(IntNFeEstorno).one()
    assert record.status == "enviando" and record.correlation_id is None
    assert create(c)["estorno"]["id"] == record.id
    assert c.api.issue_document.call_count == 1


def test_consulta_transporte_incerto_repeticao_so_get_e_preserva_original(context):
    c = context
    create(c)
    c.api.document_xml.side_effect = IntNFeError("EmissorIndisponivel")
    original = original_fields(c.venda)
    with pytest.raises(EstornoError):
        service.reconcile(c.db, c.venda, c.api)
    assert c.db.query(IntNFeEstorno).one().status == "processando"
    c.api.document_xml.side_effect = None
    assert service.reconcile(c.db, c.venda, c.api)["success"]
    assert c.api.issue_document.call_count == 1
    assert original_fields(c.venda) == original
    service.tentar_enfileirar_documento.assert_called_once_with(
        c.db, c.tenant, "intnfe", f"estorno:{c.db.query(IntNFeEstorno).one().id}"
    )


def test_consulta_tardia_nao_rebaixa_autorizacao_e_config_mudou_nao_bloqueia_get(
    context,
):
    c = context
    create(c)
    assert service.reconcile(c.db, c.venda, c.api)["success"]
    c.connection.emission_environment = 2
    c.connection.emission_enabled = False
    c.api.document_status.return_value = {"status": 4, "codigoErro": "225"}
    assert service.reconcile(c.db, c.venda, c.api)["success"]
    assert service.preview(c.db, c.venda)["success"]


def test_migration_cria_registro_duravel_e_reverte_sem_apagar_nota_original():
    import runpy
    from pathlib import Path
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import create_engine, inspect

    migration = runpy.run_path(
        str(
            Path(__file__).resolve().parents[2]
            / "alembic/versions/zzzzm20261020a1_intnfe_estorno.py"
        )
    )
    assert migration["down_revision"] == "zzzzl20261020a1"
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(
            text("CREATE TABLE vendas (id INTEGER PRIMARY KEY,nfe_status TEXT)")
        )
        conn.execute(text("INSERT INTO vendas VALUES (1,'autorizada')"))
        with Operations.context(MigrationContext.configure(conn)):
            migration["upgrade"]()
            assert "intnfe_estornos" in inspect(conn).get_table_names()
            assert {c["name"] for c in inspect(conn).get_columns("vendas")} >= {
                "nfe_estorno_status",
                "nfe_estorno_numero",
                "nfe_estorno_serie",
                "nfe_estorno_protocolo",
            }
            migration["downgrade"]()
        assert "intnfe_estornos" not in inspect(conn).get_table_names()
        assert (
            conn.execute(text("SELECT nfe_status FROM vendas WHERE id=1")).scalar_one()
            == "autorizada"
        )


@pytest.mark.parametrize(
    "cancel_status,attempted", [("solicitado", False), ("pendente", True)]
)
def test_pedido_cancelamento_em_curso_bloqueia_estorno_antes_da_rede(
    context, monkeypatch, cancel_status, attempted
):
    from datetime import datetime, timezone

    c = context
    c.venda.nfe_cancelamento_status = cancel_status
    c.venda.nfe_cancelamento_solicitado_em = (
        datetime.now(timezone.utc) if attempted else None
    )
    token = MagicMock()
    monkeypatch.setattr(service, "_access_token", token)
    with pytest.raises(EstornoError):
        create(c)
    token.assert_not_called()
    c.api.issue_document.assert_not_called()


def test_pendente_comercial_sem_tentativa_fiscal_permite_previa(context):
    c = context
    c.venda.nfe_cancelamento_status = "pendente"
    c.venda.nfe_cancelamento_solicitado_em = None
    assert service.preview(c.db, c.venda, destinatario_proprio_emitente=True)[
        "elegivel"
    ]


@pytest.mark.parametrize(
    "mutation", ["duas_notas", "dois_protocolos", "entity_utf16", "raiz_errada"]
)
def test_xml_estruturalmente_ambiguo_ou_dtd_nao_autoriza(context, mutation):
    from defusedxml import ElementTree as ET

    c = context
    _, snapshot, _, _ = build(
        c.venda,
        c.connection,
        ambiente_codigo=1,
        destinatario=destinatario_proprio(c.venda),
        motivo=MOTIVO,
    )
    xml = xml_estorno()
    if mutation == "entity_utf16":
        xml = (
            '<?xml version="1.0" encoding="utf-16"?><!DOCTYPE nfeProc [<!ENTITY x "ataque">]>'
            + xml.decode()
        ).encode("utf-16")
    elif mutation == "raiz_errada":
        xml = xml.replace(b"nfeProc", b"lote")
    else:
        from copy import deepcopy

        root = ET.fromstring(xml)
        tag = "NFe" if mutation == "duas_notas" else "protNFe"
        root.append(deepcopy(root.find("{http://www.portalfiscal.inf.br/nfe}" + tag)))
        xml = ET.tostring(root)
    with pytest.raises(EstornoError):
        validate_xml(xml, snapshot)


def test_danfe_pdf_nao_admite_html_do_emissor(context):
    c = context
    create(c)
    service.reconcile(c.db, c.venda, c.api)
    c.api.document_danfe.return_value = b"<html>erro</html>"
    with pytest.raises(EstornoError):
        service.download(c.db, c.venda, c.api, "danfe")
    c.api.document_danfe.return_value = b"%PDF-1.4\nconteudo QA"
    assert service.download(c.db, c.venda, c.api, "danfe")[0].startswith(b"%PDF-")


def test_estorno_cancelado_externamente_preserva_xml_historico_e_reabre_pendencia(
    context,
):
    from app.vendas.fiscal_status import pendencia_fiscal_cancelamento

    c = context
    original = original_fields(c.venda)
    create(c)
    assert service.reconcile(c.db, c.venda, c.api)["success"]
    record = c.db.query(IntNFeEstorno).one()
    xml = record.xml
    assert not pendencia_fiscal_cancelamento(c.venda)
    c.api.document_status.return_value = {"status": 5}
    result = service.reconcile(c.db, c.venda, c.api)
    assert not result["success"] and result["estorno"]["status"] == "cancelado"
    assert record.xml == xml and record.xml_validado
    assert pendencia_fiscal_cancelamento(c.venda)
    assert original_fields(c.venda) == original
    assert service.download(c.db, c.venda, c.api, "xml")[0] == xml.encode()
    assert result["estorno"]["xml_url"].endswith("/estorno/xml")
    assert service.tentar_enfileirar_documento.call_count == 2


@pytest.mark.parametrize("protocolo_tem_data", [True, False])
def test_consulta_em_outro_mes_preserva_data_do_xml(
    context, monkeypatch, protocolo_tem_data
):
    from datetime import datetime, timezone

    c = context
    create(c)

    class ConsultaTardia:
        @staticmethod
        def now(tz):
            return datetime(2027, 1, 15, tzinfo=tz)

    monkeypatch.setattr(service, "datetime", ConsultaTardia)
    if not protocolo_tem_data:
        c.api.document_xml.return_value = xml_estorno().replace(
            b"<dhRecbto>2026-10-20T16:22:00Z</dhRecbto>", b""
        )
    assert service.reconcile(c.db, c.venda, c.api)["success"]
    record = c.db.query(IntNFeEstorno).one()
    expected = (
        datetime(2026, 10, 20, 16, 22, tzinfo=timezone.utc)
        if protocolo_tem_data
        else datetime(2026, 10, 20, 16, 21, 24, tzinfo=timezone.utc)
    )
    # SQLite não preserva tzinfo na coluna DateTime(timezone=True); PostgreSQL preserva.
    persisted = record.autorizado_em
    persisted = (
        persisted.astimezone(timezone.utc)
        if persisted.tzinfo
        else persisted.replace(tzinfo=timezone.utc)
    )
    assert persisted == expected
    assert (
        validate_xml(c.api.document_xml.return_value, record.snapshot)["autorizado_em"]
        == expected
    )


@pytest.mark.parametrize("data_xml", ["data-invalida", "2026-10-20T16:22:00"])
def test_timestamp_xml_invalido_ou_sem_fuso_nao_confirma_estorno(context, data_xml):
    c = context
    create(c)
    c.api.document_xml.return_value = xml_estorno().replace(
        b"2026-10-20T16:22:00Z", data_xml.encode()
    )
    result = service.reconcile(c.db, c.venda, c.api)
    assert not result["success"] and result["estorno"]["status"] == "divergente"
