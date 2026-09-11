import pytest

from app.intnfe.order_fiscal_context import fiscal_order_context


@pytest.mark.parametrize(
    "channel",
    ["mercado_livre", "amazon", "shopee", "tiktok_shop"],
)
def test_marketplace_order_keeps_external_fiscal_facts_without_bling_dependency(
    channel,
):
    context = fiscal_order_context(
        {
            "origem": "conector_marketplace",
            "canal": channel,
            "modelo": 55,
            "cliente": {"uf": "MG"},
            "informacoes_adicionais": {"numero_pedido_loja": "PEDIDO-123"},
            "intermediador": {
                "cnpj": "35.635.824/0001-12",
                "identificacao": "LOJA-987",
            },
            "transporte": {
                "tipo": "Transportadora",
                "frete_por_conta": "Terceiros",
                "transportadora": {
                    "nome": "Transportadora Teste",
                    "cnpj": "11.222.333/0001-81",
                },
            },
            "pagamento": {"parcelas": [{"forma": "Cartão"}]},
        }
    )

    assert context["marketplace"] is True
    assert context["intermediador"] == {
        "cnpj": "35635824000112",
        "id_cadastro": "LOJA-987",
    }
    assert context["transporte"]["transportadora"]["cpf_cnpj"] == "11222333000181"
    assert context["formas_pagamento"] == ["Cartão"]
    assert context["pronto_para_montagem"] is True


def test_pdv_does_not_require_marketplace_identification():
    context = fiscal_order_context(
        {
            "origem": "corepet",
            "canal": "pdv",
            "modelo": 65,
            "pagamento": {"forma": "Dinheiro"},
        }
    )

    assert context["marketplace"] is False
    assert context["intermediador"] is None
    assert context["formas_pagamento"] == ["Dinheiro"]
    assert context["pronto_para_montagem"] is True


def test_partial_marketplace_or_carrier_data_is_blocked_before_emission_builder():
    context = fiscal_order_context(
        {
            "canal": "amazon",
            "modelo": 55,
            "intermediador": {"cnpj": "35.635.824/0001-12"},
            "transporte": {"transportadora": {"nome": "Transportadora Teste"}},
        }
    )

    assert context["pronto_para_montagem"] is False
    assert context["intermediador"] is None
    assert len(context["pendencias"]) == 4
