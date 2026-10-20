import json
from datetime import date
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4
from zipfile import ZipFile

import pytest

from app.services import xml_contabilidade_pacotes as pacotes
from app.services.xml_contabilidade_common import XmlContabilidadeError

CHAVE = "35261033590794000140650030000000441241595909"
OUTRA = "35260933590794000140650030000000451241595909"
INICIO = date(2026, 10, 1)
FIM = date(2026, 10, 31)


def nota(chave=CHAVE, eventos=()):
    return {
        "chave": chave,
        "emitente_cnpj": "33590794000140",
        "emitente_nome": "Empresa fictícia",
        "status": "autorizada",
        "eventos": list(eventos),
    }


def evento(tipo="110111", seq=1):
    return {"tipo": tipo, "sequencia": seq, "protocolo": f"135{tipo}{seq:02d}"}


def arquivo_evento(tipo="110111", seq=1, chave=CHAVE):
    return f"ID{tipo}{chave}{seq:02d}.xml", f"original-assinado-{tipo}-{seq}".encode()


def test_zip_por_tipo_preserva_todas_sequencias_e_bytes_sem_misturar():
    arquivos = [
        (f"{CHAVE}-nfe.xml", b"XML original assinado da nota"),
        arquivo_evento("110111"),
        arquivo_evento("110112"),
        arquivo_evento("110110", 1),
        arquivo_evento("110110", 2),
        arquivo_evento("210210"),
        arquivo_evento("210200"),
    ]
    eventos = [
        evento(t, s)
        for t, s in [
            ("110111", 1),
            ("110112", 1),
            ("110110", 1),
            ("110110", 2),
            ("210210", 1),
            ("210200", 1),
        ]
    ]
    anexos, nome, quantidade = pacotes.criar_anexos_por_tipo(
        arquivos, [nota(eventos=eventos)], INICIO, FIM
    )
    assert nome == "xml-saida-20261001-20261031.zip" and quantidade == 1
    grupos = {a["filename"].removesuffix("-20261001-20261031.zip"): a for a in anexos}
    assert set(grupos) == {
        "notas",
        "cancelamentos",
        "cartas-correcao",
        "eventos-210210",
        "eventos-210200",
    }
    esperado = {
        "notas": {arquivos[0][0]},
        "cancelamentos": {arquivos[1][0], arquivos[2][0]},
        "cartas-correcao": {arquivos[3][0], arquivos[4][0]},
        "eventos-210210": {arquivos[5][0]},
        "eventos-210200": {arquivos[6][0]},
    }
    por_nome = dict(arquivos)
    for grupo, anexo in grupos.items():
        assert anexo["mime_subtype"] == "zip"
        with ZipFile(BytesIO(anexo["content"])) as zipped:
            assert set(zipped.namelist()) == esperado[grupo] | {"manifesto.json"}
            for arquivo in esperado[grupo]:
                assert zipped.read(arquivo) == por_nome[arquivo]
            manifesto = json.loads(zipped.read("manifesto.json"))
            assert manifesto["categoria"] == grupo
            assert manifesto["quantidade_notas"] == 1
            if grupo == "cartas-correcao":
                assert [e["sequencia"] for e in manifesto["notas"][0]["eventos"]] == [
                    1,
                    2,
                ]
    download = pacotes.agrupar_download(anexos, nome)
    with ZipFile(BytesIO(download)) as zipped:
        assert set(zipped.namelist()) == {a["filename"] for a in anexos}
        for anexo in anexos:
            assert zipped.read(anexo["filename"]) == anexo["content"]


def test_somente_evento_de_nota_antiga_gera_lote_sem_zip_notas_vazio():
    anexo = arquivo_evento(chave=OUTRA)
    anexos, _, quantidade = pacotes.criar_anexos_por_tipo(
        [anexo], [nota(OUTRA, [evento()])], INICIO, FIM
    )
    assert quantidade == 1 and len(anexos) == 1
    assert anexos[0]["filename"].startswith("cancelamentos-")
    with ZipFile(BytesIO(anexos[0]["content"])) as zipped:
        assert zipped.read(anexo[0]) == anexo[1]


