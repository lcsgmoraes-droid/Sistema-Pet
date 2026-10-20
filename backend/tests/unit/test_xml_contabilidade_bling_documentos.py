"""Documentos oficiais GZIP/base64 do Bling sem transformar XML assinado."""

import base64
from copy import deepcopy
from datetime import date, datetime
import gzip
from io import BytesIO
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.services import xml_contabilidade_bling_documentos as bling_documentos
from app.services import xml_contabilidade_documentos as documentos
from app.services.xml_contabilidade_common import XmlContabilidadeError

CNPJ = "33590794000140"
CHAVE = f"352610{CNPJ}550030000000441241595909"
PROTOCOLO = "135260000000001"
SEGREDO = "credencial-privada-nao-exibir"


def nota_xml(**alteracoes):
    campos = {
        "chave": CHAVE,
        "cnpj": CNPJ,
        "modelo": "55",
        "ambiente": "1",
        "saida": "1",
        "status": "100",
        "data": "2026-01-15T12:00:00-03:00",
    }
    campos.update(alteracoes)
    return (
        (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">'
            '<NFe><infNFe Id="NFe{chave}"><ide><mod>{modelo}</mod>'
            "<dhEmi>{data}</dhEmi><tpAmb>{ambiente}</tpAmb><tpNF>{saida}</tpNF>"
            "</ide><emit><CNPJ>{cnpj}</CNPJ></emit></infNFe>"
            '<Signature xmlns="http://www.w3.org/2000/09/xmldsig#">'
            "<SignatureValue>nota-original==</SignatureValue></Signature></NFe>"
            "<protNFe><infProt><chNFe>{chave}</chNFe><cStat>{status}</cStat>"
            "<nProt>135260000000000</nProt></infProt></protNFe></nfeProc>"
        )
        .format(**campos)
        .encode()
    )


def evento_xml(**alteracoes):
    campos = {
        "tipo": "110111",
        "seq": 1,
        "chave": CHAVE,
        "cnpj": CNPJ,
        "ambiente": "1",
        "status": "135",
        "protocolo": PROTOCOLO,
        "data": "2026-01-16T13:00:00-03:00",
    }
    campos.update(alteracoes)
    return (
        (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<procEventoNFe xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.00">'
            '<evento><infEvento Id="ID{tipo}{chave}{seq:02d}">'
            "<tpAmb>{ambiente}</tpAmb><CNPJ>{cnpj}</CNPJ><chNFe>{chave}</chNFe>"
            "<dhEvento>{data}</dhEvento><tpEvento>{tipo}</tpEvento>"
            "<nSeqEvento>{seq}</nSeqEvento></infEvento>"
            '<Signature xmlns="http://www.w3.org/2000/09/xmldsig#">'
            "<SignatureValue>evento-original==</SignatureValue></Signature></evento>"
            "<retEvento><infEvento><tpAmb>{ambiente}</tpAmb><chNFe>{chave}</chNFe>"
            "<tpEvento>{tipo}</tpEvento><nSeqEvento>{seq}</nSeqEvento>"
            "<cStat>{status}</cStat><nProt>{protocolo}</nProt>"
            "<dhRegEvento>{data}</dhRegEvento></infEvento></retEvento></procEventoNFe>"
        )
        .format(**campos)
        .encode()
    )


def entrada(xml, nome="documento.xml"):
    return {
        "nome": nome,
        "conteudo": base64.b64encode(gzip.compress(xml, mtime=0)).decode("ascii"),
    }


def payload(*xmls):
    return {"data": [entrada(xml) for xml in xmls]}


def decodificar(resposta):
    return bling_documentos.decodificar_documentos_nfe(resposta, CHAVE, CNPJ)


