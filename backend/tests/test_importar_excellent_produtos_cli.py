from decimal import Decimal
from pathlib import Path

import importar_excellent_produtos_cli as importer


PAGE_TEXT = """
Relatorio Grade 22/09/2026 - Classificacao: Todas
Codigo Codigo interno Estoque atual Aviso de estoque minimo
Produto
Classificacao NCM
Custo unitario Custo total Valor venda Lucro projetavel
78986964554463 (Principal) 33692 3 | UND 0.0000
PRATO CERAMICA N 9
S/R S/R
R$ 9,60 28.80 R$ 19,00 R$ 28,20
97898969854149 (Principal) PRD00003 139 | UN 0.0000
FORMICIDA FORMIPLUS GEL 10 GR CX 120 UNID
S/R 38089119
R$ 3,56 494.84 R$ 10,90 R$ 1.020,26
Quantidade Total
142
Custo Total
R$ 523,64
"""


def test_parse_page_text_reads_cost_stock_and_summary_tail():
    products = importer.parse_page_text(PAGE_TEXT, page_number=729)

    assert len(products) == 2
    assert products[0].source_code == "78986964554463"
    assert products[0].internal_code == "33692"
    assert products[0].unit == "UND"
    assert products[0].stock == Decimal("3")
    assert products[0].unit_cost == Decimal("9.60")
    assert products[0].sale_price == Decimal("19.00")
    assert products[1].ncm == "38089119"
    assert products[1].projected_profit == Decimal("1020.26")


def test_parse_page_text_falls_back_to_source_code_when_name_is_missing():
    text_value = """
VITALCAN FILHOTES 15 (Principal) S/R 0 | UND 0.0000
S/R
unidade S/R
R$ 133,59 0.00 R$ 219,90 R$ 0,00
"""

    product = importer.parse_page_text(text_value, page_number=1)[0]

    assert product.name == "VITALCAN FILHOTES 15"
    assert product.source_name_missing is True
    assert product.internal_code is None


def test_parse_page_text_accepts_wrapped_product_name():
    text_value = """
7898268380414 (Principal) 123 2 | UND 0.0000
ADUBO ESPECIAL COM COMPOSICAO MUITO LONGA
CONTINUACAO DO NOME NA LINHA SEGUINTE
S/R 31052000
R$ 12,00 24.00 R$ 20,00 R$ 16,00
"""

    product = importer.parse_page_text(text_value, page_number=430)[0]

    assert product.name == (
        "ADUBO ESPECIAL COM COMPOSICAO MUITO LONGA "
        "CONTINUACAO DO NOME NA LINHA SEGUINTE"
    )
    assert product.ncm == "31052000"


def test_choose_skus_uses_source_code_for_duplicate_internal_codes():
    products = importer.parse_page_text(PAGE_TEXT, page_number=1)
    duplicate_internal = [
        importer.ExcellentProduct(**{**products[0].__dict__, "internal_code": "33273"}),
        importer.ExcellentProduct(**{**products[1].__dict__, "internal_code": "33273"}),
    ]

    assert importer.choose_skus(duplicate_internal) == [
        "78986964554463",
        "97898969854149",
    ]


def test_build_product_rows_preserves_scan_code_but_only_valid_gtin_for_matching():
    products = importer.parse_page_text(PAGE_TEXT, page_number=1)
    rows = importer.build_product_rows(
        products,
        tenant_id="11111111-1111-1111-1111-111111111111",
        user_id=42,
    )

    assert rows[0]["codigo"] == "33692"
    assert rows[0]["codigo_barras"] == "78986964554463"
    assert rows[0]["gtin_ean"] == "78986964554463"
    assert rows[0]["preco_custo"] == 9.6
    assert rows[0]["preco_venda"] == 19.0
    assert rows[0]["estoque_atual"] == 3.0
    assert rows[0]["unidade"] == "UN"
    assert rows[0]["anunciar_ecommerce"] is False
    assert rows[0]["anunciar_app"] is False


def test_production_apply_requires_backup_and_explicit_flags():
    source = Path(importer.__file__).read_text(encoding="utf-8")

    assert "--allow-production-apply" in source
    assert "--confirm-production" in source
    assert "--backup-reference" in source
    assert "Produtos anteriores sao arquivados" in source
    assert "db.rollback()" in source


def test_stable_result_compares_planned_and_copied_images_equally():
    common = {
        "active_products_before": 715,
        "existing_sku_collisions": 700,
        "created_products": 3643,
        "product_data": {"products": 3643},
    }
    planned = importer._stable_result(
        {
            **common,
            "base_catalog_enrichment": {
                "dry_run": True,
                "matched_products": 100,
                "compatible_products": 90,
                "incompatible_products": 10,
                "source_ambiguous_gtins": 0,
                "target_ambiguous_gtins": 0,
                "source_invalid_gtins": 5,
                "target_invalid_gtins": 403,
                "would_copy_images": 80,
                "copied_images": 0,
            },
        }
    )
    applied = importer._stable_result(
        {
            **common,
            "base_catalog_enrichment": {
                "dry_run": False,
                "matched_products": 100,
                "compatible_products": 90,
                "incompatible_products": 10,
                "source_ambiguous_gtins": 0,
                "target_ambiguous_gtins": 0,
                "source_invalid_gtins": 5,
                "target_invalid_gtins": 403,
                "would_copy_images": 0,
                "copied_images": 80,
            },
        }
    )

    assert planned == applied
    assert planned["images"] == 80
