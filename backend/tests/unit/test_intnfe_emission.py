from types import SimpleNamespace

import pytest

from app.intnfe import emission


def _objects(channel="loja_fisica"):
    tenant = SimpleNamespace(id="11111111-1111-1111-1111-111111111111")
    connection = SimpleNamespace(
        emission_environment=2,
        nfe_series="3",
        nfce_series="23",
    )
    customer = SimpleNamespace(
        nome="Cliente Teste",
        razao_social=None,
        cpf="52998224725",
        cnpj=None,
        inscricao_estadual=None,
        endereco="Rua Um",
        numero="10",
        bairro="Centro",
        cidade="Presidente Prudente",
        codigo_municipio="3541406",
        estado="SP",
        cep="19010000",
        email="cliente@example.com",
    )
    product = SimpleNamespace(
        id=9,
        codigo="PET-9",
        codigo_barras=None,
        nome="Ração Teste",
        unidade="UN",
    )
    item = SimpleNamespace(
        tipo="produto",
        produto=product,
        quantidade=2,
        preco_unitario="10.00",
        desconto_item="2.00",
    )
    payment = SimpleNamespace(forma_pagamento="pix", valor="23.00")
    sale = SimpleNamespace(
        cliente=customer,
        itens=[item],
        pagamentos=[payment],
        desconto_valor="2.00",
        taxa_entrega="5.00",
        tem_entrega=True,
        total="23.00",
        canal=channel,
        numero_venda="VEN-TESTE",
    )
    return tenant, connection, sale


@pytest.fixture(autouse=True)
def fiscal_data(monkeypatch):
    monkeypatch.setattr(
        emission,
        "local_profile",
        lambda _db, _tenant: (
            {
                "cnpj": "33590794000140",
                "razaoSocial": "Empresa Teste Ltda",
                "nomeFantasia": "Empresa Teste",
                "inscricaoEstadual": "123456789",
                "crt": "1",
                "endereco": {
                    "logradouro": "Avenida Brasil",
                    "numero": "100",
                    "complemento": None,
                    "bairro": "Centro",
                    "municipio": "Presidente Prudente",
                    "codigoMunicipio": "3541406",
                    "uf": "SP",
                    "cep": "19010000",
                },
            },
            [],
        ),
    )
    monkeypatch.setattr(
        emission,
        "_resolver_fiscal_item_nfe",
        lambda _db, _sale, _item: {
            "ncm": "23091000",
            "cest": None,
            "origem_mercadoria": "0",
            "cfop_interno": "5102",
            "cfop_interestadual": "6102",
            "cst_icms": "102",
            "icms_aliquota": 18,
            "pis_cst": "49",
            "pis_aliquota": 0,
            "cofins_cst": "49",
            "cofins_aliquota": 0,
        },
    )


def test_payload_preserves_totals_and_hides_real_recipient_in_homologation():
    tenant, connection, sale = _objects()
    payload = emission.build_payload(None, tenant, connection, sale, "nfe")
    assert payload["ambienteCodigo"] == 2
    assert payload["serie"] == "3"
    assert payload["destinatario"]["razaoSocial"].startswith("NF-E EMITIDA")
    assert payload["produtos"][0]["valorTotal"] == 20.0
    assert payload["produtos"][0]["desconto"] == 2.0
    assert payload["produtos"][0]["impostos"]["icms"] == {
        "cst": "102",
        "origem": "0",
    }
    assert payload["frete"] == {"modalidade": "9", "valor": 5.0}
    assert payload["pagamentos"] == [{"formaPagamento": "17", "valor": 23.0}]


def test_interstate_sale_uses_interstate_cfop():
    tenant, connection, sale = _objects()
    sale.cliente.estado = "RJ"
    sale.cliente.cidade = "Rio de Janeiro"
    sale.cliente.codigo_municipio = "3304557"
    assert (
        emission.build_payload(None, tenant, connection, sale, "nfe")["produtos"][0][
            "cfop"
        ]
        == "6102"
    )


def test_marketplace_without_intermediary_snapshot_is_blocked():
    tenant, connection, sale = _objects(channel="amazon")
    with pytest.raises(emission.DirectEmissionError, match="intermediador"):
        emission.build_payload(None, tenant, connection, sale, "nfe")


def test_payment_total_must_match_sale_total():
    tenant, connection, sale = _objects()
    sale.pagamentos[0].valor = "22.99"
    with pytest.raises(emission.DirectEmissionError, match="formas de pagamento"):
        emission.build_payload(None, tenant, connection, sale, "nfe")