def test_nota_e_eventos_classificados_pelo_conteudo_preservam_bytes_assinados():
    nota = b"\xef\xbb\xbf" + nota_xml()
    cce1 = evento_xml(tipo="110110", seq=1)
    cce2 = evento_xml(tipo="110110", seq=2)
    cancelamento = evento_xml()
    outro = evento_xml(tipo="210210")
    xmls = [cce2, cancelamento, nota, outro, cce1]
    resposta = {
        "data": [entrada(xml, nome="../../" + SEGREDO + ".pdf") for xml in xmls]
    }

    nota_retornada, eventos = decodificar(resposta)

    assert nota_retornada == nota
    assert len(eventos) == 4
    assert set(eventos) == {cce1, cce2, cancelamento, outro}


def test_nota_sem_eventos_e_valida():
    nota = nota_xml()
    assert decodificar(payload(nota)) == (nota, [])


def test_duplicatas_identicas_sao_deduplicadas():
    nota, evento = nota_xml(), evento_xml()
    nota_retornada, eventos = decodificar(payload(evento, nota, evento, nota))
    assert nota_retornada == nota
    assert eventos == [evento]


@pytest.mark.parametrize("tipo", ["nota", "evento"])
def test_mesma_identidade_com_bytes_diferentes_bloqueia_arquivo_conflitante(tipo):
    nota, evento = nota_xml(), evento_xml()
    original = nota if tipo == "nota" else evento
    diferente = original.replace(b"original==", b"divergente==")
    with pytest.raises(XmlContabilidadeError):
        decodificar(payload(nota, evento, diferente))


@pytest.mark.parametrize(
    "resposta",
    [None, [], {}, {"data": None}, {"data": {}}, {"data": "xml"}, {"data": []}],
)
def test_envelope_sem_lista_oficial_nao_produz_documentos(resposta):
    with pytest.raises(XmlContabilidadeError):
        decodificar(resposta)


@pytest.mark.parametrize(
    "item",
    [None, [], "xml", {}, {"conteudo": None}, {"conteudo": 123}],
)
def test_entrada_sem_conteudo_base64_valido_bloqueia_todo_lote(item):
    resposta = payload(nota_xml())
    resposta["data"].append(item)
    with pytest.raises(XmlContabilidadeError):
        decodificar(resposta)


@pytest.mark.parametrize(
    "conteudo",
    [
        "!!!" + SEGREDO,
        "á",
        "",
        base64.b64encode(b"nao-e-gzip").decode(),
        base64.b64encode(gzip.compress(nota_xml())[:-5]).decode(),
    ],
)
def test_base64_gzip_invalido_ou_truncado_nao_expoe_conteudo(conteudo):
    with pytest.raises(XmlContabilidadeError) as exc:
        decodificar({"data": [{"nome": SEGREDO, "conteudo": conteudo}]})
    assert SEGREDO not in str(exc.value)
    if conteudo:
        assert conteudo not in str(exc.value)


@pytest.mark.parametrize(
    "xml",
    [
        b"<xml-invalido",
        b"<documento>tipo-desconhecido</documento>",
        b"<nfeProc/>",
        b"<procEventoNFe/>",
        nota_xml().replace(b"nfeProc", b"enviNFe"),
        nota_xml().replace(b"nfeProc", b"NFe"),
        (
            b'<!DOCTYPE nfeProc [<!ENTITY segredo SYSTEM "file:///segredo">]>'
            + nota_xml().split(b"\n", 1)[1].replace(b"nota-original==", b"&segredo;")
        ),
    ],
)
def test_xml_invalido_namespace_tipo_ou_entidades_bloqueiam(xml):
    with pytest.raises(XmlContabilidadeError):
        decodificar(payload(xml))


def test_evento_avulso_nao_substitui_nota_autorizada():
    with pytest.raises(XmlContabilidadeError):
        decodificar(payload(evento_xml()))


@pytest.mark.parametrize(
    "alteracoes",
    [
        {"chave": "9" * 44},
        {"cnpj": "11111111000111"},
        {"modelo": "65"},
        {"ambiente": "2"},
        {"saida": "0"},
        {"status": "101"},
        {"data": "ontem"},
    ],
)
def test_nota_divergente_homologacao_entrada_ou_sem_autorizacao_bloqueia(alteracoes):
    with pytest.raises(XmlContabilidadeError):
        decodificar(payload(nota_xml(**alteracoes)))


