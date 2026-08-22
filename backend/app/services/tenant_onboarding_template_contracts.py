from __future__ import annotations

import re
from typing import Any


DEFAULT_BUNDLE_CODE = "petshop-br"
DEFAULT_BUNDLE_VERSION = "v2"
ITEM_INSTALL_TARGET_TABLES = {
    "formas_pagamento",
    "contas_bancarias",
    "especies",
    "racas",
    "linhas_racao",
    "portes_animal",
    "fases_publico",
    "tipos_tratamento",
    "sabores_proteina",
    "apresentacoes_peso",
    "dre_categorias",
    "dre_subcategorias",
    "categorias_financeiras",
    "tipo_despesas",
    "departamentos",
    "categorias",
    "produtos",
    "vet_catalogo_procedimentos",
}
REQUIRED_ONBOARDING_SECTIONS = {
    "payment_methods",
    "bank_accounts",
    "pet_species",
    "pet_breeds",
    "ration_lines",
    "animal_sizes",
    "life_stages",
    "treatment_types",
    "protein_flavors",
    "package_weights",
    "dre_categories",
    "dre_subcategories",
    "financial_categories",
    "expense_types",
    "product_departments",
    "product_categories",
}
REQUIRED_ONBOARDING_TABLES = {
    "payment_methods": ("formas_pagamento",),
    "bank_accounts": ("contas_bancarias",),
    "pet_species": ("especies",),
    "pet_breeds": ("racas", "especies"),
    "ration_lines": ("linhas_racao",),
    "animal_sizes": ("portes_animal",),
    "life_stages": ("fases_publico",),
    "treatment_types": ("tipos_tratamento",),
    "protein_flavors": ("sabores_proteina",),
    "package_weights": ("apresentacoes_peso",),
    "dre_categories": ("dre_categorias",),
    "dre_subcategories": ("dre_subcategorias",),
    "financial_categories": ("categorias_financeiras",),
    "expense_types": ("tipo_despesas",),
    "product_departments": ("departamentos",),
    "product_categories": ("categorias",),
}
REQUIRED_TEMPLATE_ITEM_TYPES = {
    "payment_methods": "payment_method",
    "bank_accounts": "bank_account",
    "pet_species": "pet_species",
    "pet_breeds": "pet_breed",
    "ration_lines": "ration_line",
    "animal_sizes": "animal_size",
    "life_stages": "life_stage",
    "treatment_types": "treatment_type",
    "protein_flavors": "protein_flavor",
    "package_weights": "package_weight",
    "dre_categories": "dre_category",
    "dre_subcategories": "dre_subcategory",
    "financial_categories": "financial_category",
    "expense_types": "expense_type",
    "product_departments": "product_department",
    "product_categories": "product_category",
}
TEMPLATE_INFRA_TABLES = (
    "template_bundles",
    "template_items",
    "tenant_template_installs",
    "tenant_template_item_installs",
)

TIPO_CUSTO_DB_LABELS = {
    "direto": "DIRETO",
    "indireto_rateavel": "INDIRETO_RATEAVEL",
    "corporativo": "CORPORATIVO",
}
BASE_RATEIO_DB_LABELS = {
    "faturamento": "FATURAMENTO",
    "pedidos": "PEDIDOS",
    "percentual": "PERCENTUAL",
    "manual": "MANUAL",
}
ESCOPO_RATEIO_DB_LABELS = {
    "loja_fisica": "LOJA_FISICA",
    "online": "ONLINE",
    "ambos": "AMBOS",
}

INSERT_TABLE_PATTERN = re.compile(
    r"\bINSERT\s+INTO\s+([a-zA-Z_][a-zA-Z0-9_]*)\b",
    re.IGNORECASE,
)


def template_item(
    item_type: str,
    template_code: str,
    name: str,
    payload: dict[str, Any],
    sort_order: int,
) -> dict[str, Any]:
    return {
        "item_type": item_type,
        "template_code": template_code,
        "name": name,
        "payload": payload,
        "sort_order": sort_order,
    }
