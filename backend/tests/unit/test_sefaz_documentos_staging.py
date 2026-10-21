"""A distribuicao so pode avancar depois de salvar todos os documentos brutos."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.notas_entrada import sefaz_importer as importer
from app.produtos_compras_models import SefazDocumentoDistribuido
from app.tenancy.context import tenant_context


TENANT = UUID("11111111-1111-4111-8111-111111111111")
OUTRO_TENANT = UUID("22222222-2222-4222-8222-222222222222")
CHAVE = "35261012345678000199550010000001231000001234"


@pytest.fixture
def db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    SefazDocumentoDistribuido.__table__.create(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def _resumo(nsu="1"):
    return {
        "nsu": nsu,
        "schema": "resNFe_v1.01.xsd",
        "xml": (
            '<resNFe xmlns="http://www.portalfiscal.inf.br/nfe">'
            f"<chNFe>{CHAVE}</chNFe><CNPJ>12345678000199</CNPJ>"
            "<xNome>Fornecedor Teste</xNome>"
            "<dhEmi>2026-10-14T10:00:00-03:00</dhEmi><vNF>123.45</vNF>"
            "</resNFe>"
        ),
    }


def _completo(nsu="2", destinatario_cnpj="11111111000111"):
    return {
        "nsu": nsu,
        "schema": "procNFe_v4.00.xsd",
        "xml": (
            '<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe"><NFe>'
            f'<infNFe Id="NFe{CHAVE}"><ide><nNF>123</nNF>'
            "<dhEmi>2026-10-14T10:00:00-03:00</dhEmi></ide>"
            "<emit><CNPJ>12345678000199</CNPJ><xNome>Fornecedor Teste</xNome></emit>"
            f"<dest><CNPJ>{destinatario_cnpj}</CNPJ></dest>"
            "<total><ICMSTot><vNF>123.45</vNF></ICMSTot></total>"
            "</infNFe></NFe></nfeProc>"
        ),
    }


def _listar(db):
    with tenant_context(TENANT):
        return (
            db.query(SefazDocumentoDistribuido)
            .order_by(SefazDocumentoDistribuido.nsu)
            .all()
        )


def test_resumo_e_evento_sao_preservados_sem_criar_nota(db):
    evento = {
        "nsu": "3",
        "schema": "procEventoNFe_v1.00.xsd",
        "xml": "<procEventoNFe><evento><infEvento>cancelamento</infEvento></evento></procEventoNFe>",
    }
    resultado = importer.importar_documentos_distribuicao(
        db, str(TENANT), [_resumo(), evento]
    )

    docs = _listar(db)
    assert resultado["staging_salvo"] is True
    assert resultado["documentos_salvos"] == 2
    assert [doc.status for doc in docs] == ["aguardando_xml", "evento_recebido"]
    assert docs[0].chave_acesso == CHAVE
    assert docs[0].emitente_nome == "Fornecedor Teste"
    assert str(docs[0].valor_total) == "123.45"
    assert docs[0].nota_entrada_id is None
    assert docs[1].raw_xml == evento["xml"]


def test_lote_invalido_nao_confirma_parcialmente(db):
    with pytest.raises(ValueError, match="staging"):
        importer.importar_documentos_distribuicao(
            db, str(TENANT), [_resumo(), {"nsu": "4", "schema": "resNFe", "xml": ""}]
        )
    assert _listar(db) == []


def test_xml_completo_falha_local_mas_fica_salvo_e_pode_reprocessar(db, monkeypatch):
    vistos = []

    def falhar_apos_staging(_docs, _tenant, _db):
        vistos.append([doc.nsu for doc in _listar(_db)])
        return {"importadas": 0, "duplicadas": 0, "erros": 1, "saidas_descartadas": 0}

    monkeypatch.setattr(importer, "_importar_docs_sefaz_scoped", falhar_apos_staging)
    resultado = importer.importar_documentos_distribuicao(
        db, str(TENANT), [_resumo(), _completo()]
    )

    assert resultado["staging_salvo"] is True
    assert resultado["erros"] == 1
    assert vistos == [["000000000000001", "000000000000002"]]
    assert _listar(db)[1].status == "erro_processamento"

    monkeypatch.setattr(
        importer,
        "_importar_docs_sefaz_scoped",
        lambda *_args: {
            "importadas": 0,
            "duplicadas": 0,
            "erros": 0,
            "saidas_descartadas": 1,
        },
    )
    repeticao = importer.reprocessar_documentos_sefaz_pendentes(db, str(TENANT))
    assert repeticao["saidas_descartadas"] == 1
    assert _listar(db)[1].status == "saida_descartada"


def test_mesmo_nsu_e_idempotente_e_conflito_nao_sobrescreve_xml(db):
    doc = _resumo()
    importer.importar_documentos_distribuicao(db, str(TENANT), [doc])
    importer.importar_documentos_distribuicao(db, str(TENANT), [doc])
    assert len(_listar(db)) == 1

    alterado = {**doc, "xml": doc["xml"].replace("123.45", "999.99")}
    with pytest.raises(ValueError, match="conteúdo diferente"):
        importer.importar_documentos_distribuicao(db, str(TENANT), [alterado])
    assert _listar(db)[0].raw_xml == doc["xml"]


def test_mesmo_nsu_pode_pertencer_a_outro_tenant(db):
    importer.importar_documentos_distribuicao(db, str(TENANT), [_resumo()])
    importer.importar_documentos_distribuicao(db, str(OUTRO_TENANT), [_resumo()])

    with tenant_context(TENANT):
        assert db.query(SefazDocumentoDistribuido).count() == 1
    with tenant_context(OUTRO_TENANT):
        assert db.query(SefazDocumentoDistribuido).count() == 1


def test_retry_processa_somente_documentos_do_tenant_solicitado(db, monkeypatch):
    with tenant_context(TENANT):
        importer._staging_documentos([_completo("7")], TENANT, db)
    with tenant_context(OUTRO_TENANT):
        importer._staging_documentos([_completo("8")], OUTRO_TENANT, db)

    processados = []

    def registrar(_db, _tenant_id, documento):
        processados.append((documento.tenant_id, documento.nsu))
        return {"importadas": 0, "duplicadas": 0, "erros": 0, "saidas_descartadas": 0}

    monkeypatch.setattr(importer, "_processar_documento_staged", registrar)
    importer.reprocessar_documentos_sefaz_pendentes(db, str(TENANT))

    assert processados == [(TENANT, "000000000000007")]


def test_retry_prioriza_xml_novo_e_alterna_erros_antigos(db, monkeypatch):
    with tenant_context(TENANT):
        documentos = importer._staging_documentos(
            [_completo("1"), _completo("2"), _completo("3")], TENANT, db
        )
        referencia = datetime(2026, 10, 14, tzinfo=timezone.utc)
        for indice, documento in enumerate(documentos[:2]):
            documento.status = "erro_processamento"
            documento.processado_em = referencia + timedelta(minutes=indice)
        db.commit()

    processados = []

    def registrar(_db, _tenant_id, documento):
        processados.append(documento.nsu)
        documento.status = "erro_processamento"
        documento.processado_em = datetime.now(timezone.utc)
        _db.commit()
        return {"importadas": 0, "duplicadas": 0, "erros": 1}

    monkeypatch.setattr(importer, "_processar_documento_staged", registrar)
    for _ in range(3):
        importer.reprocessar_documentos_sefaz_pendentes(db, str(TENANT), limite=1)

    assert processados == [
        "000000000000003",
        "000000000000001",
        "000000000000002",
    ]


def test_xml_de_outro_destinatario_fica_no_staging_sem_nota(db, monkeypatch):
    monkeypatch.setattr(
        importer,
        "_importar_docs_sefaz_scoped",
        lambda *_args: {
            "importadas": 0,
            "duplicadas": 0,
            "erros": 0,
            "saidas_descartadas": 0,
            "nao_destinadas": 1,
        },
    )
    resultado = importer.importar_documentos_distribuicao(
        db, str(TENANT), [_completo("9", "22222222000122")]
    )

    assert resultado["nao_destinadas"] == 1
    assert _listar(db)[0].status == "nao_destinada"
    assert _listar(db)[0].nota_entrada_id is None
    assert "22222222000122" in _listar(db)[0].raw_xml


def test_importador_so_aceita_xml_destinado_ao_cnpj_configurado(monkeypatch):
    class _Query:
        def filter(self, *_args):
            return self

        def order_by(self, *_args):
            return self

        def first(self):
            return object()

    class _Db:
        def query(self, _model):
            return _Query()

    monkeypatch.setattr(
        importer.SefazTenantConfigService,
        "load_config",
        lambda _tenant: {"cnpj": "11111111000111"},
    )
    monkeypatch.setattr(
        importer,
        "parse_nfe_xml",
        lambda _xml: {"fornecedor_cnpj": "12345678000199"},
    )

    terceiro = importer._importar_docs_sefaz_scoped(
        [_completo("10", "22222222000122")], str(TENANT), _Db()
    )
    assert terceiro["nao_destinadas"] == 1
    assert terceiro["importadas"] == 0

    monkeypatch.setattr(
        importer.SefazTenantConfigService,
        "load_config",
        lambda _tenant: {"cnpj": ""},
    )
    sem_cnpj = importer._importar_docs_sefaz_scoped(
        [_completo("11")], str(TENANT), _Db()
    )
    assert sem_cnpj["erros"] == 1
    assert sem_cnpj["nao_destinadas"] == 0