@pytest.mark.parametrize(
    "alteracoes",
    [
        {"chave": "9" * 44},
        {"cnpj": "11111111000111"},
        {"ambiente": "2"},
        {"status": "580"},
        {"status": "136"},
        {"protocolo": ""},
        {"data": "ontem"},
        {"seq": 0},
        {"tipo": "invalido"},
    ],
)
def test_evento_divergente_ou_sem_protocolo_valido_bloqueia(alteracoes):
    with pytest.raises(XmlContabilidadeError):
        decodificar(payload(nota_xml(), evento_xml(**alteracoes)))


def test_todas_as_sequencias_de_cce_sao_obrigatorias():
    with pytest.raises(XmlContabilidadeError):
        decodificar(payload(nota_xml(), evento_xml(tipo="110110", seq=3)))


def test_limite_de_entradas_aplica_antes_da_deduplicacao(monkeypatch):
    monkeypatch.setattr(bling_documentos, "MAX_ARQUIVOS_POR_NOTA", 2)
    nota = nota_xml()
    with pytest.raises(XmlContabilidadeError):
        decodificar(payload(nota, nota, nota))


def test_conteudo_base64_excessivo_bloqueia_sem_decodificar(monkeypatch):
    monkeypatch.setattr(bling_documentos, "MAX_XML_BYTES", 16)
    decodificador = Mock(side_effect=AssertionError("Não alocar base64 excessivo"))
    monkeypatch.setattr(bling_documentos.base64, "b64decode", decodificador)
    with pytest.raises(XmlContabilidadeError):
        decodificar({"data": [{"conteudo": "A" * 100, "nome": SEGREDO}]})
    decodificador.assert_not_called()


def test_gzip_expansivel_nao_ultrapassa_limite_por_xml(monkeypatch):
    nota_grande = nota_xml().replace(
        b"</nfeProc>", b"<!--" + b"x" * 100_000 + b"--></nfeProc>"
    )
    resposta = payload(nota_grande)
    assert len(resposta["data"][0]["conteudo"]) < 2048
    monkeypatch.setattr(bling_documentos, "MAX_XML_BYTES", 2048)
    with pytest.raises(XmlContabilidadeError):
        decodificar(resposta)


def test_tamanho_total_expandido_considera_nota_e_todos_eventos(monkeypatch):
    nota, evento = nota_xml(), evento_xml()
    monkeypatch.setattr(
        bling_documentos, "MAX_TOTAL_BYTES", len(nota) + len(evento) - 1
    )
    with pytest.raises(XmlContabilidadeError):
        decodificar(payload(nota, evento))


