import os
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("DEBUG", "false")

from app import notas_entrada_routes  # noqa: E402
from app.notas_entrada import consulta_routes  # noqa: E402
from app.notas_entrada.documentos import validar_xml_nfe_entrada  # noqa: E402


CHAVE = "35260912345678000195550010000001231234567890"
XML_AUTORIZADO = f"""<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
  <NFe><infNFe Id="NFe{CHAVE}" versao="4.00"><ide><mod>55</mod></ide></infNFe></NFe>
  <protNFe><infProt><chNFe>{CHAVE}</chNFe><cStat>100</cStat></infProt></protNFe>
</nfeProc>"""


class _FakeQuery:
    def __init__(self, nota):
        self.nota = nota

    def filter(self, *_args):
        return self

    def first(self):
        return self.nota


class _FakeDB:
    def __init__(self, nota):
        self.nota = nota

    def query(self, *_args):
        return _FakeQuery(self.nota)


def _criar_nota(*, serie="1"):
    nota = SimpleNamespace(
        id=10,
        numero_nota="123",
        serie=serie,
        chave_acesso=CHAVE if serie != "PDF" else "PDF-entrada-sintetica",
        xml_content=XML_AUTORIZADO,
        tenant_id="tenant-a",
    )
    return nota, _FakeDB(nota)


def test_rotas_de_documentos_estao_publicadas():
    app = FastAPI()
    app.include_router(notas_entrada_routes.router)

    assert "/notas-entrada/{nota_id}/xml" in app.openapi()["paths"]
    assert "/notas-entrada/{nota_id}/danfe" in app.openapi()["paths"]


def test_validar_xml_nfe_entrada_exige_nota_autorizada():
    assert validar_xml_nfe_entrada(XML_AUTORIZADO, CHAVE) == XML_AUTORIZADO

    with pytest.raises(ValueError, match="protocolo de autorizacao"):
        validar_xml_nfe_entrada(
            XML_AUTORIZADO.replace("<cStat>100", "<cStat>204"), CHAVE
        )


def test_baixar_xml_retorna_original_com_nome_seguro():
    nota, db = _criar_nota()

    response = consulta_routes.baixar_xml_nota_entrada(
        nota.id,
        db=db,
        user_and_tenant=(object(), "tenant-a"),
    )

    assert response.body.decode("utf-8") == XML_AUTORIZADO
    assert response.media_type == "application/xml"
    assert (
        response.headers["content-disposition"]
        == 'attachment; filename="nfe_123_serie_1.xml"'
    )


def test_baixar_danfe_gera_pdf_do_xml_salvo(monkeypatch):
    nota, db = _criar_nota()
    monkeypatch.setattr(
        consulta_routes,
        "gerar_danfe_entrada",
        lambda xml_content, chave_acesso: b"%PDF-documento-teste",
    )

    response = consulta_routes.baixar_danfe_nota_entrada(
        nota.id,
        db=db,
        user_and_tenant=(object(), "tenant-a"),
    )

    assert response.body == b"%PDF-documento-teste"
    assert response.media_type == "application/pdf"
    assert (
        response.headers["content-disposition"]
        == 'attachment; filename="danfe_123_serie_1.pdf"'
    )


def test_documentos_nao_expoem_entrada_sintetica_de_pdf():
    nota, db = _criar_nota(serie="PDF")

    with pytest.raises(HTTPException) as exc_info:
        consulta_routes.baixar_xml_nota_entrada(
            nota.id,
            db=db,
            user_and_tenant=(object(), "tenant-a"),
        )

    assert exc_info.value.status_code == 409
