from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from defusedxml import ElementTree as ET
import pytest

from app.intnfe.client import IntNFeClient, IntNFeError
from app.services import xml_contabilidade_documentos as documentos
from app.services import xml_contabilidade_eventos as eventos
from app.services.xml_contabilidade_common import XmlContabilidadeError

CHAVE = "35261033590794000140650030000000441241595909"
CNPJ = "33590794000140"
PROT = "135260000000001"
NOTA = f"""<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe"><NFe><infNFe Id="NFe{CHAVE}"><ide><mod>65</mod><dhEmi>2026-10-19T12:00:00-03:00</dhEmi><tpAmb>1</tpAmb><tpNF>1</tpNF></ide><emit><CNPJ>{CNPJ}</CNPJ></emit></infNFe></NFe><protNFe><infProt><chNFe>{CHAVE}</chNFe><cStat>100</cStat></infProt></protNFe></nfeProc>""".encode()


def xml_evento(
    tipo="110111",
    seq=1,
    chave=CHAVE,
    cnpj=CNPJ,
    ambiente="1",
    status="135",
    protocolo=PROT,
    data="2026-10-19T13:00:00-03:00",
):
    return f"""<?xml version="1.0" encoding="UTF-8"?><procEventoNFe xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.00"><evento><infEvento Id="ID{tipo}{chave}{seq:02d}"><tpAmb>{ambiente}</tpAmb><CNPJ>{cnpj}</CNPJ><chNFe>{chave}</chNFe><dhEvento>{data}</dhEvento><tpEvento>{tipo}</tpEvento><nSeqEvento>{seq}</nSeqEvento></infEvento><Signature xmlns="http://www.w3.org/2000/09/xmldsig#"><SignatureValue>bytes-preservados</SignatureValue></Signature></evento><retEvento><infEvento><tpAmb>{ambiente}</tpAmb><chNFe>{chave}</chNFe><tpEvento>{tipo}</tpEvento><nSeqEvento>{seq}</nSeqEvento><cStat>{status}</cStat><nProt>{protocolo}</nProt><dhRegEvento>{data}</dhRegEvento></infEvento></retEvento></procEventoNFe>""".encode()


def row(xml=None, tipo="110111", **changes):
    return {
        "autorizado": True,
        "tipoEventoCodigo": int(tipo),
        "protocolo": PROT,
        "xmlEvento": xml.decode() if xml else None,
        **changes,
    }


def coleta(rows, *, cancelada=False, detalhe=None):
    return eventos.coletar_eventos(
        ET.fromstring(NOTA),
        {"_eventos_intnfe": rows, **(detalhe or {})},
        CHAVE,
        CNPJ,
        cancelada=cancelada,
    )


@pytest.mark.parametrize("tipo", ["nfe", "nfce"])
def test_cliente_eventos_usa_endpoint_oficial_e_lista_completa(tipo):
    api = object.__new__(IntNFeClient)
    api._request = Mock(return_value=[row(xml_evento())])
    assert api.document_events("segredo", tipo, "correlacao-1")
    api._request.assert_called_once_with(
        "GET", f"/{tipo}/correlacao-1/eventos", token="segredo"
    )


@pytest.mark.parametrize("resposta", [{"eventos": []}, [None], "[]"])
def test_cliente_eventos_rejeita_lista_invalida(resposta):
    api = object.__new__(IntNFeClient)
    api._request = Mock(return_value=resposta)
    with pytest.raises(IntNFeError, match="RespostaInvalida"):
        api.document_events("token", "nfe", "correlacao-1")


def test_todas_sequencias_cce_cancelamento_manifestacao_e_bytes_originais():
    xmls = [
        xml_evento("110110", 1),
        xml_evento("110110", 2),
        xml_evento(),
        xml_evento("210210", 1),
    ]
    rows = [
        row(xml, tipo=tipo)
        for xml, tipo in zip(xmls, ["110110", "110110", "110111", "210210"])
    ]
    arquivos, resumo, cancelamento = coleta(rows + rows, cancelada=True)
    assert [xml for _, xml in arquivos] == xmls
    assert len(resumo) == 4 and cancelamento
    assert [e["sequencia"] for e in resumo if e["tipo"] == "110110"] == [1, 2]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"chave": "9" * 44},
        {"cnpj": "11111111000111"},
        {"ambiente": "2"},
        {"status": "580"},
        {"protocolo": ""},
        {"data": "ontem"},
    ],
)
def test_evento_de_outra_nota_empresa_ambiente_ou_sem_protocolo_bloqueia(kwargs):
    with pytest.raises(XmlContabilidadeError):
        coleta([row(xml_evento(**kwargs))])


