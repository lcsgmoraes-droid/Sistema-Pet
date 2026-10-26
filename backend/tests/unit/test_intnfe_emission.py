from copy import deepcopy
from datetime import date
from decimal import Decimal
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
        endereco_entrega="Rua Um, 10, Centro, Presidente Prudente/SP",
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


@pytest.mark.parametrize("environment", [1, 2])
@pytest.mark.parametrize("document", ["52998224725", "33590794000140"])
def test_delivery_uses_selected_additional_address_without_changing_sale(
    environment, document
):
    tenant, connection, sale = _objects()
    connection.emission_environment = environment
    sale.cliente.cpf = document if len(document) == 11 else None
    sale.cliente.cnpj = document if len(document) == 14 else None
    sale.cliente.enderecos_adicionais = [
        {
            "endereco": "Rua Dois",
            "numero": "20",
            "complemento": "Casa B",
            "bairro": "Vila Nova",
            "cidade": "Presidente Prudente",
            "estado": "SP",
            "cep": "19020-000",
            "codigo_municipio": "3541406",
        }
    ]
    sale.endereco_entrega = "Rua Dois, 20 - Casa B, Vila Nova, Presidente Prudente/SP"
    before = deepcopy(sale)

    payload = emission.build_payload(None, tenant, connection, sale, "nfce")

    assert sale == before
    consumer = payload["consumidor"]
    assert consumer["cpf" if len(document) == 11 else "cnpj"] == document
    assert consumer["endereco"]["logradouro"] == "Rua Dois"
    assert consumer["endereco"]["complemento"] == "Casa B"
    assert consumer["endereco"]["cep"] == "19020000"
    assert payload["indicadorPresenca"] == "4"
    assert "transportadora" not in payload["frete"]


def test_delivery_freight_includes_explicit_tax_values(monkeypatch):
    tenant, connection, sale = _objects()
    profile = emission.local_profile
    fiscal = emission._resolver_fiscal_item_nfe
    monkeypatch.setattr(
        emission, "local_profile", lambda *args: ({**profile(*args)[0], "crt": "3"}, [])
    )
    monkeypatch.setattr(
        emission,
        "_resolver_fiscal_item_nfe",
        lambda *args: {
            **fiscal(*args),
            "cst_icms": "00",
            "pis_cst": "01",
            "pis_aliquota": "1.65",
            "cofins_cst": "01",
            "cofins_aliquota": "7.60",
        },
    )

    product = emission.build_payload(None, tenant, connection, sale, "nfce")[
        "produtos"
    ][0]

    assert product["frete"] == 5
    assert product["impostos"]["icms"]["valor"] == 4.14
    assert product["impostos"]["pis"]["baseCalculo"] == 23
    assert product["impostos"]["pis"]["valor"] == 0.38
    assert product["impostos"]["cofins"]["baseCalculo"] == 23
    assert product["impostos"]["cofins"]["valor"] == 1.75


@pytest.mark.parametrize(
    "fee, expected", [("0.01", [0.01, 0, 0]), ("0.02", [0.01, 0.01, 0])]
)
def test_delivery_freight_distributes_residual_cents_and_preserves_payments(
    fee, expected
):
    tenant, connection, sale = _objects()
    sale.itens = [deepcopy(sale.itens[0]) for _ in range(3)]
    sale.taxa_entrega = fee
    sale.desconto_valor = "6.00"
    sale.total = str(Decimal("54.00") + Decimal(fee))
    sale.pagamentos = [
        SimpleNamespace(forma_pagamento="pix", valor="50.00"),
        SimpleNamespace(forma_pagamento="Cashback", valor="2.00"),
        SimpleNamespace(
            forma_pagamento="Crédito Cliente", valor=str(Decimal("2.00") + Decimal(fee))
        ),
    ]
    before = deepcopy(sale)

    payload = emission.build_payload(None, tenant, connection, sale, "nfce")

    assert [item["frete"] for item in payload["produtos"]] == expected
    assert sum(Decimal(str(item["frete"])) for item in payload["produtos"]) == Decimal(
        fee
    )
    assert [item["formaPagamento"] for item in payload["pagamentos"]] == [
        "17",
        "19",
        "05",
    ]
    assert sale == before


