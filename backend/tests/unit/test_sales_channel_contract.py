import os
from types import SimpleNamespace

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from app.services.sales_channel import (
    CANAL_APP,
    CANAL_ECOMMERCE,
    CANAL_LOJA_FISICA,
    benefit_channel_from_sales_channel,
    is_online_sales_channel,
    normalize_online_sales_channel,
    normalize_sales_channel,
    resolve_checkout_sales_channel,
)


def test_normalize_sales_channel_usa_canonicos_do_pdv_app_e_ecommerce():
    assert normalize_sales_channel("pdv") == CANAL_LOJA_FISICA
    assert normalize_sales_channel("loja-fisica") == CANAL_LOJA_FISICA
    assert normalize_sales_channel("balcao") == CANAL_LOJA_FISICA

    assert normalize_sales_channel("app") == CANAL_APP
    assert normalize_sales_channel("aplicativo") == CANAL_APP
    assert normalize_sales_channel("mobile") == CANAL_APP
    assert normalize_sales_channel("app_movel") == CANAL_APP

    assert normalize_sales_channel("web") == CANAL_ECOMMERCE
    assert normalize_sales_channel("site") == CANAL_ECOMMERCE
    assert normalize_sales_channel("e-commerce") == CANAL_ECOMMERCE


def test_normalize_sales_channel_preserva_canais_operacionais_conhecidos():
    assert normalize_sales_channel("app_funcionario") == "app_funcionario"
    assert normalize_sales_channel("banho_tosa") == "banho_tosa"
    assert normalize_sales_channel("veterinario") == "veterinario"


def test_normalize_sales_channel_aplica_default_explicito():
    assert normalize_sales_channel(None) == CANAL_ECOMMERCE
    assert normalize_sales_channel("", default=CANAL_LOJA_FISICA) == CANAL_LOJA_FISICA


def test_resolve_checkout_sales_channel_prioriza_payload_depois_headers():
    assert resolve_checkout_sales_channel(
        SimpleNamespace(origem="app"),
        SimpleNamespace(headers={"X-Client-Channel": "web"}),
    ) == CANAL_APP

    assert resolve_checkout_sales_channel(
        SimpleNamespace(origem=None),
        SimpleNamespace(headers={"X-Client-Channel": "mobile", "X-Canal-Venda": "web"}),
    ) == CANAL_APP

    assert resolve_checkout_sales_channel(
        SimpleNamespace(origem=None),
        SimpleNamespace(headers={"X-Canal-Venda": "site"}),
    ) == CANAL_ECOMMERCE

    assert resolve_checkout_sales_channel(
        SimpleNamespace(origem=None),
        SimpleNamespace(headers={}),
    ) == CANAL_ECOMMERCE

    assert resolve_checkout_sales_channel(
        SimpleNamespace(origem="pdv"),
        SimpleNamespace(headers={}),
    ) == CANAL_ECOMMERCE


def test_online_sales_channel_e_campanhas_usam_mesma_normalizacao():
    assert normalize_online_sales_channel("mobile") == CANAL_APP
    assert normalize_online_sales_channel("app_movel") == CANAL_APP
    assert normalize_online_sales_channel("site") == CANAL_ECOMMERCE
    assert normalize_online_sales_channel("pdv") == CANAL_ECOMMERCE

    assert is_online_sales_channel("mobile") is True
    assert is_online_sales_channel("site") is True
    assert is_online_sales_channel("pdv") is False

    assert benefit_channel_from_sales_channel("mobile") == CANAL_APP
    assert benefit_channel_from_sales_channel("web") == CANAL_ECOMMERCE
    assert benefit_channel_from_sales_channel("pdv") == CANAL_LOJA_FISICA
