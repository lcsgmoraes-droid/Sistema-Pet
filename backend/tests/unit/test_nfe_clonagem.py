from copy import deepcopy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock
import unicodedata

import pytest
from fastapi import HTTPException

from app.intnfe.client import IntNFeError
from app.nfe import clone_service as service
from app.nfe.clone_xml import payload_from_xml
from app.intnfe.xml_integrity import INVALID_MESSAGE
from tests.helpers.signed_nfe import make_key, sign_nfe

TENANT = "11111111-1111-1111-1111-111111111111"
CNPJ = "33590794000140"
XML = f"""<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe"><NFe><infNFe Id="NFe{"1" * 44}">
<ide><mod>55</mod><tpNF>1</tpNF><serie>1</serie><nNF>1648</nNF><tpAmb>1</tpAmb><natOp>Venda</natOp><indFinal>1</indFinal><indPres>1</indPres><finNFe>1</finNFe><indIntermed>0</indIntermed></ide>
<emit><CNPJ>{CNPJ}</CNPJ><xNome>Empresa</xNome><IE>123</IE><CRT>3</CRT><enderEmit><xLgr>Rua Um</xLgr><nro>1</nro><xBairro>Centro</xBairro><cMun>3541406</cMun><xMun>Presidente Prudente</xMun><UF>SP</UF><CEP>19010000</CEP></enderEmit></emit>
<dest><CPF>52998224725</CPF><xNome>Cliente</xNome><indIEDest>9</indIEDest><enderDest><xLgr>Rua Dois</xLgr><nro>2</nro><xBairro>Centro</xBairro><cMun>3541406</cMun><xMun>Presidente Prudente</xMun><UF>SP</UF></enderDest></dest>
<det nItem="1"><prod><cProd>SKU1</cProd><cEAN>SEM GTIN</cEAN><xProd>Ração</xProd><NCM>23099010</NCM><CFOP>5102</CFOP><uCom>UN</uCom><qCom>2</qCom><vUnCom>10</vUnCom><vProd>20</vProd><cEANTrib>SEM GTIN</cEANTrib><uTrib>UN</uTrib><qTrib>2</qTrib><vUnTrib>10</vUnTrib><indTot>1</indTot></prod><imposto><vTotTrib>0</vTotTrib><ICMS><ICMS00><orig>0</orig><CST>00</CST><modBC>3</modBC><vBC>20</vBC><pICMS>18</pICMS><vICMS>3.60</vICMS></ICMS00></ICMS><PIS><PISAliq><CST>01</CST><vBC>20</vBC><pPIS>1.65</pPIS><vPIS>0.33</vPIS></PISAliq></PIS><COFINS><COFINSAliq><CST>01</CST><vBC>20</vBC><pCOFINS>7.6</pCOFINS><vCOFINS>1.52</vCOFINS></COFINSAliq></COFINS></imposto></det>
<total><ICMSTot><vBC>20</vBC><vICMS>3.60</vICMS><vProd>20</vProd><vFrete>0</vFrete><vNF>20</vNF></ICMSTot></total><transp><modFrete>9</modFrete></transp><pag><detPag><indPag>0</indPag><tPag>17</tPag><vPag>20</vPag></detPag><vTroco>0</vTroco></pag><infAdic><infCpl>Observação preservada</infCpl><infAdFisco>Informação fiscal</infAdFisco></infAdic></infNFe></NFe></nfeProc>"""


def payload():
    return payload_from_xml(XML, cnpj=CNPJ, environment=1)[0]


@pytest.fixture(scope="module")
def signed_clone_source():
    cnpj = "11222333000181"
    key = make_key("352610" + cnpj + "55001000001648112345678")
    xml = "".join(
        character
        for character in unicodedata.normalize("NFD", XML)
        if not unicodedata.combining(character)
    )
    xml = xml.replace(CNPJ, cnpj).replace("1" * 44, key)
    xml = xml.replace(
        "</ide>", "<dhEmi>2026-10-26T10:00:00-03:00</dhEmi></ide>"
    ).replace(
        "</nfeProc>",
        f"<protNFe><infProt><chNFe>{key}</chNFe><cStat>100</cStat>"
        "</infProt></protNFe></nfeProc>",
    )
    return SimpleNamespace(cnpj=cnpj, key=key, unsigned=xml, xml=sign_nfe(xml))