def test_delivery_preview_has_address_and_freight_contract(monkeypatch):
    tenant, connection, sale = _objects()
    monkeypatch.setattr(emission, "_connection", lambda *_: connection)

    preview = emission.preview(None, tenant, sale, "nfce")

    assert preview["indicador_presenca"] == "4"
    assert preview["modalidade_frete"] == "3"
    assert preview["frete"] == 5
    assert preview["itens"][0]["frete"] == 5
    assert preview["destinatario"]["endereco"]["logradouro"] == "Rua Um"


@pytest.mark.parametrize("field", ["cep", "codigo_municipio"])
def test_delivery_missing_fiscal_address_returns_clear_block(field):
    tenant, connection, sale = _objects()
    setattr(sale.cliente, field, None)

    with pytest.raises(emission.DirectEmissionError) as error:
        emission.build_payload(None, tenant, connection, sale, "nfce")

    assert error.value.code == "nfce_delivery_address_required"
    assert error.value.validation["pode_emitir"] is False
    assert error.value.validation["bloqueios"][0]["campo"].startswith(
        "entrega.endereco."
    )


def test_delivery_cpf_without_customer_cannot_replace_structured_address():
    tenant, connection, sale = _objects()
    sale.cliente = None
    sale.nfe_consumidor_cpf = "52998224725"

    with pytest.raises(emission.DirectEmissionError, match="Vincule um cliente"):
        emission.build_payload(None, tenant, connection, sale, "nfce")


def test_delivery_cannot_use_interstate_destination():
    tenant, connection, sale = _objects()
    sale.cliente.estado = "PR"
    sale.endereco_entrega = "Rua Um, 10, Centro, Presidente Prudente/PR"

    with pytest.raises(emission.DirectEmissionError, match="dentro do estado"):
        emission.build_payload(None, tenant, connection, sale, "nfce")


def test_delivery_negative_fee_is_blocked():
    tenant, connection, sale = _objects()
    sale.taxa_entrega = "-0.01"

    with pytest.raises(emission.DirectEmissionError, match="não pode ser negativa"):
        emission.build_payload(None, tenant, connection, sale, "nfce")


@pytest.mark.parametrize(
    "courier",
    [
        SimpleNamespace(is_terceirizado=True),
        SimpleNamespace(tipo_vinculo_entrega="terceirizado"),
    ],
)
def test_delivery_does_not_silently_classify_third_party_as_own(courier):
    tenant, connection, sale = _objects()
    sale.entregador = courier

    with pytest.raises(emission.DirectEmissionError, match="terceirizado"):
        emission.build_payload(None, tenant, connection, sale, "nfce")


@pytest.mark.parametrize("valid_address", [True, False])
def test_delivery_details_show_selected_address_and_keep_rejected_attempt_visible(
    valid_address,
):
    tenant, _connection, sale = _objects()
    sale.id = 123
    for field in (
        "nfe_numero",
        "nfe_serie",
        "nfe_chave",
        "nfe_codigo_erro",
        "nfe_motivo_rejeicao",
        "nfe_protocolo",
        "nfe_data_emissao",
        "vendedor",
    ):
        setattr(sale, field, None)
    sale.nfe_tipo, sale.nfe_modelo = "nfce", "65"
    sale.nfe_status, sale.nfe_ambiente = "rejeitada", 2
    sale.endereco_entrega = "Rua Dois, 20, Centro, Presidente Prudente/SP"
    sale.cliente.enderecos_adicionais = [
        {
            "endereco": "Rua Dois",
            "numero": "20",
            "bairro": "Centro",
            "cidade": "Presidente Prudente",
            "estado": "SP",
            "codigo_municipio": "3541406",
            "cep": "19020000" if valid_address else None,
        }
    ]

    details = emission.local_document_details(None, tenant, sale)

    assert details["indicador_presenca"].startswith("4 -")
    assert details["transporte"]["frete_por_conta"].startswith("3 -")
    if valid_address:
        assert details["cliente"]["endereco"] == "Rua Dois"
        assert details["cliente"]["numero"] == "20"
        assert details["endereco_entrega"]["cep"] == "19020000"
    else:
        assert details["endereco_entrega"]["endereco"] == sale.endereco_entrega


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


