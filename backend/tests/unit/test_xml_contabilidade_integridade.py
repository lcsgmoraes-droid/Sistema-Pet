"""O cache contábil só entrega bytes comprovados pela assinatura original."""

from datetime import date, datetime
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4
from zipfile import ZipFile

import pytest

from app.intnfe.xml_integrity import ensure_signed_xml
from app.services import xml_contabilidade_documentos as documentos
from tests.helpers.signed_nfe import make_key, sign_nfe

CNPJ = "11222333000181"
KEY = make_key("3526101122233300018155001000000001100000001")
DAY = date(2026, 10, 26)


def source(key=KEY):
    return sign_nfe(
        f'<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe"><NFe>'  # NOSONAR: namespace XML.
        f'<infNFe Id="NFe{key}"><ide><dhEmi>2026-10-26T12:00:00-03:00</dhEmi>'
        "<tpAmb>1</tpAmb><tpNF>1</tpNF></ide><emit><CNPJ>"
        f"{CNPJ}</CNPJ><xNome>Empresa ficticia</xNome><enderEmit>"
        "<xBairro>Jardim Botanico</xBairro></enderEmit></emit></infNFe></NFe>"
        f"<protNFe><infProt><chNFe>{key}</chNFe><cStat>100</cStat>"
        "</infProt></protNFe></nfeProc>"
    )


def document(xml, key=KEY):
    return documentos.Documento(
        "intnfe",
        "1",
        key,
        55,
        "autorizada",
        datetime(2026, 10, 26, 12),
        venda=SimpleNamespace(
            nfe_xml=xml, nfe_tipo="nfe", nfe_correlation_id="fixture", nfe_ambiente=1
        ),
    )


@pytest.fixture
def context(monkeypatch):
    monkeypatch.setattr(documentos, "_cnpj_empresa", lambda *_: CNPJ)
    monkeypatch.setattr(documentos, "_obter_eventos", lambda *_: {})


def test_cache_valido_preserva_bytes_exatos_sem_consulta_externa(context, monkeypatch):
    from app.intnfe import client

    xml = b"\xef\xbb\xbf" + source()
    doc = document(xml)
    api = Mock(side_effect=AssertionError("O cache não precisa de rede."))
    monkeypatch.setattr(client, "IntNFeClient", api)
    returned, detail = documentos._obter_xml(Mock(), uuid4(), doc)
    assert returned == xml and detail == {}
    assert doc.venda.nfe_xml is xml
    api.assert_not_called()


def test_lote_usa_representacao_comprovada_sem_sobrescrever_cache(context):
    original = source()
    corrupted = original.replace(b"Jardim Botanico", "Jardim Botânico".encode())
    doc = document(corrupted.decode())
    arquivos, notas = documentos._coletar_arquivos(Mock(), uuid4(), [doc], DAY, DAY)
    assert len(arquivos) == len(notas) == 1
    repaired = arquivos[0][1]
    assert b"Jardim Botanico" in repaired
    assert ensure_signed_xml(repaired, expected_key=KEY, expected_cnpj=CNPJ) == repaired
    assert doc.venda.nfe_xml == corrupted.decode()
    zipped, _, _ = documentos._zip(arquivos, notas, DAY, DAY)
    with ZipFile(BytesIO(zipped)) as archive:
        assert archive.read(f"{KEY}-nfe.xml") == repaired


def test_xml_alterado_bloqueia_lote_inteiro_sem_vazar_conteudo(context):
    good = document(source())
    key2 = make_key(KEY[:25] + "000000002" + KEY[34:])
    bad_xml = source(key2).replace(b"Empresa ficticia", b"DADO-EXTERNO-NAO-EXIBIR")
    bad = document(bad_xml, key2)
    bad.documento_id = "2"
    with pytest.raises(
        documentos.XmlContabilidadeError, match="integridade.*parcial"
    ) as error:
        documentos._coletar_arquivos(Mock(), uuid4(), [good, bad], DAY, DAY)
    assert error.value.status_code == 409
    assert "DADO-EXTERNO" not in str(error.value)
    assert bad.venda.nfe_xml == bad_xml


def test_validacao_individual_tambem_rejeita_cache_com_digest_alterado():
    corrupted = source().replace(b"Empresa ficticia", b"Outro conteudo")
    with pytest.raises(documentos.XmlContabilidadeError, match="integridade"):
        documentos.validar_xml_saida(corrupted, KEY, 55)


def test_modelo_desconhecido_nao_remove_vinculo_com_o_modelo_da_nota():
    with pytest.raises(documentos.XmlContabilidadeError, match="integridade"):
        documentos.validar_xml_saida(source(), KEY, 57)


def test_cache_da_empresa_errada_nao_e_servido_nem_regravado(context, monkeypatch):
    doc = document(source())
    original = doc.venda.nfe_xml
    monkeypatch.setattr(documentos, "_cnpj_empresa", lambda *_: "33590794000140")
    with pytest.raises(documentos.XmlContabilidadeError, match="desta empresa"):
        documentos._obter_xml(Mock(), uuid4(), doc)
    assert doc.venda.nfe_xml is original


def test_download_de_outra_chave_nao_preenche_cache(context, monkeypatch):
    from app.intnfe import client, emission

    doc = document(None)
    doc.chave = make_key(KEY[:25] + "000000002" + KEY[34:])
    api = Mock()
    api.document_xml.return_value = source()
    monkeypatch.setattr(client, "IntNFeClient", lambda: api)
    monkeypatch.setattr(emission, "_connection", lambda *_a, **_kw: Mock())
    monkeypatch.setattr(emission, "_access_token", lambda *_: "fixture-token")
    with pytest.raises(documentos.XmlContabilidadeError, match="integridade"):
        documentos._obter_xml(Mock(), uuid4(), doc)
    assert doc.venda.nfe_xml is None
    api.close.assert_called_once()
