from datetime import datetime, timezone
from types import SimpleNamespace

from app.integrations.ifood.catalog import build_catalog_item

NOW = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)


def _product(**overrides):
    values = {
        "id": 10,
        "codigo": "PET-10",
        "nome": "Racao Premium 1 kg",
        "codigo_barras": "7891234567890",
        "gtin_ean": None,
        "situacao": True,
        "ativo": True,
        "deleted_at": None,
        "is_parent": False,
        "is_sellable": True,
        "tipo": "produto",
        "anunciar_ecommerce": True,
        "preco_venda": 18,
        "preco_promocional": None,
        "promocao_ativa": False,
        "promocao_inicio": None,
        "promocao_fim": None,
        "preco_ecommerce": 20,
        "preco_ecommerce_promo": 16,
        "preco_ecommerce_promo_inicio": None,
        "preco_ecommerce_promo_fim": None,
        "estoque_atual": 12,
        "descricao_completa": "Alimento completo",
        "descricao_curta": None,
        "departamento": SimpleNamespace(nome="Pet shop"),
        "categoria": SimpleNamespace(nome="Racoes"),
        "subcategoria": "Caes",
        "marca": SimpleNamespace(nome="Marca Boa"),
        "unidade": "UN",
        "volume": 1,
        "imagem_principal": "/uploads/produtos/racao.webp",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_builds_ifood_item_from_ecommerce_channel_with_markup_and_stock_safety():
    result = build_catalog_item(
        _product(),
        source="ecommerce",
        markup_percent=10,
        stock_safety=2.5,
        public_base_url="https://corepet.com.br",
        now=NOW,
    )

    assert result.eligible is True
    assert result.errors == ()
    assert result.payload == {
        "barcode": "7891234567890",
        "name": "Racao Premium 1 kg",
        "plu": "PET-10",
        "active": True,
        "inventory": {"stock": 9.5},
        "details": {
            "categorization": {
                "department": "Pet shop",
                "category": "Racoes",
                "subCategory": "Caes",
            },
            "brand": "Marca Boa",
            "unit": "UN",
            "volume": None,
            "imageUrl": "https://corepet.com.br/uploads/produtos/racao.webp",
            "description": "Alimento completo",
        },
        "prices": {"price": 22.0, "promotionPrice": 17.6},
        "channels": ["ifood-app"],
    }


def test_rejects_product_without_barcode_instead_of_sending_bad_item():
    result = build_catalog_item(
        _product(codigo="", codigo_barras=None, gtin_ean=None),
        source="ecommerce",
        public_base_url="https://corepet.com.br",
        now=NOW,
    )

    assert result.eligible is False
    assert result.payload is None
    assert "EAN ou codigo interno ausente." in result.errors


def test_uses_sku_as_internal_code_when_product_has_no_ean():
    result = build_catalog_item(
        _product(codigo_barras=None, gtin_ean=None),
        source="ecommerce",
        public_base_url="https://corepet.com.br",
        now=NOW,
    )

    assert result.eligible is True
    assert result.payload["barcode"] == "PET-10"
    assert "o SKU sera usado como codigo interno" in result.warnings[0]


def test_erp_source_accepts_product_not_announced_on_ecommerce_and_uses_sale_price():
    result = build_catalog_item(
        _product(anunciar_ecommerce=False, preco_venda=15, preco_ecommerce=99),
        source="erp",
        public_base_url="https://corepet.com.br",
        now=NOW,
    )

    assert result.eligible is True
    assert result.payload["prices"]["price"] == 15.0


def test_ignores_promotion_when_discount_is_not_greater_than_five_percent():
    result = build_catalog_item(
        _product(preco_ecommerce=100, preco_ecommerce_promo=96),
        source="ecommerce",
        public_base_url="https://corepet.com.br",
        now=NOW,
    )

    assert result.eligible is True
    assert result.payload["prices"]["promotionPrice"] is None
    assert "o iFood exige desconto superior a 5%" in result.warnings[0]


def test_never_sends_negative_stock_after_safety_reserve():
    result = build_catalog_item(
        _product(estoque_atual=1),
        source="ecommerce",
        stock_safety=3,
        public_base_url="https://corepet.com.br",
        now=NOW,
    )

    assert result.payload["inventory"]["stock"] == 0.0