def test_novo_contrato_rateia_so_global_e_cupom_preservando_desconto_item():
    tenant, connection, sale = _objects()
    sale.desconto_venda_valor = 3
    sale.cupom_discount_applied = 4
    sale.desconto_valor = 9
    sale.total = "16.00"
    sale.pagamentos[0].valor = "16.00"
    payload = emission.build_payload(None, tenant, connection, sale, "nfe")
    assert payload["produtos"][0]["valorTotal"] == 20
    assert payload["produtos"][0]["desconto"] == 9
    assert sale.itens[0].desconto_item == "2.00"
    assert sale.itens[0].subtotal == "18.00"


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
    assert payload["informacoesAdicionais"].startswith("Venda VEN-TESTE | Crediario:")
    assert "CorePet" not in payload["informacoesAdicionais"]


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


def test_nfce_bloqueia_regra_386_no_item_tres_antes_da_transmissao(monkeypatch):
    tenant, connection, sale = _objects()
    sale.tem_entrega = False
    sale.taxa_entrega = "0.00"
    sale.total = "18.00"
    sale.pagamentos[0].valor = "18.00"
    primeiro = sale.itens[0]
    sale.itens = [
        primeiro,
        SimpleNamespace(
            **{
                **vars(primeiro),
                "produto": SimpleNamespace(**{**vars(primeiro.produto), "id": 10}),
            }
        ),
        SimpleNamespace(
            **{
                **vars(primeiro),
                "produto": SimpleNamespace(**{**vars(primeiro.produto), "id": 11}),
            }
        ),
    ]
    fiscal_original = emission._resolver_fiscal_item_nfe

    def fiscal_item(db, venda, item):
        fiscal = fiscal_original(db, venda, item)
        if item.produto.id == 11:
            return {
                **fiscal,
                "cfop_interno": "5405",
                "cst_icms": "102",
                "icms_st": True,
            }
        return fiscal

    monkeypatch.setattr(emission, "_resolver_fiscal_item_nfe", fiscal_item)

    with pytest.raises(emission.DirectEmissionError) as rejeicao:
        emission.build_payload(None, tenant, connection, sale, "nfce")

    bloqueios = rejeicao.value.validation["bloqueios"]
    assert {item["campo"] for item in bloqueios} == {"cfop", "cst_icms"}
    assert all(item["item_numero"] == 3 for item in bloqueios)
    assert all(item["produto_id"] == 11 for item in bloqueios)


def test_nfce_accepts_own_delivery_fee_with_recipient_address():
    tenant, connection, sale = _objects()

    payload = emission.build_payload(None, tenant, connection, sale, "nfce")
    assert payload["indicadorPresenca"] == "4"
    assert payload["frete"] == {"modalidade": "3", "valor": 5.0}
    assert payload["consumidor"]["endereco"]["logradouro"] == "Rua Um"
    assert payload["consumidor"]["endereco"]["codigoMunicipio"] == "3541406"
    assert payload["produtos"][0]["frete"] == 5.0
    assert payload["pagamentos"] == [{"formaPagamento": "17", "valor": 23.0}]


def test_free_delivery_nfce_still_has_presence_freight_and_address():
    tenant, connection, sale = _objects()
    sale.taxa_entrega = "0.00"
    sale.total = "18.00"
    sale.pagamentos[0].valor = "18.00"
    payload = emission.build_payload(None, tenant, connection, sale, "nfce")
    assert payload["indicadorPresenca"] == "4"
    assert payload["frete"] == {"modalidade": "3", "valor": 0.0}
    assert payload["consumidor"]["endereco"]["cep"] == "19010000"
    assert "frete" not in payload["produtos"][0]


def test_delivery_nfce_requires_identified_recipient():
    tenant, connection, sale = _objects()
    sale.cliente = None

    with pytest.raises(emission.DirectEmissionError, match="consumidor identificado"):
        emission.build_payload(None, tenant, connection, sale, "nfce")


def test_nfce_uses_sale_cpf_without_customer_registration():
    tenant, connection, sale = _objects()
    sale.cliente = None
    sale.nfe_consumidor_cpf = "52998224725"
    sale.tem_entrega = False
    sale.taxa_entrega = "0.00"
    sale.total = "18.00"
    sale.pagamentos[0].valor = "18.00"

    payload = emission.build_payload(None, tenant, connection, sale, "nfce")

    assert payload["consumidor"]["cpf"] == "52998224725"
    assert payload["consumidor"]["nome"].startswith("NF-E EMITIDA")
    assert sale.cliente is None

    connection.emission_environment = 1
    production_payload = emission.build_payload(None, tenant, connection, sale, "nfce")
    assert production_payload["consumidor"] == {"cpf": "52998224725"}