def test_cancelada_sem_comprovante_nao_gera_zip_com_aviso():
    with pytest.raises(XmlContabilidadeError, match="cancelamento.*110111.*parcial"):
        coleta([], cancelada=True)


def test_cancelamento_por_substituicao_tambem_incluido_como_cancelada():
    _, resumo, cancelamento = coleta(
        [row(xml_evento("110112"), tipo="110112")], cancelada=True
    )
    assert cancelamento and resumo[0]["tipo"] == "110112"


def test_cancelamento_sem_vinculacao_a_nota_nao_confirma_cancelamento():
    with pytest.raises(XmlContabilidadeError, match="protocolo de registro"):
        coleta([row(xml_evento(status="136"))], cancelada=True)


def test_evento_confirmado_sem_xml_e_cce_com_sequencia_faltante_bloqueiam():
    with pytest.raises(XmlContabilidadeError, match="110110.*ausente"):
        coleta([row(tipo="110110")])
    with pytest.raises(XmlContabilidadeError, match="sequência 1.*sequência 2"):
        coleta([row(xml_evento("110110", 3), tipo="110110")])


@pytest.mark.parametrize("campo", ["xmlCartaCorrecao", "xmlCancelamento", "xmlEvento"])
def test_campos_legados_importados_nao_incluem_eventos_nem_consultam_links(
    monkeypatch, campo
):
    from app.nfe import documentos as documentos_api

    baixar = Mock(side_effect=AssertionError("Não consultar documentos importados"))
    monkeypatch.setattr(documentos_api, "baixar_link_documento", baixar)
    detalhe = {
        campo: [xml_evento().decode(), "https://exemplo.invalid/documento-privado"]
    }
    assert coleta([], detalhe=detalhe) == ([], [], False)
    with pytest.raises(XmlContabilidadeError, match="cancelamento"):
        coleta([], cancelada=True, detalhe=detalhe)
    baixar.assert_not_called()


def test_tentativa_rejeitada_nao_e_incluida_como_evento_fiscal():
    assert coleta([row(autorizado=False)]) == ([], [], False)


def test_protocolo_metadados_divergente_bloqueia():
    with pytest.raises(XmlContabilidadeError, match="diverge"):
        coleta([row(xml_evento(), protocolo="135260000000999")])


def test_coleta_consulta_eventos_mesmo_com_nota_xml_em_cache(monkeypatch):
    doc = documentos.Documento(
        "intnfe",
        "7",
        CHAVE,
        65,
        "autorizada",
        datetime(2026, 10, 19, 12),
        venda=SimpleNamespace(nfe_xml=NOTA),
    )
    monkeypatch.setattr(documentos, "_cnpj_empresa", lambda *_: CNPJ)
    buscar = Mock(
        return_value={
            "_eventos_intnfe": [row(xml_evento(data="2026-11-02T12:00:00-03:00"))]
        }
    )
    monkeypatch.setattr(documentos, "_obter_eventos", buscar)
    arquivos, notas = documentos._coletar_arquivos(
        Mock(), uuid4(), [doc], date(2026, 10, 1), date(2026, 10, 31)
    )
    buscar.assert_called_once()
    assert len(arquivos) == 2 and notas[0]["status"] == "cancelada"
    assert "após o período" in notas[0]["observacao"]


def test_falha_consulta_eventos_nao_expoe_segredo_nem_gera_pacote(monkeypatch):
    from app.intnfe import client

    api = Mock()
    api.document_events.side_effect = RuntimeError("token-secreto")
    monkeypatch.setattr(client, "IntNFeClient", lambda: api)
    from app.intnfe import emission

    monkeypatch.setattr(emission, "_connection", lambda *_a, **_kw: Mock())
    monkeypatch.setattr(emission, "_access_token", lambda *_: "segredo")
    doc = SimpleNamespace(
        documento_id="1", venda=SimpleNamespace(nfe_tipo="nfe", nfe_correlation_id="id")
    )
    with pytest.raises(XmlContabilidadeError, match="todos os eventos") as erro:
        eventos.obter_eventos_intnfe(Mock(), uuid4(), doc)
    assert "secreto" not in str(erro.value)
    api.close.assert_called_once()
