from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

DEFAULT_BUNDLE_CODE = "petshop-br"
DEFAULT_BUNDLE_VERSION = "v2"
NAME_RECEITAS_VENDAS = "Receitas de Vendas"
NAME_TAXAS_CARTAO = "Taxas de Cartao"
PRODUCT_REFERENCE_DESCRIPTION = "Produto de referencia para importacao opcional."
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


def _template_item(
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


BUILTIN_TEMPLATE_ITEMS: list[dict[str, Any]] = [
    _template_item(
        "payment_method",
        "payment_cash",
        "Dinheiro",
        {
            "nome": "Dinheiro",
            "tipo": "dinheiro",
            "taxa_percentual": 0,
            "taxa_fixa": 0,
            "prazo_dias": 0,
            "prazo_recebimento": 0,
            "gera_contas_receber": False,
            "split_parcelas": False,
            "requer_nsu": False,
            "ativo": True,
            "permite_parcelamento": False,
            "max_parcelas": 1,
            "parcelas_maximas": 1,
            "icone": "cash",
            "cor": "#22C55E",
        },
        10,
    ),
    _template_item(
        "payment_method",
        "payment_pix",
        "PIX",
        {
            "nome": "PIX",
            "tipo": "pix",
            "taxa_percentual": 0,
            "taxa_fixa": 0,
            "prazo_dias": 0,
            "prazo_recebimento": 0,
            "operadora": "PIX",
            "gera_contas_receber": False,
            "split_parcelas": False,
            "requer_nsu": False,
            "ativo": True,
            "permite_parcelamento": False,
            "max_parcelas": 1,
            "parcelas_maximas": 1,
            "icone": "pix",
            "cor": "#0EA5E9",
        },
        20,
    ),
    _template_item(
        "payment_method",
        "payment_debit",
        "Cartao de debito",
        {
            "nome": "Cartao de debito",
            "tipo": "cartao_debito",
            "taxa_percentual": 2,
            "taxa_fixa": 0,
            "prazo_dias": 1,
            "prazo_recebimento": 1,
            "operadora": None,
            "gera_contas_receber": True,
            "split_parcelas": False,
            "requer_nsu": True,
            "tipo_cartao": "debito",
            "ativo": True,
            "permite_parcelamento": False,
            "max_parcelas": 1,
            "parcelas_maximas": 1,
            "icone": "card",
            "cor": "#3B82F6",
        },
        30,
    ),
    _template_item(
        "payment_method",
        "payment_credit",
        "Cartao de credito",
        {
            "nome": "Cartao de credito",
            "tipo": "cartao_credito",
            "taxa_percentual": 3,
            "taxa_fixa": 0,
            "prazo_dias": 30,
            "prazo_recebimento": 30,
            "operadora": None,
            "gera_contas_receber": True,
            "split_parcelas": True,
            "requer_nsu": True,
            "tipo_cartao": "credito",
            "ativo": True,
            "permite_parcelamento": True,
            "max_parcelas": 12,
            "parcelas_maximas": 12,
            "icone": "card",
            "cor": "#8B5CF6",
        },
        40,
    ),
    _template_item(
        "dre_category",
        "dre_receitas",
        NAME_RECEITAS_VENDAS,
        {
            "nome": NAME_RECEITAS_VENDAS,
            "ordem": 1,
            "natureza": "receita",
            "ativo": True,
        },
        100,
    ),
    _template_item(
        "dre_category",
        "dre_cmv",
        "Custo das Mercadorias Vendidas",
        {
            "nome": "Custo das Mercadorias Vendidas",
            "ordem": 2,
            "natureza": "custo",
            "ativo": True,
        },
        200,
    ),
    _template_item(
        "dre_category",
        "dre_despesas_operacionais",
        "Despesas Operacionais",
        {
            "nome": "Despesas Operacionais",
            "ordem": 3,
            "natureza": "despesa",
            "ativo": True,
        },
        300,
    ),
    _template_item(
        "dre_subcategory",
        "dre_vendas_produtos",
        "Vendas de Produtos",
        {
            "categoria_code": "dre_receitas",
            "nome": "Vendas de Produtos",
            "tipo_custo": "direto",
            "base_rateio": None,
            "escopo_rateio": "ambos",
            "ativo": True,
        },
        110,
    ),
    _template_item(
        "dre_subcategory",
        "dre_vendas_servicos",
        "Vendas de Servicos",
        {
            "categoria_code": "dre_receitas",
            "nome": "Vendas de Servicos",
            "tipo_custo": "direto",
            "base_rateio": None,
            "escopo_rateio": "ambos",
            "ativo": True,
        },
        120,
    ),
    _template_item(
        "dre_subcategory",
        "dre_cmv_produtos",
        "CMV - Produtos",
        {
            "categoria_code": "dre_cmv",
            "nome": "CMV - Produtos",
            "tipo_custo": "direto",
            "base_rateio": None,
            "escopo_rateio": "ambos",
            "ativo": True,
        },
        210,
    ),
    _template_item(
        "dre_subcategory",
        "dre_taxas_cartao",
        NAME_TAXAS_CARTAO,
        {
            "categoria_code": "dre_despesas_operacionais",
            "nome": NAME_TAXAS_CARTAO,
            "tipo_custo": "direto",
            "base_rateio": None,
            "escopo_rateio": "ambos",
            "ativo": True,
        },
        310,
    ),
    _template_item(
        "financial_category",
        "fin_receitas_vendas",
        NAME_RECEITAS_VENDAS,
        {
            "nome": NAME_RECEITAS_VENDAS,
            "tipo": "receita",
            "cor": "#16A34A",
            "icone": "trending-up",
            "descricao": "Receitas operacionais de produtos e servicos.",
            "dre_subcategory_code": "dre_vendas_produtos",
            "tipo_custo": "variavel",
            "ativo": True,
        },
        400,
    ),
    _template_item(
        "financial_category",
        "fin_cmv",
        "CMV",
        {
            "nome": "CMV",
            "tipo": "despesa",
            "cor": "#F97316",
            "icone": "package",
            "descricao": "Custo das mercadorias vendidas.",
            "dre_subcategory_code": "dre_cmv_produtos",
            "tipo_custo": "variavel",
            "ativo": True,
        },
        410,
    ),
    _template_item(
        "expense_type",
        "expense_cmv",
        "CMV",
        {
            "nome": "CMV",
            "e_custo_fixo": False,
            "dre_subcategory_code": "dre_cmv_produtos",
            "ativo": True,
        },
        450,
    ),
    _template_item(
        "expense_type",
        "expense_taxas_cartao",
        NAME_TAXAS_CARTAO,
        {
            "nome": NAME_TAXAS_CARTAO,
            "e_custo_fixo": False,
            "dre_subcategory_code": "dre_taxas_cartao",
            "ativo": True,
        },
        460,
    ),
    _template_item(
        "product_department",
        "dept_produtos",
        "Produtos",
        {
            "nome": "Produtos",
            "descricao": "Produtos comercializados pela loja.",
            "ativo": True,
        },
        500,
    ),
    _template_item(
        "product_category",
        "cat_pet_food",
        "Pet Food",
        {
            "nome": "Pet Food",
            "departamento_code": "dept_produtos",
            "descricao": "Racoes, alimentos e petiscos.",
            "icone": "package",
            "cor": "#2563EB",
            "ordem": 1,
            "ativo": True,
        },
        510,
    ),
    _template_item(
        "product_category",
        "cat_acessorios",
        "Acessorios",
        {
            "nome": "Acessorios",
            "departamento_code": "dept_produtos",
            "descricao": "Acessorios, brinquedos e itens de uso geral.",
            "icone": "shopping-bag",
            "cor": "#9333EA",
            "ordem": 2,
            "ativo": True,
        },
        520,
    ),
    _template_item(
        "product_reference",
        "prod_ref_racao_adulto_1kg",
        "Referencia Racao Adulto 1kg",
        {
            "codigo": "TPL-RACAO-ADULTO-1KG",
            "nome": "Referencia Racao Adulto 1kg",
            "categoria_code": "cat_pet_food",
            "departamento_code": "dept_produtos",
            "tipo": "produto",
            "descricao_curta": PRODUCT_REFERENCE_DESCRIPTION,
            "preco_custo": 0,
            "preco_venda": 0,
            "estoque_atual": 0,
            "estoque_minimo": 0,
            "estoque_maximo": 0,
            "unidade": "UN",
            "condicao": "novo",
            "ativo": False,
            "situacao": False,
        },
        900,
    ),
    _template_item(
        "product_reference",
        "prod_ref_petisco_100g",
        "Referencia Petisco 100g",
        {
            "codigo": "TPL-PETISCO-100G",
            "nome": "Referencia Petisco 100g",
            "categoria_code": "cat_pet_food",
            "departamento_code": "dept_produtos",
            "tipo": "produto",
            "descricao_curta": PRODUCT_REFERENCE_DESCRIPTION,
            "preco_custo": 0,
            "preco_venda": 0,
            "estoque_atual": 0,
            "estoque_minimo": 0,
            "estoque_maximo": 0,
            "unidade": "UN",
            "condicao": "novo",
            "ativo": False,
            "situacao": False,
        },
        910,
    ),
    _template_item(
        "product_reference",
        "prod_ref_brinquedo",
        "Referencia Brinquedo",
        {
            "codigo": "TPL-BRINQUEDO",
            "nome": "Referencia Brinquedo",
            "categoria_code": "cat_acessorios",
            "departamento_code": "dept_produtos",
            "tipo": "produto",
            "descricao_curta": PRODUCT_REFERENCE_DESCRIPTION,
            "preco_custo": 0,
            "preco_venda": 0,
            "estoque_atual": 0,
            "estoque_minimo": 0,
            "estoque_maximo": 0,
            "unidade": "UN",
            "condicao": "novo",
            "ativo": False,
            "situacao": False,
        },
        920,
    ),
]


# Base financeira v2: plano inicial suficientemente completo para o tenant
# operar e classificar a DRE desde o primeiro dia, sem copiar movimentacoes,
# valores ou dados privados de outra empresa.
_DRE_CATEGORY_TEMPLATES = (
    ("dre_outras_receitas", "Outras Receitas", "receita", 2),
    ("dre_deducoes_receita", "Deduções da Receita", "despesa", 3),
    ("dre_pessoal", "Despesas com Pessoal", "despesa", 6),
    ("dre_ocupacao", "Despesas de Ocupação", "despesa", 7),
    ("dre_comercial", "Despesas Comerciais", "despesa", 8),
    ("dre_administrativas", "Despesas Administrativas", "despesa", 9),
    ("dre_veiculos", "Despesas com Veículos e Logística", "despesa", 10),
    ("dre_tributos", "Tributos", "despesa", 11),
    ("dre_financeiras", "Despesas Financeiras", "despesa", 12),
)

for template_code, name, nature, order in _DRE_CATEGORY_TEMPLATES:
    BUILTIN_TEMPLATE_ITEMS.append(
        _template_item(
            "dre_category",
            template_code,
            name,
            {"nome": name, "ordem": order, "natureza": nature, "ativo": True},
            100 + (order * 100),
        )
    )


_DRE_SUBCATEGORY_TEMPLATES = (
    ("dre_receitas_financeiras", "dre_outras_receitas", "Receitas Financeiras", "direto", None),
    ("dre_outras_receitas_operacionais", "dre_outras_receitas", "Outras Receitas Operacionais", "direto", None),
    ("dre_devolucoes", "dre_deducoes_receita", "Devoluções e Cancelamentos", "direto", None),
    ("dre_descontos_concedidos", "dre_deducoes_receita", "Descontos Concedidos", "direto", None),
    ("dre_cmv_servicos", "dre_cmv", "CMV - Materiais e Serviços", "direto", None),
    ("dre_fretes_compras", "dre_cmv", "Fretes sobre Compras", "direto", None),
    ("dre_comissoes_vendas", "dre_despesas_operacionais", "Comissões de Vendas", "direto", None),
    ("dre_embalagens", "dre_despesas_operacionais", "Embalagens", "direto", None),
    ("dre_frete_operacional", "dre_despesas_operacionais", "Fretes e Entregas", "direto", None),
    ("dre_salarios_encargos", "dre_pessoal", "Salários e Encargos", "indireto_rateavel", "faturamento"),
    ("dre_prolabore", "dre_pessoal", "Pró-Labore", "corporativo", None),
    ("dre_beneficios", "dre_pessoal", "Benefícios e Treinamentos", "indireto_rateavel", "faturamento"),
    ("dre_aluguel", "dre_ocupacao", "Aluguel e Condomínio", "indireto_rateavel", "faturamento"),
    ("dre_energia", "dre_ocupacao", "Energia Elétrica", "indireto_rateavel", "faturamento"),
    ("dre_agua", "dre_ocupacao", "Água e Esgoto", "indireto_rateavel", "faturamento"),
    ("dre_internet", "dre_ocupacao", "Internet e Telefonia", "indireto_rateavel", "faturamento"),
    ("dre_limpeza", "dre_ocupacao", "Limpeza e Conservação", "indireto_rateavel", "faturamento"),
    ("dre_manutencao_predial", "dre_ocupacao", "Manutenção Predial", "indireto_rateavel", "faturamento"),
    ("dre_seguranca", "dre_ocupacao", "Segurança e Alarme", "indireto_rateavel", "faturamento"),
    ("dre_marketing", "dre_comercial", "Marketing e Publicidade", "indireto_rateavel", "faturamento"),
    ("dre_fidelidade", "dre_comercial", "Fidelidade, Brindes e Eventos", "indireto_rateavel", "faturamento"),
    ("dre_contabilidade", "dre_administrativas", "Contabilidade e Assessoria", "corporativo", None),
    ("dre_software", "dre_administrativas", "Softwares e Sistemas", "corporativo", None),
    ("dre_material_escritorio", "dre_administrativas", "Material de Escritório e Limpeza", "corporativo", None),
    ("dre_seguros", "dre_administrativas", "Seguros e Licenças", "corporativo", None),
    ("dre_combustivel", "dre_veiculos", "Combustível", "indireto_rateavel", "faturamento"),
    ("dre_manutencao_veiculos", "dre_veiculos", "Manutenção de Veículos", "indireto_rateavel", "faturamento"),
    ("dre_logistica", "dre_veiculos", "Logística, Pedágios e Estacionamento", "indireto_rateavel", "faturamento"),
    ("dre_simples_das", "dre_tributos", "Simples Nacional / DAS", "corporativo", None),
    ("dre_impostos_vendas", "dre_tributos", "Impostos sobre Vendas", "direto", None),
    ("dre_tarifas_bancarias", "dre_financeiras", "Tarifas Bancárias", "corporativo", None),
    ("dre_juros_multas", "dre_financeiras", "Juros e Multas", "corporativo", None),
    ("dre_outros_fixos", "dre_administrativas", "Outros Custos Fixos", "corporativo", None),
    ("dre_outros_variaveis", "dre_despesas_operacionais", "Outros Custos Variáveis", "direto", None),
)

for index, (template_code, category_code, name, cost_type, allocation_base) in enumerate(
    _DRE_SUBCATEGORY_TEMPLATES,
    start=1,
):
    BUILTIN_TEMPLATE_ITEMS.append(
        _template_item(
            "dre_subcategory",
            template_code,
            name,
            {
                "categoria_code": category_code,
                "nome": name,
                "tipo_custo": cost_type,
                "base_rateio": allocation_base,
                "escopo_rateio": "ambos",
                "ativo": True,
            },
            1300 + index,
        )
    )


_FINANCIAL_CATEGORY_TEMPLATES = (
    ("fin_vendas_servicos", "Vendas de Serviços", "receita", "#0D9488", "briefcase", "dre_vendas_servicos", "variavel"),
    ("fin_receitas_financeiras", "Receitas Financeiras", "receita", "#16A34A", "landmark", "dre_receitas_financeiras", "variavel"),
    ("fin_outras_receitas", "Outras Receitas", "receita", "#22C55E", "circle-plus", "dre_outras_receitas_operacionais", "variavel"),
    ("fin_devolucoes", "Devoluções e Cancelamentos", "despesa", "#DC2626", "undo", "dre_devolucoes", "variavel"),
    ("fin_descontos", "Descontos Concedidos", "despesa", "#EA580C", "badge-percent", "dre_descontos_concedidos", "variavel"),
    ("fin_fretes_compras", "Fretes sobre Compras", "despesa", "#0891B2", "truck", "dre_fretes_compras", "variavel"),
    ("fin_taxas_cartao", "Taxas de Cartão", "despesa", "#7C3AED", "credit-card", "dre_taxas_cartao", "variavel"),
    ("fin_comissoes", "Comissões de Vendas", "despesa", "#DB2777", "users", "dre_comissoes_vendas", "variavel"),
    ("fin_embalagens", "Embalagens", "despesa", "#D97706", "package", "dre_embalagens", "variavel"),
    ("fin_salarios", "Salários e Encargos", "despesa", "#4F46E5", "users", "dre_salarios_encargos", "fixo"),
    ("fin_prolabore", "Pró-Labore", "despesa", "#4338CA", "user-round", "dre_prolabore", "fixo"),
    ("fin_aluguel", "Aluguel e Condomínio", "despesa", "#64748B", "store", "dre_aluguel", "fixo"),
    ("fin_energia", "Energia Elétrica", "despesa", "#CA8A04", "zap", "dre_energia", "fixo"),
    ("fin_agua", "Água e Esgoto", "despesa", "#0284C7", "droplets", "dre_agua", "fixo"),
    ("fin_internet", "Internet e Telefonia", "despesa", "#2563EB", "wifi", "dre_internet", "fixo"),
    ("fin_marketing", "Marketing e Publicidade", "despesa", "#DB2777", "megaphone", "dre_marketing", "ambos"),
    ("fin_contabilidade", "Contabilidade e Assessoria", "despesa", "#475569", "calculator", "dre_contabilidade", "fixo"),
    ("fin_softwares", "Softwares e Sistemas", "despesa", "#6366F1", "monitor", "dre_software", "fixo"),
    ("fin_seguros", "Seguros e Licenças", "despesa", "#0F766E", "shield", "dre_seguros", "fixo"),
    ("fin_combustivel", "Combustível e Veículos", "despesa", "#B45309", "car", "dre_combustivel", "variavel"),
    ("fin_impostos", "Impostos / DAS", "despesa", "#991B1B", "landmark", "dre_simples_das", "fixo"),
    ("fin_tarifas_bancarias", "Tarifas Bancárias", "despesa", "#334155", "landmark", "dre_tarifas_bancarias", "variavel"),
    ("fin_juros_multas", "Juros e Multas", "despesa", "#BE123C", "triangle-alert", "dre_juros_multas", "variavel"),
    ("fin_outros_fixos", "Outros Custos Fixos", "despesa", "#78716C", "circle-ellipsis", "dre_outros_fixos", "fixo"),
    ("fin_outros_variaveis", "Outros Custos Variáveis", "despesa", "#A16207", "circle-ellipsis", "dre_outros_variaveis", "variavel"),
)

for index, (template_code, name, kind, color, icon, dre_code, cost_kind) in enumerate(
    _FINANCIAL_CATEGORY_TEMPLATES,
    start=1,
):
    BUILTIN_TEMPLATE_ITEMS.append(
        _template_item(
            "financial_category",
            template_code,
            name,
            {
                "nome": name,
                "tipo": kind,
                "cor": color,
                "icone": icon,
                "descricao": f"Classificação padrão: {name}.",
                "dre_subcategory_code": dre_code,
                "tipo_custo": cost_kind,
                "ativo": True,
            },
            1500 + index,
        )
    )


_EXPENSE_TYPE_TEMPLATES = (
    ("expense_rent", "Aluguel", True, "dre_aluguel"),
    ("expense_payroll", "Salários e Encargos", True, "dre_salarios_encargos"),
    ("expense_das", "Impostos / DAS Simples Nacional", True, "dre_simples_das"),
    ("expense_energy", "Energia Elétrica", True, "dre_energia"),
    ("expense_phone", "Internet / Telefone", True, "dre_internet"),
    ("expense_water", "Água", True, "dre_agua"),
    ("expense_accounting", "Contador / Assessoria Contábil", True, "dre_contabilidade"),
    ("expense_software", "Sistema / Software", True, "dre_software"),
    ("expense_insurance", "Seguro", True, "dre_seguros"),
    ("expense_fixed_marketing", "Marketing / Publicidade Fixo", True, "dre_marketing"),
    ("expense_resale_products", "Produto para Revenda", False, "dre_cmv_produtos"),
    ("expense_purchase_freight", "Frete de Compra", False, "dre_fretes_compras"),
    ("expense_sales_commission", "Comissões de Vendas", False, "dre_comissoes_vendas"),
    ("expense_packaging", "Embalagens", False, "dre_embalagens"),
    ("expense_performance_marketing", "Marketing / Anúncios por Resultado", False, "dre_marketing"),
    ("expense_other_variable", "Outros Custos Variáveis", False, "dre_outros_variaveis"),
    ("expense_other_fixed", "Outros Custos Fixos", True, "dre_outros_fixos"),
)

for index, (template_code, name, is_fixed, dre_code) in enumerate(
    _EXPENSE_TYPE_TEMPLATES,
    start=1,
):
    BUILTIN_TEMPLATE_ITEMS.append(
        _template_item(
            "expense_type",
            template_code,
            name,
            {
                "nome": name,
                "e_custo_fixo": is_fixed,
                "dre_subcategory_code": dre_code,
                "ativo": True,
            },
            1600 + index,
        )
    )

BUILTIN_TEMPLATE_ITEMS.extend(
    [
        _template_item(
            "bank_account",
            "bank_cash_register",
            "Caixa",
            {
                "nome": "Caixa",
                "tipo": "caixa_fisico",
                "banco": None,
                "agencia": None,
                "conta": None,
                "saldo_inicial": 0,
                "saldo_atual": 0,
                "cor": "#22C55E",
                "icone": "banknote",
                "instituicao_bancaria": False,
                "ativa": True,
                "observacoes": "Conta padrao para recebimentos em dinheiro.",
            },
            45,
        ),
        _template_item(
            "bank_account",
            "bank_main_account",
            "Conta Bancaria Principal",
            {
                "nome": "Conta Bancaria Principal",
                "tipo": "corrente",
                "banco": None,
                "agencia": None,
                "conta": None,
                "saldo_inicial": 0,
                "saldo_atual": 0,
                "cor": "#2563EB",
                "icone": "landmark",
                "instituicao_bancaria": True,
                "ativa": True,
                "observacoes": "Conta bancaria inicial para configurar depois.",
            },
            46,
        ),
        _template_item(
            "pet_species",
            "species_dog",
            "Cao",
            {"nome": "Cao", "ativo": True},
            50,
        ),
        _template_item(
            "pet_species",
            "species_cat",
            "Gato",
            {"nome": "Gato", "ativo": True},
            51,
        ),
        _template_item(
            "pet_breed",
            "breed_dog_srd",
            "SRD - Cao",
            {
                "nome": "SRD",
                "species_code": "species_dog",
                "especie": "Cao",
                "ativo": True,
            },
            60,
        ),
        _template_item(
            "pet_breed",
            "breed_cat_srd",
            "SRD - Gato",
            {
                "nome": "SRD",
                "species_code": "species_cat",
                "especie": "Gato",
                "ativo": True,
            },
            61,
        ),
    ]
)

for index, name in enumerate(
    ("Super Premium", "Premium Special", "Premium", "Standard"),
    start=1,
):
    BUILTIN_TEMPLATE_ITEMS.append(
        _template_item(
            "ration_line",
            f"ration_line_{index}",
            name,
            {"nome": name, "descricao": None, "ordem": index, "ativo": True},
            600 + index,
        )
    )

for index, name in enumerate(
    ("Pequeno", "Medio", "Medio e Grande", "Grande", "Gigante", "Todos"),
    start=1,
):
    BUILTIN_TEMPLATE_ITEMS.append(
        _template_item(
            "animal_size",
            f"animal_size_{index}",
            name,
            {"nome": name, "descricao": None, "ordem": index, "ativo": True},
            620 + index,
        )
    )

for index, name in enumerate(("Filhote", "Adulto", "Senior", "Gestante"), start=1):
    BUILTIN_TEMPLATE_ITEMS.append(
        _template_item(
            "life_stage",
            f"life_stage_{index}",
            name,
            {"nome": name, "descricao": None, "ordem": index, "ativo": True},
            640 + index,
        )
    )

for index, name in enumerate(
    (
        "Obesidade",
        "Light",
        "Hipoalergenico",
        "Sensivel",
        "Digestivo",
        "Urinario",
        "Renal",
        "Articular",
        "Dermatologico",
    ),
    start=1,
):
    BUILTIN_TEMPLATE_ITEMS.append(
        _template_item(
            "treatment_type",
            f"treatment_type_{index}",
            name,
            {"nome": name, "descricao": None, "ordem": index, "ativo": True},
            660 + index,
        )
    )

for index, name in enumerate(
    (
        "Frango",
        "Carne",
        "Peixe",
        "Salmao",
        "Cordeiro",
        "Peru",
        "Porco",
        "Vegetariano",
        "Soja",
        "Mix",
    ),
    start=1,
):
    BUILTIN_TEMPLATE_ITEMS.append(
        _template_item(
            "protein_flavor",
            f"protein_flavor_{index}",
            name,
            {"nome": name, "descricao": None, "ordem": index, "ativo": True},
            680 + index,
        )
    )

for index, weight in enumerate((0.5, 1, 2, 3, 5, 7, 10, 10.1, 15, 20, 25), start=1):
    label = f"{weight:g}kg"
    BUILTIN_TEMPLATE_ITEMS.append(
        _template_item(
            "package_weight",
            f"package_weight_{index}",
            label,
            {"peso_kg": weight, "descricao": label, "ordem": index, "ativo": True},
            700 + index,
        )
    )


_VET_PROCEDURES_PATH = (
    Path(__file__).resolve().parents[1] / "catalogos" / "vet_procedimentos_v1.json"
)
with _VET_PROCEDURES_PATH.open("r", encoding="utf-8") as _vet_procedures_file:
    _VET_PROCEDURES = json.load(_vet_procedures_file)

for index, procedure in enumerate(_VET_PROCEDURES, start=1):
    BUILTIN_TEMPLATE_ITEMS.append(
        _template_item(
            "vet_procedure",
            procedure["code"],
            procedure["name"],
            {
                "nome": procedure["name"],
                "descricao": procedure.get("descricao"),
                "categoria": procedure.get("categoria"),
                "duracao_minutos": procedure.get("duracao_minutos"),
                "requer_anestesia": bool(procedure.get("requer_anestesia", False)),
            },
            1000 + index,
        )
    )