def test_sale_cpf_does_not_enable_nfe_without_customer():
    tenant, connection, sale = _objects()
    sale.cliente = None
    sale.nfe_consumidor_cpf = "52998224725"

    with pytest.raises(emission.DirectEmissionError, match="cliente cadastrado"):
        emission.build_payload(None, tenant, connection, sale, "nfe")


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


def test_cst_00_nao_e_enviado_como_csosn(monkeypatch):
    tenant, connection, sale = _objects()
    sale.tem_entrega = False
    sale.taxa_entrega = "0.00"
    sale.total = sale.pagamentos[0].valor = "18.00"
    fiscal_original = emission._resolver_fiscal_item_nfe
    monkeypatch.setattr(
        emission,
        "_resolver_fiscal_item_nfe",
        lambda db, venda, item: {
            **fiscal_original(db, venda, item),
            "cst_icms": "00",
        },
    )

    with pytest.raises(emission.DirectEmissionError, match="CSOSN 00") as exc_info:
        emission.build_payload(None, tenant, connection, sale, "nfce")

    assert exc_info.value.validation["bloqueios"][0]["campo"] == "cst_icms"
    assert exc_info.value.validation["bloqueios"][0]["valor_atual"] == "00"


def test_missing_product_taxes_return_editable_fiscal_fields(monkeypatch):
    tenant, connection, sale = _objects()
    sale.tem_entrega = False
    sale.taxa_entrega = "0.00"
    sale.total = sale.pagamentos[0].valor = "18.00"
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
            "item_id": None,
            "item_numero": 1,
            "lote_id": None,
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
            "origem_mercadoria": "0",
            "cfop": "5102",
            "icms": "102",
            "pis": "49",
            "cofins": "49",
        }
    ]
    assert details["diagnostico_rejeicao"]["correcoes"][0]["campo"] == "cst_icms"
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


@pytest.mark.parametrize("document_type", ["nfe", "nfce"])
@pytest.mark.parametrize("cashback_name", ["Cashback", "cashback", " CASHBACK "])
def test_debit_and_cashback_use_specific_payment_codes(document_type, cashback_name):
    tenant, connection, sale = _objects()
    sale.itens[0].quantidade = 1
    sale.itens[0].preco_unitario = "28.90"
    sale.itens[0].desconto_item = "0.00"
    sale.itens[0].subtotal = "28.90"
    sale.desconto_valor = "0.00"
    sale.taxa_entrega = "0.00"
    sale.tem_entrega = False
    sale.total = "28.90"
    sale.pagamentos = [
        SimpleNamespace(forma_pagamento="Cartão de débito", valor="27.00"),
        SimpleNamespace(forma_pagamento=cashback_name, valor="1.90"),
    ]

    payload = emission.build_payload(None, tenant, connection, sale, document_type)

    assert payload["pagamentos"] == [
        {"formaPagamento": "04", "valor": 27.0, "tipoIntegracao": "2"},
        {"formaPagamento": "19", "valor": 1.9},
    ]
    assert payload["produtos"][0]["valorTotal"] == 28.9
    assert payload["produtos"][0].get("desconto", 0) == 0


@pytest.mark.parametrize("document_type", ["nfe", "nfce"])
@pytest.mark.parametrize(
    "credit_name", ["Crédito Cliente", "credito_cliente", " CRÉDITO CLIENTE "]
)
def test_customer_credit_uses_store_credit_without_installments(
    document_type, credit_name
):
    tenant, connection, sale = _objects()
    sale.taxa_entrega = "0.00"
    sale.tem_entrega = False
    sale.total = "18.00"
    sale.pagamentos = [
        SimpleNamespace(
            forma_pagamento=credit_name,
            valor="18.00",
            data_recebimento_prevista=date(2026, 10, 14),
            numero_parcelas=1,
        )
    ]
    sale.contas_receber = [
        SimpleNamespace(
            id=1,
            descricao="Venda VEN-TESTE",
            status="recebido",
            data_vencimento=date(2026, 10, 14),
            valor_original="18.00",
            forma_pagamento=SimpleNamespace(tipo="credito_cliente"),
        )
    ]

    payload = emission.build_payload(None, tenant, connection, sale, document_type)

    assert payload["pagamentos"] == [{"formaPagamento": "05", "valor": 18.0}]
    assert "Crediario:" not in payload["informacoesAdicionais"]


