from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.nfse_manual.service import (
    build_copy_text,
    build_preparation_snapshot,
    parse_nfse_xml,
    validate_attachment,
)


def _objects():
    tenant = SimpleNamespace(
        cnpj="12.345.678/0001-90",
        razao_social="Clínica Veterinária Maiara Ltda",
        inscricao_municipal="123456",
        cidade="Presidente Prudente",
        uf="SP",
    )
    customer = SimpleNamespace(
        nome="Tutor Teste",
        razao_social=None,
        cpf="123.456.789-09",
        cnpj=None,
        email="tutor@example.com",
        celular="18999999999",
        telefone=None,
        endereco="Rua das Flores",
        numero="10",
        complemento=None,
        bairro="Centro",
        cidade="Presidente Prudente",
        estado="SP",
        cep="19000-000",
    )
    fiscal = SimpleNamespace(
        nfse_item_lista_servico="5.01",
        municipio_iss="Presidente Prudente",
        municipio_iss_codigo="3541406",
        cnae_principal="7500100",
        iss_aliquota=Decimal("2.00"),
        iss_retido=False,
        nfse_natureza_operacao="1",
        nfse_regime_especial_tributacao="6",
        nfse_portal_url="https://issprudente.sp.gov.br/",
    )
    consultation = SimpleNamespace(
        id=42,
        finalizado_em=datetime(2026, 8, 19, 15, 30, tzinfo=timezone.utc),
    )
    return tenant, customer, fiscal, consultation


def test_preparation_builds_ready_snapshot_and_copy_text():
    tenant, customer, fiscal, consultation = _objects()

    snapshot = build_preparation_snapshot(
        tenant=tenant,
        customer=customer,
        fiscal=fiscal,
        consultation=consultation,
        amount=Decimal("180.50"),
        description="Consulta clínica e vacinação",
    )

    assert snapshot["ready"] is True
    assert snapshot["missing_fields"] == []
    assert snapshot["customer"]["document"] == "12345678909"
    assert snapshot["service"]["amount"] == 180.5
    assert snapshot["origin"]["consultation_id"] == 42

    copy_text = build_copy_text(snapshot)
    assert "Tutor Teste" in copy_text
    assert "R$ 180,50" in copy_text
    assert "Item da lista: 5.01" in copy_text


def test_preparation_lists_missing_required_data():
    tenant, customer, fiscal, consultation = _objects()
    customer.cpf = None
    fiscal.nfse_item_lista_servico = None

    snapshot = build_preparation_snapshot(
        tenant=tenant,
        customer=customer,
        fiscal=fiscal,
        consultation=consultation,
        amount=Decimal("0"),
        description="",
    )

    assert snapshot["ready"] is False
    assert "CPF ou CNPJ do cliente" in snapshot["missing_fields"]
    assert "item da lista de serviços" in snapshot["missing_fields"]
    assert "valor dos serviços" in snapshot["missing_fields"]


@pytest.mark.parametrize(
    ("amount_text", "expected"),
    [("123.45", Decimal("123.45")), ("1.234,56", Decimal("1234.56"))],
)
def test_xml_import_reads_nfse_metadata(amount_text, expected):
    xml = f"""
    <CompNfse xmlns="http://www.abrasf.org.br/nfse.xsd">
      <Rps><IdentificacaoRps><Numero>111</Numero></IdentificacaoRps></Rps>
      <Nfse>
        <InfNfse>
          <Numero>987</Numero>
          <CodigoVerificacao>ABC123</CodigoVerificacao>
          <DataEmissao>2026-08-19T10:15:00-03:00</DataEmissao>
          <ValoresNfse><ValorServicos>{amount_text}</ValorServicos></ValoresNfse>
        </InfNfse>
      </Nfse>
    </CompNfse>
    """.encode()

    metadata = parse_nfse_xml(xml)

    assert metadata["invoice_number"] == "987"
    assert metadata["verification_code"] == "ABC123"
    assert metadata["service_amount"] == expected
    assert metadata["issued_at"].utcoffset().total_seconds() == -3 * 60 * 60


def test_xml_import_rejects_doctype_and_pdf_validates_signature():
    with pytest.raises(HTTPException) as exc_info:
        parse_nfse_xml(
            b'<!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]><x>&e;</x>'
        )
    assert exc_info.value.status_code == 422

    validate_attachment("pdf", "nota.pdf", b"%PDF-1.7\nconteudo")
    with pytest.raises(HTTPException) as pdf_error:
        validate_attachment("pdf", "nota.pdf", b"arquivo falso")
    assert pdf_error.value.status_code == 422
