from datetime import date
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


def test_crediario_uses_credito_loja_instead_of_outros():
    tenant, connection, sale = _objects()
    sale.pagamentos[0].forma_pagamento = "Crediário"
    sale.pagamentos[0].numero_parcelas = 1
    sale.pagamentos[0].data_recebimento_prevista = date(2026, 10, 5)
    sale.pagamentos[0].intervalo_crediario = None

    payload = emission.build_payload(None, tenant, connection, sale, "nfe")

    assert payload["pagamentos"] == [{"formaPagamento": "05", "valor": 23.0}]
    assert (
        "Crediario: 1/1 vence em 05/10/2026 - R$ 23,00"
        in payload["informacoesAdicionais"]
    )


def test_crediario_uses_saved_receivable_due_date_and_sale_observation():
    tenant, connection, sale = _objects()
    sale.observacoes = "Entregar no posto"
    sale.pagamentos[0].forma_pagamento = "Crediário"
    sale.pagamentos[0].numero_parcelas = 1
    sale.pagamentos[0].data_recebimento_prevista = date(2026, 10, 20)
    sale.pagamentos[0].intervalo_crediario = None
    sale.contas_receber = [
        SimpleNamespace(
            id=42,
            descricao="Venda VEN-TESTE - Crediário",
            status="pendente",
            data_vencimento=date(2026, 10, 5),
            numero_parcela=1,
            total_parcelas=1,
            valor_original="23.00",
            valor_final="23.00",
            forma_pagamento=SimpleNamespace(tipo="crediario"),
        )
    ]

    payload = emission.build_payload(None, tenant, connection, sale, "nfe")

    assert "Observacoes da venda: Entregar no posto" in payload["informacoesAdicionais"]
    assert "05/10/2026" in payload["informacoesAdicionais"]
    assert "20/10/2026" not in payload["informacoesAdicionais"]


def test_nfe_accepts_complete_recipient_address_without_cep():
    tenant, connection, sale = _objects()
    sale.cliente.cep = None

    recipient = emission.build_payload(None, tenant, connection, sale, "nfe")[
        "destinatario"
    ]

    assert recipient["endereco"]["codigoMunicipio"] == "3541406"
    assert "cep" not in recipient["endereco"]


def test_nfe_still_requires_mandatory_recipient_address_fields():
    tenant, connection, sale = _objects()
    sale.cliente.codigo_municipio = None

    with pytest.raises(emission.DirectEmissionError, match="código IBGE"):
        emission.build_payload(None, tenant, connection, sale, "nfe")


def test_counter_nfce_does_not_require_recipient_address():
    tenant, connection, sale = _objects()
    sale.tem_entrega = False
    sale.taxa_entrega = "0.00"
    sale.total = "18.00"
    sale.pagamentos[0].valor = "18.00"
    sale.cliente.endereco = None
    sale.cliente.numero = None
    sale.cliente.bairro = None
    sale.cliente.cidade = None
    sale.cliente.codigo_municipio = None
    sale.cliente.estado = None
    sale.cliente.cep = None

    payload = emission.build_payload(None, tenant, connection, sale, "nfce")
    consumer = payload["consumidor"]

    assert consumer["cpf"] == "52998224725"
    assert consumer["nome"].startswith("NF-E EMITIDA")
    assert "endereco" not in consumer
    assert "razaoSocial" not in consumer
    assert "indicadorIe" not in consumer
    assert payload["produtos"][0]["cfop"] == "5102"
    assert "frete" not in payload
    assert "documentosReferenciados" not in payload


def test_nfce_with_delivery_fee_requires_nfe():
    tenant, connection, sale = _objects()

    with pytest.raises(emission.DirectEmissionError, match="não aceita frete"):
        emission.build_payload(None, tenant, connection, sale, "nfce")


def test_delivery_nfce_without_fee_requires_identity_but_not_address():
    tenant, connection, sale = _objects()
    sale.taxa_entrega = "0.00"
    sale.total = "18.00"
    sale.pagamentos[0].valor = "18.00"
    sale.cliente.endereco = None
    sale.cliente.numero = None
    sale.cliente.bairro = None
    sale.cliente.cidade = None
    sale.cliente.codigo_municipio = None
    sale.cliente.estado = None

    payload = emission.build_payload(None, tenant, connection, sale, "nfce")

    assert payload["consumidor"]["cpf"] == "52998224725"
    assert payload["produtos"][0]["cfop"] == "5102"


def test_delivery_nfce_requires_identified_recipient():
    tenant, connection, sale = _objects()
    sale.cliente = None

    with pytest.raises(emission.DirectEmissionError, match="consumidor identificado"):
        emission.build_payload(None, tenant, connection, sale, "nfce")


def test_high_value_nfce_requires_identified_recipient():
    with pytest.raises(emission.DirectEmissionError, match="consumidor identificado"):
        emission._recipient(
            None,
            1,
            "nfce",
            require_identity=True,
            require_address=True,
        )