@pytest.mark.parametrize("document_type", ["nfe", "nfce"])
def test_coupon_cashback_customer_credit_and_debit_preserve_fiscal_totals(
    document_type,
):
    tenant, connection, sale = _objects()
    first_item = sale.itens[0]
    first_item.quantidade = 1
    first_item.preco_unitario = "70.00"
    first_item.desconto_item = "5.00"
    first_item.subtotal = "65.00"
    second_item = SimpleNamespace(
        tipo="produto",
        produto=first_item.produto,
        quantidade=1,
        preco_unitario="30.00",
        desconto_item="0.00",
        subtotal="30.00",
    )
    sale.itens = [first_item, second_item]
    sale.desconto_venda_valor = "0.00"
    sale.cupom_code = "CAMPANHA7"
    sale.cupom_discount_applied = "7.00"
    sale.desconto_valor = "12.00"
    sale.taxa_entrega = "0.00"
    sale.tem_entrega = False
    sale.total = "88.00"
    sale.pagamentos = [
        SimpleNamespace(forma_pagamento="Crédito Cliente", valor="20.00"),
        SimpleNamespace(forma_pagamento="Cashback", valor="8.00"),
        SimpleNamespace(forma_pagamento="Cartão de débito", valor="60.00"),
    ]

    payload = emission.build_payload(None, tenant, connection, sale, document_type)

    assert payload["pagamentos"] == [
        {"formaPagamento": "05", "valor": 20.0},
        {"formaPagamento": "19", "valor": 8.0},
        {"formaPagamento": "04", "valor": 60.0, "tipoIntegracao": "2"},
    ]
    assert [item["valorTotal"] for item in payload["produtos"]] == [70.0, 30.0]
    assert [item["desconto"] for item in payload["produtos"]] == [9.79, 2.21]
    assert first_item.desconto_item == "5.00"
    assert second_item.desconto_item == "0.00"
    assert "Crediario:" not in payload["informacoesAdicionais"]


@pytest.mark.parametrize("document_type", ["nfe", "nfce"])
def test_credit_card_keeps_card_payment_code(document_type):
    tenant, connection, sale = _objects()
    sale.taxa_entrega = "0.00"
    sale.tem_entrega = False
    sale.total = "18.00"
    sale.pagamentos = [
        SimpleNamespace(forma_pagamento="Cartão de crédito", valor="18.00")
    ]

    payload = emission.build_payload(None, tenant, connection, sale, document_type)

    assert payload["pagamentos"] == [
        {"formaPagamento": "03", "valor": 18.0, "tipoIntegracao": "2"}
    ]


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


def _amazon_commercial_data():
    return {
        "canal": "amazon",
        "numero_pedido": "PEDIDO-EXTERNO-123",
        "codigo_rastreamento": "RASTREIO-123",
        "informacoes_complementares": "Enviar com a documentação da mercadoria.",
        "intermediador_cnpj": "11444777000161",
        "intermediador_identificacao": "LOJA-VENDEDOR-987",
    }


@pytest.mark.parametrize("financial_channel", ["loja_fisica", "amazon"])
def test_nfe_manual_amazon_envia_intermediador_e_referencia_sem_alterar_venda(
    financial_channel,
):
    tenant, connection, sale = _objects(channel=financial_channel)
    sale.nfe_contexto_comercial = _amazon_commercial_data()
    original_items = deepcopy(sale.itens)
    original_payments = deepcopy(sale.pagamentos)

    payload = emission.build_payload(None, tenant, connection, sale, "nfe")

    assert payload["indicadorPresenca"] == "2"
    assert payload["intermediador"] == {
        "cnpj": "11444777000161",
        "identificadorCadastro": "LOJA-VENDEDOR-987",
    }
    assert "Canal de venda: Amazon" in payload["informacoesAdicionais"]
    assert "Nº Pedido Loja: PEDIDO-EXTERNO-123" in payload["informacoesAdicionais"]
    assert "Código de rastreamento: RASTREIO-123" in payload["informacoesAdicionais"]
    assert sale.canal == financial_channel
    assert sale.total == "23.00"
    assert sale.itens == original_items
    assert sale.pagamentos == original_payments
    assert "IBPT" not in payload["informacoesAdicionais"]
    assert "vTotTrib" not in str(payload)


