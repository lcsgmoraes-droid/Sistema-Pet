from types import SimpleNamespace

import pytest

from app.intnfe import emission


def _objects(channel="loja_fisica"):
    tenant = SimpleNamespace(
        id="11111111-1111-1111-1111-111111111111", cnpj="33590794000140"
    )
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
        subtotal="18.00",
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
            "cfop_interestadual_nao_contribuinte": "6102",
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
    assert payload["produtos"][0]["impostos"]["pis"] == {
        "cst": "49",
        "aliquota": 0.0,
    }
    assert payload["produtos"][0]["impostos"]["cofins"] == {
        "cst": "49",
        "aliquota": 0.0,
    }
    assert payload["emitente"]["cnpj"] == "33590794000140"
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


def test_interstate_st_sale_to_non_contributor_uses_6108(monkeypatch):
    tenant, connection, sale = _objects()
    sale.cliente.estado = "RJ"
    sale.cliente.cidade = "Rio de Janeiro"
    sale.cliente.codigo_municipio = "3304557"
    monkeypatch.setattr(
        emission,
        "_resolver_fiscal_item_nfe",
        lambda *_args: {
            "ncm": "23099010",
            "cest": "2200100",
            "origem_mercadoria": "0",
            "cfop_interno": "5405",
            "cfop_interestadual": "6102",
            "cfop_interestadual_nao_contribuinte": "6108",
            "cst_icms": "500",
            "icms_st": True,
            "icms_aliquota": None,
            "pis_cst": "49",
            "pis_aliquota": 0,
            "cofins_cst": "49",
            "cofins_aliquota": 0,
        },
    )

    product = emission.build_payload(None, tenant, connection, sale, "nfe")["produtos"][
        0
    ]

    assert product["cfop"] == "6108"
    assert product["impostos"]["icms"] == {"cst": "500", "origem": "0"}


def test_non_contributor_with_incompatible_csosn_is_blocked(monkeypatch):
    tenant, connection, sale = _objects()
    monkeypatch.setattr(
        emission,
        "_resolver_fiscal_item_nfe",
        lambda *_args: {
            "ncm": "23091000",
            "cest": None,
            "origem_mercadoria": "0",
            "cfop_interno": "5102",
            "cfop_interestadual": "6102",
            "cfop_interestadual_nao_contribuinte": "6102",
            "cst_icms": "900",
            "icms_aliquota": 18,
            "pis_cst": "49",
            "pis_aliquota": 0,
            "cofins_cst": "49",
            "cofins_aliquota": 0,
        },
    )

    with pytest.raises(emission.DirectEmissionError, match="CSOSN 900"):
        emission.build_payload(None, tenant, connection, sale, "nfe")


def test_local_document_details_keeps_sale_items_visible_after_rejection():
    tenant, _connection, sale = _objects()
    tenant.uf = "SP"
    tenant.id = "11111111-1111-1111-1111-111111111111"
    sale.id = 123
    sale.nfe_numero = 17842
    sale.nfe_serie = 2
    sale.nfe_modelo = "55"
    sale.nfe_tipo = "nfe"
    sale.nfe_chave = "3" * 44
    sale.nfe_status = "rejeitada"
    sale.nfe_codigo_erro = "600"
    sale.nfe_motivo_rejeicao = "CSOSN incompatível"
    sale.nfe_protocolo = None
    sale.nfe_ambiente = 1
    sale.nfe_data_emissao = None
    sale.vendedor = SimpleNamespace(nome="Vendedor")
    sale.endereco_entrega = None
    sale.observacoes = None
    sale.cliente.id = 7
    sale.cliente.codigo = "6695"
    sale.cliente.tipo_pessoa = "PF"
    sale.cliente.celular = "18999999999"
    sale.cliente.telefone = None
    sale.cliente.complemento = None
    sale.itens[0].produto_id = 9
    sale.itens[0].servico_descricao = None
    sale.pagamentos[0].prazo_recebimento_dias = None
    sale.pagamentos[0].data_recebimento_prevista = None
    sale.pagamentos[0].numero_transacao = None

    details = emission.local_document_details(None, tenant, sale)

    assert details["codigo_erro"] == "600"
    assert details["cliente"]["nome"] == "Cliente Teste"
    assert details["itens"] == [
        {
            "produto_id": 9,
            "codigo": "PET-9",
            "descricao": "Ração Teste",
            "unidade": "UN",
            "quantidade": 2,
            "valor_unitario": 10.0,
            "valor_total": 20.0,
            "desconto": 2.0,
            "ncm": "23091000",
            "cest": None,
            "cfop": "5102",
            "icms": "102",
            "pis": "49",
            "cofins": "49",
        }
    ]
    assert details["totais"] == {
        "valor_produtos": 20.0,
        "valor_frete": 5.0,
        "valor_seguro": 0,
        "outras_despesas": 0,
        "valor_desconto": 2.0,
        "valor_total": 23.0,
    }
    assert details["pagamento"]["parcelas"][0]["forma"] == "pix"


def test_cst_49_without_saved_rate_is_sent_with_explicit_zero(monkeypatch):
    tenant, connection, sale = _objects()
    monkeypatch.setattr(
        emission,
        "_resolver_fiscal_item_nfe",
        lambda *_args: {
            "ncm": "23091000",
            "cest": None,
            "origem_mercadoria": "0",
            "cfop_interno": "5102",
            "cfop_interestadual": "6102",
            "cst_icms": "102",
            "icms_aliquota": None,
            "pis_cst": "49",
            "pis_aliquota": None,
            "cofins_cst": "49",
            "cofins_aliquota": None,
        },
    )

    taxes = emission.build_payload(None, tenant, connection, sale, "nfe")["produtos"][
        0
    ]["impostos"]

    assert taxes["pis"] == {"cst": "49", "aliquota": 0.0}
    assert taxes["cofins"] == {"cst": "49", "aliquota": 0.0}


def test_marketplace_without_intermediary_snapshot_is_blocked():
    tenant, connection, sale = _objects(channel="amazon")
    with pytest.raises(emission.DirectEmissionError, match="intermediador"):
        emission.build_payload(None, tenant, connection, sale, "nfe")


def test_payment_total_must_match_sale_total():
    tenant, connection, sale = _objects()
    sale.pagamentos[0].valor = "22.99"
    with pytest.raises(emission.DirectEmissionError, match="formas de pagamento"):
        emission.build_payload(None, tenant, connection, sale, "nfe")


def test_fractional_quantity_uses_saved_subtotal_for_one_cent_rounding():
    tenant, connection, sale = _objects()
    item = sale.itens[0]
    item.quantidade = "0.941"
    item.preco_unitario = "169.90"
    item.desconto_item = "0"
    item.subtotal = "159.89"
    sale.desconto_valor = "0"
    sale.taxa_entrega = "0"
    sale.tem_entrega = False
    sale.total = "159.89"
    sale.pagamentos[0].valor = "159.89"

    product = emission.build_payload(None, tenant, connection, sale, "nfe")["produtos"][
        0
    ]

    assert product["valorTotal"] == 159.89
    assert round(product["quantidade"] * product["valorUnitario"], 2) == 159.89


def test_saved_subtotal_with_more_than_one_cent_difference_is_blocked():
    tenant, connection, sale = _objects()
    sale.itens[0].subtotal = "18.02"

    with pytest.raises(emission.DirectEmissionError, match="subtotal salvo"):
        emission.build_payload(None, tenant, connection, sale, "nfe")