def test_first_corepet_number_is_recorded_for_sequence():
    saved = []

    class Query:
        def filter(self, *_args):
            return self

        def one_or_none(self):
            return None

    db = SimpleNamespace(query=lambda *_args: Query(), add=saved.append)
    sale = SimpleNamespace(
        tenant_id="11111111-1111-1111-1111-111111111111",
        nfe_numero=529,
        nfe_serie=1,
        nfe_ambiente=1,
        nfe_modelo="65",
    )

    emission._remember_sequence_start(db, sale)

    assert len(saved) == 1
    assert saved[0].modelo == 65
    assert saved[0].serie == "1"
    assert saved[0].numero_inicial == 529


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


def test_nfce_for_customer_from_another_state_stays_internal():
    tenant, connection, sale = _objects()
    sale.tem_entrega = False
    sale.taxa_entrega = "0.00"
    sale.total = "18.00"
    sale.pagamentos[0].valor = "18.00"
    sale.cliente.estado = "RJ"
    sale.cliente.cidade = "Rio de Janeiro"
    sale.cliente.codigo_municipio = "3304557"

    payload = emission.build_payload(None, tenant, connection, sale, "nfce")

    assert payload["produtos"][0]["cfop"] == "5102"
    assert "endereco" not in payload["consumidor"]


def test_provider_validation_maps_single_product_tax_fields():
    _tenant, _connection, sale = _objects()

    validation = emission._provider_validation(
        sale,
        ["CFOP do produto é inválido.", "CST do PIS é obrigatório."],
    )

    assert [item["campo"] for item in validation["bloqueios"]] == ["cfop", "pis_cst"]
    assert all(item["produto_id"] == 9 for item in validation["bloqueios"])


def test_multiple_recorded_fifo_lots_block_direct_emission():
    tenant, connection, sale = _objects()
    sale.id = 20
    sale.tenant_id = tenant.id
    sale.itens[0].produto_id = sale.itens[0].produto.id
    sale.itens[0].lote_id = None
    sale.itens[0].estoque_origem_tenant_id = None

    class RowsQuery:
        def filter(self, *_args):
            return self

        def all(self):
            return [
                SimpleNamespace(
                    lotes_consumidos='[{"lote_id": 2057}, {"lote_id": 2088}]'
                )
            ]

    db = SimpleNamespace(query=lambda *_args: RowsQuery())

    with pytest.raises(emission.DirectEmissionError, match="mais de um lote"):
        emission.build_payload(db, tenant, connection, sale, "nfe")


def test_single_recorded_fifo_lot_is_recovered_for_older_sale():
    _tenant, _connection, sale = _objects()
    sale.id = 20
    sale.tenant_id = "11111111-1111-1111-1111-111111111111"
    item = sale.itens[0]
    item.produto_id = item.produto.id
    item.lote_id = None
    item.estoque_origem_tenant_id = None
    expected_lot = SimpleNamespace(id=2057, fiscal_ncm="23099010")

    class Query:
        def __init__(self, rows=None, first=None):
            self.rows = rows
            self.first_value = first

        def filter(self, *_args):
            return self

        def all(self):
            return self.rows

        def first(self):
            return self.first_value

    def query(target):
        if target is emission.ProdutoLote:
            return Query(first=expected_lot)
        return Query(rows=[SimpleNamespace(lotes_consumidos='[{"lote_id": 2057}]')])

    recovered = emission._lot_from_recorded_fifo(
        SimpleNamespace(query=query), sale, item
    )

    assert recovered is expected_lot


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

    with pytest.raises(emission.DirectEmissionError, match="CSOSN 900") as exc_info:
        emission.build_payload(None, tenant, connection, sale, "nfe")

    bloqueio = exc_info.value.validation["bloqueios"][0]
    assert bloqueio["produto_id"] == 9
    assert bloqueio["campo"] == "cst_icms"
    assert bloqueio["valor_atual"] == "900"


def test_missing_product_taxes_return_editable_fiscal_fields(monkeypatch):
    tenant, connection, sale = _objects()
    monkeypatch.setattr(
        emission,
        "_resolver_fiscal_item_nfe",
        lambda *_args: {
            "ncm": "23091000",
            "origem_mercadoria": "0",
            "cfop_interno": "5102",
            "cfop_interestadual": "6102",
            "cfop_interestadual_nao_contribuinte": "6102",
            "cst_icms": None,
            "pis_cst": None,
            "cofins_cst": None,
        },
    )

    with pytest.raises(emission.DirectEmissionError) as exc_info:
        emission.build_payload(None, tenant, connection, sale, "nfce")

    bloqueios = exc_info.value.validation["bloqueios"]
    assert {item["campo"] for item in bloqueios} == {
        "cst_icms",
        "pis_cst",
        "cofins_cst",
    }
    assert all(item["produto_id"] == 9 for item in bloqueios)


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


@pytest.mark.parametrize(
    "channel",
    [
        "amazon",
        "mercado_livre",
        "Mercado Livre",
        "ml",
        "shopee",
        "tiktok",
        "TikTok Shop",
    ],
)
def test_direct_emission_is_blocked_for_every_marketplace_channel(channel):
    tenant, connection, sale = _objects(channel=channel)
    with pytest.raises(emission.DirectEmissionError, match="apenas para vendas do PDV"):
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