def source_context(monkeypatch, document, **overrides):
    sale = SimpleNamespace(
        id=42,
        nfe_provider="intnfe",
        nfe_correlation_id="source-document",
        nfe_chave=document.key,
        nfe_modelo=55,
        nfe_tipo="nfe",
        nfe_numero=1648,
        nfe_serie="1",
        nfe_status="autorizada",
        nfe_xml=document.xml,
    )
    sale.__dict__.update(overrides)
    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = sale
    monkeypatch.setattr(
        service, "get_tenant", Mock(return_value=SimpleNamespace(cnpj=document.cnpj))
    )
    monkeypatch.setattr(
        service, "_connection", lambda *_args: SimpleNamespace(emission_environment=1)
    )
    download = Mock(return_value=document.xml)
    monkeypatch.setattr(service, "download_document", download)
    return sale, db, download


@pytest.mark.parametrize("as_text", [False, True])
def test_preparar_valida_assinatura_do_cache_sem_alterar_original(
    monkeypatch, signed_clone_source, as_text
):
    source = signed_clone_source
    cached = source.xml.decode() if as_text else source.xml
    sale, db, download = source_context(monkeypatch, source, nfe_xml=cached)

    result, xml = service.prepare(
        db, TENANT, Mock(), {"provedor": "intnfe", "venda_id": sale.id}
    )

    assert result["dados"]["produtos"][0]["descricao"] == "Racao"
    assert result["numero"] is None
    assert result["origem"]["numero"] == "1648"
    assert xml == source.xml.decode()
    assert sale.nfe_xml is cached
    download.assert_not_called()
    db.commit.assert_not_called()


def test_preparar_recupera_so_conteudo_comprovado_pela_assinatura_sem_regravar_cache(
    monkeypatch, signed_clone_source
):
    source = signed_clone_source
    damaged = source.xml.decode().replace("Racao", "Ração")
    sale, db, download = source_context(monkeypatch, source, nfe_xml=damaged)

    result, verified = service.prepare(
        db, TENANT, Mock(), {"provedor": "intnfe", "venda_id": sale.id}
    )

    assert result["dados"]["produtos"][0]["descricao"] == "Racao"
    assert "Ração" not in verified
    assert sale.nfe_xml is damaged
    download.assert_not_called()
    db.commit.assert_not_called()


@pytest.mark.parametrize(
    "invalid_source",
    ["unsigned", "changed_value", "wrong_key", "wrong_company", "wrong_model"],
)
def test_preparar_recusa_origem_sem_assinatura_e_vinculo_validos(
    monkeypatch, signed_clone_source, invalid_source
):
    source = signed_clone_source
    sale, db, download = source_context(monkeypatch, source)
    if invalid_source == "unsigned":
        sale.nfe_xml = source.unsigned
    elif invalid_source == "changed_value":
        sale.nfe_xml = source.xml.replace(b"<vProd>20</vProd>", b"<vProd>21</vProd>")
    elif invalid_source == "wrong_key":
        sale.nfe_chave = make_key("352610" + source.cnpj + "55001000001649112345678")
    elif invalid_source == "wrong_company":
        service.get_tenant.return_value.cnpj = CNPJ
    else:
        sale.nfe_tipo = "nfce"
    cached = sale.nfe_xml

    with pytest.raises(HTTPException) as failure:
        service.prepare(db, TENANT, Mock(), {"provedor": "intnfe", "venda_id": sale.id})

    assert failure.value.status_code == 502
    assert failure.value.detail == INVALID_MESSAGE
    assert sale.nfe_xml is cached
    download.assert_not_called()
    db.commit.assert_not_called()


def test_clonagem_nao_expoe_erro_tecnico_do_guardiao(monkeypatch, signed_clone_source):
    sale, db, _download = source_context(monkeypatch, signed_clone_source)
    monkeypatch.setattr(
        service,
        "ensure_signed_xml",
        Mock(
            side_effect=IntNFeError(
                "XmlInvalido", provider_message="<html>privado</html>"
            )
        ),
    )

    with pytest.raises(HTTPException) as failure:
        service.source_xml(
            db, TENANT, Mock(), {"provedor": "intnfe", "venda_id": sale.id}
        )

    assert failure.value.status_code == 502
    assert failure.value.detail == INVALID_MESSAGE
    assert "privado" not in failure.value.detail