def test_merge_nota_periodo_e_evento_ja_coletado_nao_duplica():
    arquivo = arquivo_evento()
    antes = nota(eventos=[evento()])
    depois = nota(eventos=[evento(), evento("110110")])
    depois["status"] = "cancelada"
    arquivos, notas = pacotes.mesclar_coletas(
        [arquivo], [antes], [arquivo, arquivo_evento("110110")], [depois]
    )
    assert len(arquivos) == 2 and len(notas) == 1
    assert notas[0]["status"] == "cancelada" and notas[0]["eventos_incluidos"] == 2
    assert antes["status"] == "autorizada" and len(antes["eventos"]) == 1


def test_evento_conflitante_ou_nome_inseguro_bloqueia_lote():
    arquivo = arquivo_evento()
    with pytest.raises(XmlContabilidadeError, match="conflitantes"):
        pacotes.mesclar_coletas([arquivo], [nota()], [(arquivo[0], b"outro")], [])
    with pytest.raises(XmlContabilidadeError, match="identificação"):
        pacotes.criar_anexos_por_tipo(
            [("../fora.xml", b"bytes")], [nota()], INICIO, FIM
        )


def test_limite_aplicado_soma_de_todos_zips(monkeypatch):
    monkeypatch.setattr(pacotes, "MAX_ZIP_BYTES", 100)
    with pytest.raises(XmlContabilidadeError, match="ZIPs excedem"):
        pacotes.criar_anexos_por_tipo(
            [(f"{CHAVE}-nfe.xml", b"original"), arquivo_evento()], [nota()], INICIO, FIM
        )


def test_lote_sem_notas_ou_eventos_nao_envia_anexos_vazios():
    with pytest.raises(XmlContabilidadeError) as erro:
        pacotes.criar_anexos_por_tipo([], [], INICIO, FIM)
    assert erro.value.status_code == 404


@pytest.mark.parametrize("origem", ["mensal", "manual"])
def test_envio_anexa_zips_separados_na_mesma_mensagem(origem, monkeypatch):
    from app.services import xml_contabilidade_documentos as documentos
    from app.services import xml_contabilidade_service as service

    arquivos = [(f"{CHAVE}-nfe.xml", b"nota assinada"), arquivo_evento()]
    monkeypatch.setattr(
        documentos,
        "_preparar_periodo",
        Mock(return_value=(arquivos, [nota(eventos=[evento()])])),
    )
    monkeypatch.setattr(service, "_cnpj_empresa", lambda *_: "33590794000140")
    monkeypatch.setattr(service.email_service, "is_email_configured", lambda: True)
    smtp = Mock(return_value=True)
    monkeypatch.setattr(service.email_service, "send_email", smtp)
    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(
        razao_social="Empresa fictícia", name="Empresa"
    )
    envio = SimpleNamespace(
        origem=origem,
        data_inicio=INICIO,
        data_fim=FIM,
        email_destino="contador@example.com",
    )
    service._processar_envio(db, uuid4(), envio)
    smtp.assert_called_once()
    anexos = smtp.call_args.kwargs["attachments"]
    assert {a["filename"] for a in anexos} == {
        "notas-20261001-20261031.zip",
        "cancelamentos-20261001-20261031.zip",
    }
    assert smtp.call_args.kwargs["simulate_if_unconfigured"] is False
    assert envio.status == "enviado" and envio.quantidade_xml == 1


def test_falha_na_coleta_bloqueia_todos_anexos_antes_smtp(monkeypatch):
    from app.services import xml_contabilidade_documentos as documentos
    from app.services import xml_contabilidade_service as service

    monkeypatch.setattr(
        documentos,
        "_preparar_periodo",
        Mock(side_effect=XmlContabilidadeError("evento ausente", 409)),
    )
    monkeypatch.setattr(service, "_cnpj_empresa", lambda *_: "33590794000140")
    monkeypatch.setattr(service.email_service, "is_email_configured", lambda: True)
    smtp = Mock()
    monkeypatch.setattr(service.email_service, "send_email", smtp)
    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = None
    envio = SimpleNamespace(origem="mensal", data_inicio=INICIO, data_fim=FIM)
    with pytest.raises(XmlContabilidadeError, match="evento ausente"):
        service._processar_envio(db, uuid4(), envio)
    smtp.assert_not_called()