def test_contexto_amazon_recusa_nfce_antes_de_transmitir():
    tenant, connection, sale = _objects()
    sale.nfe_contexto_comercial = _amazon_commercial_data()

    with pytest.raises(emission.DirectEmissionError, match="modelo 55"):
        emission.build_payload(None, tenant, connection, sale, "nfce")


@pytest.mark.parametrize(
    "missing_field",
    ["numero_pedido", "intermediador_cnpj", "intermediador_identificacao"],
)
def test_contexto_amazon_incompleto_nao_vira_venda_direta(missing_field):
    tenant, connection, sale = _objects()
    sale.nfe_contexto_comercial = _amazon_commercial_data()
    sale.nfe_contexto_comercial[missing_field] = ""

    with pytest.raises(emission.DirectEmissionError, match="Amazon"):
        emission.build_payload(None, tenant, connection, sale, "nfe")


def test_contexto_amazon_nao_libera_outro_marketplace():
    tenant, connection, sale = _objects(channel="shopee")
    sale.nfe_contexto_comercial = _amazon_commercial_data()

    with pytest.raises(emission.DirectEmissionError, match="apenas para vendas do PDV"):
        emission.build_payload(None, tenant, connection, sale, "nfe")


def test_venda_direta_online_envia_presenca_internet_sem_intermediador():
    tenant, connection, sale = _objects()
    sale.nfe_contexto_comercial = {
        "canal": "venda_direta_online",
        "numero_pedido": "WEB-123",
    }

    payload = emission.build_payload(None, tenant, connection, sale, "nfe")

    assert payload["indicadorPresenca"] == "2"
    assert "intermediador" not in payload
    assert "Nº Pedido Loja: WEB-123" in payload["informacoesAdicionais"]


def test_novo_campo_nulo_preserva_payload_pdv_existente():
    tenant, connection, sale = _objects()
    previous = emission.build_payload(None, tenant, connection, sale, "nfe")
    sale.nfe_contexto_comercial = None

    assert emission.build_payload(None, tenant, connection, sale, "nfe") == previous


def test_preview_retorna_contexto_salvo_e_dados_que_serao_transmitidos(monkeypatch):
    tenant, connection, sale = _objects()
    sale.nfe_contexto_comercial = _amazon_commercial_data()
    monkeypatch.setattr(emission, "_connection", lambda *_args: connection)

    preview = emission.preview(None, tenant, sale, "nfe")
    payload = emission.build_payload(None, tenant, connection, sale, "nfe")
    previous_fingerprint = emission.emission_fingerprint(None, tenant, sale, "nfe")
    sale.nfe_contexto_comercial["numero_pedido"] = "PEDIDO-OUTRO-456"

    assert preview["contexto_comercial"]["numero_pedido"] == "PEDIDO-EXTERNO-123"
    assert preview["informacoes_adicionais"] == payload["informacoesAdicionais"]
    assert previous_fingerprint != emission.emission_fingerprint(
        None, tenant, sale, "nfe"
    )


def test_contexto_novo_nunca_trunca_referencia_ou_observacoes():
    tenant, connection, sale = _objects()
    sale.nfe_contexto_comercial = _amazon_commercial_data()
    sale.observacoes = "x" * 5000

    with pytest.raises(emission.DirectEmissionError, match="5000 caracteres"):
        emission.build_payload(None, tenant, connection, sale, "nfe")


def test_detalhes_fiscais_exibem_presenca_e_intermediador_que_foram_salvos():
    tenant, _connection, sale = _objects()
    sale.id = 123
    for field in (
        "nfe_numero",
        "nfe_serie",
        "nfe_chave",
        "nfe_codigo_erro",
        "nfe_motivo_rejeicao",
        "nfe_protocolo",
        "nfe_data_emissao",
    ):
        setattr(sale, field, None)
    sale.nfe_tipo, sale.nfe_modelo = "nfe", "55"
    sale.nfe_status, sale.nfe_ambiente = "autorizada", 1
    sale.nfe_contexto_comercial = _amazon_commercial_data()

    details = emission.local_document_details(None, tenant, sale)

    assert details["indicador_presenca"].startswith("2 -")
    assert details["intermediador"] == {
        "cnpj": "11444777000161",
        "identificacao": "LOJA-VENDEDOR-987",
    }
    assert (
        details["informacoes_adicionais"]["numero_pedido_loja"] == "PEDIDO-EXTERNO-123"
    )
    assert sale.canal == "loja_fisica"