def row(**overrides):
    values = dict(
        id=7,
        tenant_id=TENANT,
        dados=payload(),
        xml_origem=XML,
        origem={"numero": "1648", "serie": "1"},
        modelo=55,
        status="rascunho",
        idempotency_key=None,
        enviado_em=None,
        correlation_id=None,
        numero=None,
        chave=None,
        protocolo=None,
        motivo=None,
        xml=None,
        cancelamento_status=None,
        cancelamento_codigo=None,
        cancelamento_motivo=None,
        cancelamento_solicitado_em=None,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def configure(monkeypatch, record):
    monkeypatch.setattr(service, "get_clone", lambda *_args, **_kwargs: record)
    monkeypatch.setattr(
        service,
        "_connection",
        lambda *_args, **_kwargs: SimpleNamespace(emission_environment=1),
    )
    monkeypatch.setattr(service, "_access_token", lambda *_args, **_kwargs: "token")
    monkeypatch.setattr(
        service,
        "read_numbering",
        lambda *_args: SimpleNamespace(
            series=[
                SimpleNamespace(
                    modelo=55, ambienteCodigo=1, serie="1", ultimoNumero=1650
                )
            ]
        ),
    )
    monkeypatch.setattr(service, "log_action", lambda *_args, **_kwargs: None)


def test_xml_preserva_dados_e_omite_identidade_fiscal():
    data, model = payload_from_xml(XML, cnpj=CNPJ, environment=1)
    assert model == 55
    assert data["destinatario"]["cpf"] == "52998224725"
    assert data["produtos"][0]["impostos"]["icms"] == {
        "origem": "0",
        "cst": "00",
        "aliquota": 18.0,
        "valor": 3.6,
    }
    assert data["informacoesAdicionais"] == "Observação preservada"
    assert data["informacoesFisco"] == "Informação fiscal"
    assert (
        "numero" not in data and "chaveAcesso" not in data and "protocolo" not in data
    )


@pytest.mark.parametrize(
    "before,after,missing",
    [
        ("SEM GTIN", "7891234567895", "cEAN"),
        ("<modBC>3</modBC>", "<modBC>0</modBC>", "modBC"),
        ("<indPag>0</indPag>", "<indPag>1</indPag>", "indPag"),
        ("<vBC>20</vBC>", "<vBC>10</vBC>", "vBC"),
    ],
)
def test_xml_sem_equivalente_bloqueia_sem_descartar(before, after, missing):
    with pytest.raises(HTTPException) as exc:
        payload_from_xml(XML.replace(before, after, 1), cnpj=CNPJ, environment=1)
    assert exc.value.status_code == 422
    assert missing in str(exc.value.detail)


def test_xml_de_outra_empresa_e_recusado():
    with pytest.raises(HTTPException) as exc:
        payload_from_xml(XML, cnpj="00000000000000", environment=1)
    assert exc.value.status_code == 403


@pytest.mark.parametrize(
    "xml",
    [
        "<html>502 Bad Gateway",
        XML.replace("<mod>55</mod>", "<mod>inválido</mod>"),
        XML.replace("<vProd>20</vProd>", "<vProd>nan</vProd>", 1),
    ],
)
def test_xml_invalido_produz_erro_legivel(xml):
    with pytest.raises(HTTPException) as exc:
        payload_from_xml(xml, cnpj=CNPJ, environment=1)
    assert exc.value.status_code == 422
    assert "inválido" in exc.value.detail


def test_recalcula_tributos_e_permite_salvar_novamente():
    original = payload()
    edited = deepcopy(original)
    edited["produtos"][0]["quantidade"] = 3
    edited["pagamentos"][0]["valor"] = 30
    result = service.normalize_data(edited, original)
    assert result["produtos"][0]["valorTotal"] == 30
    assert result["produtos"][0]["impostos"]["icms"]["valor"] == 5.4
    assert result["produtos"][0]["impostos"]["pis"]["valor"] == 0.5
    assert service.normalize_data(result, original, previous=result) == result
    assert original["produtos"][0]["impostos"]["icms"]["valor"] == 3.6


def test_clone_permite_revisar_operacao_intermediada_sem_alterar_identidade_fiscal():
    original = payload()
    edited = deepcopy(original)
    edited["indicadorPresenca"] = "2"
    edited["intermediador"] = {
        "cnpj": "15.436.940/0001-03",
        "identificadorCadastro": "  LOJA-QA-CLONE  ",
    }
    result = service.normalize_data(edited, original, modelo=55)
    assert result["indicadorPresenca"] == "2"
    assert result["intermediador"] == {
        "cnpj": "15436940000103",
        "identificadorCadastro": "LOJA-QA-CLONE",
    }
    for field in ("emitente", "serie", "ambienteCodigo", "produtos", "pagamentos"):
        assert result[field] == original[field]
    assert original["indicadorPresenca"] == "1"
    assert "intermediador" not in original
    assert (
        service.normalize_data(result, original, previous=result, modelo=55) == result
    )


@pytest.mark.parametrize("presence", ["1", "9", "", "99", True, []])
def test_intermediador_exige_presenca_internet_valida(presence):
    original = payload()
    edited = deepcopy(original)
    edited.update(
        indicadorPresenca=presence,
        intermediador={"cnpj": "11222333000181", "identificadorCadastro": "LOJA-QA"},
    )
    with pytest.raises(HTTPException) as exc:
        service.normalize_data(edited, original, modelo=55)
    assert exc.value.status_code == 422
    assert "presença" in exc.value.detail


@pytest.mark.parametrize(
    "intermediary",
    [
        {},
        {"cnpj": "11222333000181"},
        {"cnpj": "00000000000000", "identificadorCadastro": "LOJA-QA"},
        {"cnpj": "11222333000182", "identificadorCadastro": "LOJA-QA"},
        {"cnpj": "11222333000181", "identificadorCadastro": "   "},
        {"cnpj": "11222333000181", "identificadorCadastro": "x" * 61},
        {"cnpj": "11222333000181", "identificadorCadastro": 123},
        {
            "cnpj": "11222333000181",
            "identificadorCadastro": "LOJA-QA",
            "token": "indevido",
        },
        "11222333000181",
    ],
)
def test_intermediador_invalido_e_recusado_antes_de_salvar(intermediary):
    original = payload()
    edited = deepcopy(original)
    edited.update(indicadorPresenca="2", intermediador=intermediary)
    with pytest.raises(HTTPException) as exc:
        service.normalize_data(edited, original, modelo=55)
    assert exc.value.status_code == 422


def test_clone_nfce_preserva_presenca_e_recusa_nova_intermediacao():
    original = payload()
    assert service.normalize_data(deepcopy(original), original, modelo=65) == original
    for change in (
        {"indicadorPresenca": "2"},
        {
            "intermediador": {
                "cnpj": "11222333000181",
                "identificadorCadastro": "LOJA-QA",
            }
        },
    ):
        edited = deepcopy(original)
        edited.update(change)
        with pytest.raises(HTTPException) as exc:
            service.normalize_data(edited, original, modelo=65)
        assert exc.value.status_code == 422
        assert "somente para NF-e" in exc.value.detail


def test_clone_permite_operacao_direta_sem_carregar_intermediador_anterior():
    original = payload()
    original.update(
        indicadorPresenca="2",
        intermediador={
            "cnpj": "11222333000181",
            "identificadorCadastro": "LOJA-ANTERIOR",
        },
    )
    edited = deepcopy(original)
    edited["indicadorPresenca"] = "1"
    del edited["intermediador"]
    result = service.normalize_data(edited, original, modelo=55)
    assert "intermediador" not in result
    assert result["indicadorPresenca"] == "1"
    assert result["produtos"] == original["produtos"]


@pytest.mark.parametrize(
    "change",
    [
        lambda data: data.update(serie="7"),
        lambda data: data.update(ambienteCodigo=2),
        lambda data: data.update(finalidade="4"),
        lambda data: data.update(tipoOperacao="0"),
        lambda data: data["produtos"][0].update(ncm="00000000"),
        lambda data: data["produtos"][0]["impostos"]["icms"].update(cst="40"),
    ],
)
def test_revisao_comercial_nao_libera_alterar_identidade_ou_tributacao(change):
    original = payload()
    edited = deepcopy(original)
    edited.update(
        indicadorPresenca="2",
        intermediador={"cnpj": "11222333000181", "identificadorCadastro": "LOJA-QA"},
    )
    change(edited)
    with pytest.raises(HTTPException) as exc:
        service.normalize_data(edited, original, modelo=55)
    assert exc.value.status_code == 422


def test_criar_clone_nfce_nao_libera_intermediacao_nem_persiste_dados_invalidos(
    monkeypatch,
):
    original = payload()
    monkeypatch.setattr(
        service,
        "prepare",
        lambda *_args: (
            {"dados": original, "origem": {"modelo": 65}, "modelo": 65},
            XML,
        ),
    )
    edited = deepcopy(original)
    edited.update(
        indicadorPresenca="2",
        intermediador={"cnpj": "11222333000181", "identificadorCadastro": "LOJA-QA"},
    )
    db, api = Mock(), Mock()
    with pytest.raises(HTTPException) as exc:
        service.create(db, TENANT, 1, api, {}, edited)
    assert exc.value.status_code == 422
    db.add.assert_not_called()
    db.commit.assert_not_called()
    api.issue_document.assert_not_called()


def test_clone_ja_enviado_nao_permite_revisar_intermediador(monkeypatch):
    record = row(status="autorizada", correlation_id="clone-ja-enviado")
    monkeypatch.setattr(service, "get_clone", lambda *_args, **_kwargs: record)
    edited = deepcopy(record.dados)
    edited.update(
        indicadorPresenca="2",
        intermediador={"cnpj": "11222333000181", "identificadorCadastro": "LOJA-QA"},
    )
    db = Mock()
    with pytest.raises(HTTPException) as exc:
        service.update(db, TENANT, 1, record.id, edited)
    assert exc.value.status_code == 409
    assert "intermediador" not in record.dados
    db.commit.assert_not_called()


@pytest.mark.parametrize(
    "change",
    [
        lambda data: data.update(numero=1649),
        lambda data: data["emitente"].update(cnpj="00000000000000"),
        lambda data: data["pagamentos"][0].update(valor=19),
        lambda data: data["produtos"][0].update(quantidade=-1),
    ],
)
def test_dados_indevidos_ou_total_inconsistente_nao_sao_salvos(change):
    original = payload()
    edited = deepcopy(original)
    change(edited)
    with pytest.raises(HTTPException):
        service.normalize_data(edited, original)


def test_emite_apenas_uma_vez_com_chave_persistida_e_numero_do_emissor(monkeypatch):
    record = row()
    configure(monkeypatch, record)
    db = Mock()
    api = Mock()

    def send(_token, _kind, data, key):
        assert db.commit.called
        assert record.idempotency_key == key
        assert "numero" not in data
        return {"correlationId": "clone-correlation"}

    api.issue_document.side_effect = send
    api.document_status.return_value = {
        "status": 3,
        "numero": 1651,
        "chaveAcesso": "2" * 44,
    }
    api.document_xml.return_value = b"<xml/>"
    first = service.issue(db, TENANT, 1, record.id, api)
    second = service.issue(db, TENANT, 1, record.id, api)
    assert first["numero"] == second["numero"] == "1651"
    assert api.issue_document.call_count == 1
    assert record.origem["numero"] == "1648"


def test_envio_incerto_recupera_mesma_chave_e_corpo(monkeypatch):
    record = row(
        status="inconclusiva",
        idempotency_key="same-key",
        enviado_em=datetime.now(timezone.utc) - timedelta(minutes=3),
    )
    configure(monkeypatch, record)
    api = Mock()
    api.issue_document.return_value = {"correlationId": "recovered"}
    api.document_status.return_value = {"status": 2, "numero": 1651}
    result = service.consult(Mock(), TENANT, 7, api)
    api.issue_document.assert_called_once_with("token", "nfe", record.dados, "same-key")
    assert result["correlation_id"] == "recovered"


def test_envio_fora_janela_nunca_e_repetido(monkeypatch):
    record = row(
        status="inconclusiva",
        idempotency_key="same-key",
        enviado_em=datetime.now(timezone.utc) - timedelta(hours=24),
    )
    configure(monkeypatch, record)
    api = Mock()
    service.consult(Mock(), TENANT, 7, api)
    api.issue_document.assert_not_called()


def test_consulta_preserva_autorizacao_se_xml_temporariamente_indisponivel(monkeypatch):
    record = row(status="autorizada", correlation_id="known", numero="1651")
    configure(monkeypatch, record)
    api = Mock()
    api.document_status.return_value = {"status": 3, "numero": 1651}
    api.document_xml.side_effect = IntNFeError("Indisponivel", status=503)
    db = Mock()
    result = service.consult(db, TENANT, 7, api)
    assert result["status"] == "autorizada"
    db.commit.assert_called_once()


def test_cancelamento_incerto_preserva_nota_e_confirma_por_evento(monkeypatch):
    record = row(
        status="autorizada", correlation_id="known", numero="1651", xml="<xml/>"
    )
    configure(monkeypatch, record)
    api = Mock()
    api.cancel_document.side_effect = IntNFeError("Proxy", status=502, uncertain=True)
    api.document_status.return_value = {"status": 3, "numero": 1651}
    api.document_events.return_value = [
        {
            "tipoEventoCodigo": "110111",
            "autorizado": True,
            "protocolo": "123",
            "codigoRetorno": "135",
        }
    ]
    result = service.cancel(
        Mock(), TENANT, 1, 7, api, "Cancelamento para corrigir valores"
    )
    assert result["status"] == "cancelada"
    assert result["cancelamento_status"] == "confirmado"
    api.cancel_document.assert_called_once()


def test_numero_remoto_atrasado_bloqueia_sem_emitir(monkeypatch):
    record = row()
    configure(monkeypatch, record)
    monkeypatch.setattr(
        service, "read_numbering", lambda *_args: SimpleNamespace(series=[])
    )
    api = Mock()
    with pytest.raises(HTTPException) as exc:
        service.issue(Mock(), TENANT, 1, 7, api)
    assert exc.value.status_code == 409
    api.issue_document.assert_not_called()


def test_tributacao_st_nao_e_recalculada_sem_revisao_fiscal():
    original = payload()
    original["produtos"][0]["impostos"]["icms"]["valorStRetido"] = 5
    edited = deepcopy(original)
    edited["produtos"][0]["quantidade"] = 3
    edited["pagamentos"][0]["valor"] = 30
    with pytest.raises(HTTPException) as exc:
        service.normalize_data(edited, original)
    assert "tributação especial" in exc.value.detail


def test_criacao_rascunho_nao_emite_nem_cria_venda(monkeypatch):
    prepared = {"origem": {"numero": "1648"}, "dados": payload(), "modelo": 55}
    monkeypatch.setattr(service, "prepare", lambda *_args: (prepared, XML))
    monkeypatch.setattr(service, "log_action", lambda *_args, **_kwargs: None)
    db = Mock()
    api = Mock()
    result = service.create(db, TENANT, 1, api, {"id": "ignored"}, prepared["dados"])
    added = db.add.call_args.args[0]
    assert added.__tablename__ == "notas_fiscais_clones"
    assert added.xml_origem == XML
    assert added.numero is None
    assert result["status"] == "rascunho"
    assert db.add.call_count == 1
    api.issue_document.assert_not_called()


def test_cancelamento_pendente_antigo_consulta_antes_de_nova_tentativa(monkeypatch):
    record = row(
        status="autorizada",
        correlation_id="known",
        numero="1651",
        xml="<xml/>",
        cancelamento_status="pendente",
        cancelamento_solicitado_em=datetime.now(timezone.utc) - timedelta(minutes=3),
    )
    configure(monkeypatch, record)
    api = Mock()
    api.document_status.return_value = {"status": 3, "numero": 1651}
    api.document_events.return_value = []
    api.cancel_document.return_value = {
        "autorizado": True,
        "protocolo": "123",
        "codigoRetorno": "135",
    }
    result = service.cancel(
        Mock(), TENANT, 1, 7, api, "Cancelamento para corrigir valores"
    )
    assert result["status"] == "cancelada"
    calls = [call[0] for call in api.mock_calls]
    assert calls.index("document_status") < calls.index("cancel_document")


def test_cancelamento_em_andamento_apenas_consulta(monkeypatch):
    record = row(
        status="autorizada",
        correlation_id="known",
        numero="1651",
        xml="<xml/>",
        cancelamento_status="solicitado",
        cancelamento_solicitado_em=datetime.now(timezone.utc) - timedelta(minutes=5),
    )
    configure(monkeypatch, record)
    api = Mock()
    api.document_status.return_value = {"status": 3, "numero": 1651}
    api.document_events.return_value = []
    result = service.cancel(
        Mock(), TENANT, 1, 7, api, "Cancelamento para corrigir valores"
    )
    assert result["status"] == "autorizada"
    api.cancel_document.assert_not_called()
