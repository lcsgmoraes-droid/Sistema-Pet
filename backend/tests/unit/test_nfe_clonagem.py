from copy import deepcopy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from app.intnfe.client import IntNFeError
from app.nfe import clone_service as service
from app.nfe.clone_xml import payload_from_xml

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