def test_tamanho_total_comprimido_tambem_limita_cabecalhos_gzip(monkeypatch):
    nota, evento = nota_xml(), evento_xml()
    limite_total = len(nota) + len(evento) + 1
    comprimidos = []
    for xml in (nota, evento):
        buffer = BytesIO()
        with gzip.GzipFile(
            filename="x" * (limite_total // 2),
            mode="wb",
            fileobj=buffer,
            mtime=0,
        ) as arquivo:
            arquivo.write(xml)
        comprimidos.append(buffer.getvalue())
    assert all(len(conteudo) < limite_total for conteudo in comprimidos)
    assert sum(map(len, comprimidos)) > limite_total
    monkeypatch.setattr(bling_documentos, "MAX_TOTAL_BYTES", limite_total)
    resposta = {
        "data": [
            {"conteudo": base64.b64encode(conteudo).decode("ascii")}
            for conteudo in comprimidos
        ]
    }
    with pytest.raises(XmlContabilidadeError):
        decodificar(resposta)


def test_consulta_endpoint_oficial_com_tenant_e_formato_xml(monkeypatch):
    tenant = uuid4()
    nota, evento = nota_xml(), evento_xml()
    api = Mock()
    api._request.return_value = payload(evento, nota)
    construir = Mock(return_value=api)
    monkeypatch.setattr(bling_documentos, "BlingAPI", construir)

    assert bling_documentos.obter_documentos_nfe(tenant, CHAVE, CNPJ) == (
        nota,
        [evento],
    )
    construir.assert_called_once_with(tenant_id=tenant)
    api._request.assert_called_once_with(
        "GET", f"/nfe/documento/{CHAVE}", data={"formato": "xml"}
    )


@pytest.mark.parametrize(
    "chave,cnpj",
    [
        (None, CNPJ),
        ("/../../credencial", CNPJ),
        ("9" * 44, CNPJ),
        (CHAVE[:20] + "65" + CHAVE[22:], CNPJ),
        (CHAVE, None),
        (CHAVE, "11111111000111"),
        (CHAVE, "33.590.794/0001-40"),
    ],
)
def test_referencia_invalida_e_bloqueada_antes_da_requisicao(monkeypatch, chave, cnpj):
    construir = Mock()
    monkeypatch.setattr(bling_documentos, "BlingAPI", construir)
    with pytest.raises(XmlContabilidadeError):
        bling_documentos.obter_documentos_nfe(uuid4(), chave, cnpj)
    construir.assert_not_called()


@pytest.mark.parametrize("na_construcao", [False, True])
def test_falha_remota_bloqueia_e_oculta_resposta_privada(monkeypatch, na_construcao):
    erro = RuntimeError(SEGREDO)
    api = Mock()
    api._request.side_effect = erro
    construir = Mock(side_effect=erro) if na_construcao else Mock(return_value=api)
    monkeypatch.setattr(bling_documentos, "BlingAPI", construir)
    with pytest.raises(XmlContabilidadeError) as exc:
        bling_documentos.obter_documentos_nfe(uuid4(), CHAVE, CNPJ)
    assert SEGREDO not in str(exc.value)


@pytest.mark.parametrize("status_cache", ["autorizada", "cancelada"])
def test_coletor_real_descobre_todos_eventos_independente_do_cache(
    monkeypatch, status_cache
):
    from app.nfe import documentos as documentos_api

    tenant, db = uuid4(), Mock()
    nota = nota_xml()
    eventos = [evento_xml(), evento_xml(tipo="110110", seq=1)]
    api = Mock()
    api._request.return_value = payload(eventos[0], nota, eventos[1])
    monkeypatch.setattr(bling_documentos, "BlingAPI", lambda **_: api)
    monkeypatch.setattr(documentos, "_cnpj_empresa", lambda *_: CNPJ)
    monkeypatch.setattr(documentos, "_obter_eventos", lambda *_: {})
    monkeypatch.setattr(
        documentos_api,
        "obter_nota_documento",
        lambda *_: ({"chaveAcesso": CHAVE}, 55, None),
    )
    legado = Mock(side_effect=AssertionError("NF55 deve consultar documentos oficiais"))
    monkeypatch.setattr(documentos_api, "obter_xml_documento", legado)
    doc = documentos.Documento(
        "bling", "123", CHAVE, 55, status_cache, datetime(2026, 1, 15, 12)
    )

    arquivos, notas = documentos._coletar_arquivos(
        db, tenant, [doc], date(2026, 1, 1), date(2026, 1, 31)
    )

    assert dict(arquivos)[f"{CHAVE}-nfe.xml"] == nota
    assert {conteudo for _, conteudo in arquivos} == {nota, *eventos}
    assert len(notas) == 1
    assert notas[0]["status"] == "cancelada"
    assert notas[0]["eventos_incluidos"] == 2
    assert {evento["tipo"] for evento in notas[0]["eventos"]} == {
        "110111",
        "110110",
    }
    legado.assert_not_called()
    api._request.assert_called_once_with(
        "GET", f"/nfe/documento/{CHAVE}", data={"formato": "xml"}
    )


def test_modelo_65_preserva_coleta_existente_sem_endpoint_nf55(monkeypatch):
    from app.nfe import documentos as documentos_api

    chave = CHAVE[:20] + "65" + CHAVE[22:]
    nota = nota_xml(chave=chave, modelo="65")
    detalhe = {"chaveAcesso": chave}
    monkeypatch.setattr(
        documentos_api, "obter_nota_documento", lambda *_: (detalhe, 65, None)
    )
    legado = Mock(return_value=nota)
    monkeypatch.setattr(documentos_api, "obter_xml_documento", legado)
    novo = Mock(side_effect=AssertionError("NFC-e preserva o endpoint existente"))
    monkeypatch.setattr(bling_documentos, "obter_documentos_nfe", novo)
    doc = documentos.Documento(
        "bling", "123", chave, 65, "autorizada", datetime(2026, 1, 15, 12)
    )

    assert documentos._obter_xml(Mock(), uuid4(), doc) == (nota, detalhe)
    legado.assert_called_once_with(detalhe, 65)
    novo.assert_not_called()


@pytest.mark.parametrize("formato_anterior", ["escalar", "lista", "ausente"])
def test_nf55_acrescenta_eventos_sem_descartar_ou_mutar_detalhe_original(
    monkeypatch, formato_anterior
):
    from app.nfe import documentos as documentos_api

    nota, canonico = nota_xml(), evento_xml()
    anterior = evento_xml(tipo="210210")
    detalhe = {
        "chaveAcesso": CHAVE,
        "xmlCancelamento": "comprovante-anterior.xml",
        "xmlCartaCorrecao": [evento_xml(tipo="110110")],
    }
    if formato_anterior == "escalar":
        detalhe["xmlEvento"] = anterior
    elif formato_anterior == "lista":
        detalhe["xmlEvento"] = [None, anterior, b""]
    original = deepcopy(detalhe)
    api = Mock()
    api._request.return_value = payload(nota, canonico)
    monkeypatch.setattr(bling_documentos, "BlingAPI", lambda **_: api)
    monkeypatch.setattr(documentos, "_cnpj_empresa", lambda *_: CNPJ)
    monkeypatch.setattr(
        documentos_api, "obter_nota_documento", lambda *_: (detalhe, 55, None)
    )
    doc = documentos.Documento(
        "bling", "123", CHAVE, 55, "autorizada", datetime(2026, 1, 15, 12)
    )

    nota_retornada, resultado = documentos._obter_xml(Mock(), uuid4(), doc)

    assert nota_retornada == nota
    assert resultado["xmlEvento"] == (
        [canonico] if formato_anterior == "ausente" else [anterior, canonico]
    )
    assert resultado["xmlCancelamento"] == original["xmlCancelamento"]
    assert resultado["xmlCartaCorrecao"] == original["xmlCartaCorrecao"]
    assert detalhe == original


def test_coletor_cancelado_sem_comprovante_continua_bloqueando(monkeypatch):
    from app.nfe import documentos as documentos_api

    api = Mock()
    api._request.return_value = payload(nota_xml())
    monkeypatch.setattr(bling_documentos, "BlingAPI", lambda **_: api)
    monkeypatch.setattr(documentos, "_cnpj_empresa", lambda *_: CNPJ)
    monkeypatch.setattr(documentos, "_obter_eventos", lambda *_: {})
    monkeypatch.setattr(
        documentos_api,
        "obter_nota_documento",
        lambda *_: ({"chaveAcesso": CHAVE}, 55, None),
    )
    doc = documentos.Documento(
        "bling", "123", CHAVE, 55, "cancelada", datetime(2026, 1, 15, 12)
    )
    with pytest.raises(XmlContabilidadeError, match="cancelamento.*parcial"):
        documentos._coletar_arquivos(
            Mock(), uuid4(), [doc], date(2026, 1, 1), date(2026, 1, 31)
        )
