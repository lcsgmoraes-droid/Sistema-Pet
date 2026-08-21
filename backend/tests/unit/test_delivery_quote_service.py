from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.delivery_quote_service import DeliveryQuoteError, quote_delivery


def _config(**overrides):
    values = {
        "logradouro": "Rua da Loja",
        "numero": "100",
        "bairro": "Centro",
        "cidade": "Campinas",
        "estado": "SP",
        "cep": "13000-000",
        "entrega_ativa": True,
        "retirada_ativa": True,
        "modalidade_cobranca": "por_km",
        "taxa_fixa": 12,
        "valor_por_km_cobrado": 2,
        "taxa_minima": 5,
        "distancia_maxima_entrega_km": 20,
        "frete_gratis_acima": 150,
        "distancia_maxima_frete_gratis_km": 8,
        "pedido_minimo": 0,
        "prazo_entrega_texto": "Entrega hoje",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


TENANT = SimpleNamespace(cidade="Campinas", uf="SP")


def _quote(config, *, subtotal=100, distance=Decimal("5")):
    return quote_delivery(
        config=config,
        tenant=TENANT,
        cidade_destino="Campinas",
        endereco_destino="Rua do Cliente, 20, Campinas, SP",
        subtotal_elegivel=subtotal,
        distance_calculator=lambda *_args: distance,
    )


def test_por_km_charges_distance_and_respects_minimum_fee():
    regular = _quote(_config(), subtotal=100, distance=Decimal("10"))
    minimum = _quote(_config(), subtotal=100, distance=Decimal("1"))

    assert regular["valor_frete"] == 20
    assert regular["distancia_km"] == 10
    assert regular["valor_por_km"] == 2
    assert minimum["valor_frete"] == 5


def test_free_shipping_value_does_not_override_free_distance_limit():
    free = _quote(_config(), subtotal=180, distance=Decimal("5"))
    charged = _quote(_config(), subtotal=180, distance=Decimal("12"))

    assert free["valor_frete"] == 0
    assert free["frete_gratis_aplicado"] is True
    assert charged["valor_frete"] == 24
    assert charged["frete_gratis_aplicado"] is False


def test_delivery_maximum_distance_blocks_checkout():
    with pytest.raises(DeliveryQuoteError, match="fora da area"):
        _quote(_config(), subtotal=300, distance=Decimal("20.01"))


def test_fixed_fee_does_not_require_maps_without_distance_rules():
    config = _config(
        modalidade_cobranca="fixa",
        taxa_fixa=12.5,
        distancia_maxima_entrega_km=None,
        frete_gratis_acima=None,
        distancia_maxima_frete_gratis_km=None,
    )

    result = quote_delivery(
        config=config,
        tenant=TENANT,
        cidade_destino="Campinas",
        endereco_destino="Rua do Cliente, 20, Campinas, SP",
        subtotal_elegivel=100,
        distance_calculator=lambda *_args: pytest.fail("Maps nao deveria ser chamado"),
    )

    assert result["valor_frete"] == 12.5
    assert result["distancia_km"] is None


def test_fixed_fee_without_delivery_radius_stays_in_store_city():
    config = _config(
        modalidade_cobranca="fixa",
        distancia_maxima_entrega_km=None,
        frete_gratis_acima=None,
        distancia_maxima_frete_gratis_km=None,
    )

    with pytest.raises(DeliveryQuoteError, match="apenas a cidade"):
        quote_delivery(
            config=config,
            tenant=TENANT,
            cidade_destino="Valinhos",
            endereco_destino="Rua do Cliente, 20, Valinhos, SP",
            subtotal_elegivel=100,
        )
