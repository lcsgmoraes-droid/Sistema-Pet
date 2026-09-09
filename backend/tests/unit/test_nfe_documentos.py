from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from app.nfe import documentos
from app.nfe.danfe_nfce import gerar_danfe_nfce, validar_xml_nota

CHAVE = "35260933590794000140650030000000441241595909"
XML = f"""<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe"><NFe><infNFe Id="NFe{CHAVE}">
<ide><mod>65</mod><nNF>44</nNF><serie>3</serie><dhEmi>2026-09-09T12:00:00-03:00</dhEmi><tpAmb>1</tpAmb></ide>
<emit><xNome>Loja teste</xNome><CNPJ>33590794000140</CNPJ><enderEmit><xLgr>Rua Teste</xLgr><nro>1</nro><xMun>Presidente Prudente</xMun><UF>SP</UF></enderEmit></emit>
<det><prod><cProd>123</cProd><xProd>Ração teste</xProd><qCom>1.097</qCom><uCom>KG</uCom><vUnCom>9.30</vUnCom><vProd>10.20</vProd></prod></det>
<total><ICMSTot><vProd>10.20</vProd><vNF>10.20</vNF></ICMSTot></total>
<pag><detPag><tPag>17</tPag><vPag>10.20</vPag></detPag></pag></infNFe>
<infNFeSupl><qrCode>https://www.nfce.fazenda.sp.gov.br/qrcode?p={CHAVE}|3|1</qrCode><urlChave>https://www.nfce.fazenda.sp.gov.br/consulta</urlChave></infNFeSupl></NFe>
<protNFe><infProt><cStat>100</cStat><chNFe>{CHAVE}</chNFe><nProt>135266165936952</nProt><dhRecbto>2026-09-09T12:00:00-03:00</dhRecbto></infProt></protNFe></nfeProc>""".encode()


def test_pdf_nfce_usa_xml_autorizado_e_nao_endpoint_nfe_inexistente(monkeypatch):
    baixar = Mock(return_value=XML)
    monkeypatch.setattr(documentos, "baixar_link_documento", baixar)
    pdf = documentos.obter_pdf_documento(
        {"situacao": 5, "chaveAcesso": CHAVE, "xml": "https://www.bling.com.br/xml"}, 65
    )
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 2500
    baixar.assert_called_once_with("https://www.bling.com.br/xml")


@pytest.mark.parametrize(
    "url",
    [
        "http://www.bling.com.br/doc",
        "https://bling.com.br.evil.test/doc",
        "https://127.0.0.1/doc",
        "https://www.bling.com.br:8443/doc",
        "https://user@www.bling.com.br/doc",
    ],
)
def test_rejeita_link_nao_oficial(url):
    with pytest.raises(ValueError):
        documentos.validar_link_documento(url)


def test_xml_de_outra_nota_e_rejeitado():
    with pytest.raises(ValueError, match="não corresponde"):
        validar_xml_nota(XML, "0" * 44, 65)


def test_pdf_sem_autorizacao_ou_qrcode_e_bloqueado():
    with pytest.raises(ValueError, match="protocolo"):
        gerar_danfe_nfce(XML.replace(b"<cStat>100", b"<cStat>204"), CHAVE)
    with pytest.raises(ValueError, match="QR Code"):
        gerar_danfe_nfce(XML.replace(b"qrCode", b"removido"), CHAVE)


def test_documento_exige_nota_pertencente_ao_tenant_antes_de_chamar_bling(monkeypatch):
    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = None
    bling = Mock()
    monkeypatch.setattr(documentos, "BlingAPI", bling)
    with pytest.raises(HTTPException) as erro:
        documentos.obter_nota_documento(db, "tenant-a", 123)
    assert erro.value.status_code == 404
    assert bling.call_count == 0


def test_nfe_55_baixa_pdf_do_link_documentado(monkeypatch):
    monkeypatch.setattr(documentos, "baixar_link_documento", lambda _: b"%PDF-teste")
    assert (
        documentos.obter_pdf_documento({"linkPDF": "https://www.bling.com.br/pdf"}, 55)
        == b"%PDF-teste"
    )
