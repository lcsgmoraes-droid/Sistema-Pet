from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.template_models import (
    TemplateBundle,
    TemplateItem,
    TenantTemplateInstall,
    TenantTemplateItemInstall,
)
from app.utils.tenant_safe_sql import (
    execute_tenant_safe,
    execute_tenant_safe_scalar,
)


DEFAULT_BUNDLE_CODE = "petshop-br"
DEFAULT_BUNDLE_VERSION = "v1"
NAME_RECEITAS_VENDAS = "Receitas de Vendas"
NAME_TAXAS_CARTAO = "Taxas de Cartao"
PRODUCT_REFERENCE_DESCRIPTION = "Produto de referencia para importacao opcional."
ITEM_INSTALL_TARGET_TABLES = {
    "formas_pagamento",
    "dre_categorias",
    "dre_subcategorias",
    "categorias_financeiras",
    "tipo_despesas",
    "departamentos",
    "categorias",
    "produtos",
}
REQUIRED_ONBOARDING_SECTIONS = {
    "payment_methods",
    "dre_categories",
    "dre_subcategories",
    "financial_categories",
    "expense_types",
    "product_departments",
    "product_categories",
}
REQUIRED_ONBOARDING_TABLES = {
    "payment_methods": ("formas_pagamento",),
    "dre_categories": ("dre_categorias",),
    "dre_subcategories": ("dre_subcategorias",),
    "financial_categories": ("categorias_financeiras",),
    "expense_types": ("tipo_despesas",),
    "product_departments": ("departamentos",),
    "product_categories": ("categorias",),
}
REQUIRED_TEMPLATE_ITEM_TYPES = {
    "payment_methods": "payment_method",
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
        {"nome": NAME_RECEITAS_VENDAS, "ordem": 1, "natureza": "receita", "ativo": True},
        100,
    ),
    _template_item(
        "dre_category",
        "dre_cmv",
        "Custo das Mercadorias Vendidas",
        {"nome": "Custo das Mercadorias Vendidas", "ordem": 2, "natureza": "custo", "ativo": True},
        200,
    ),
    _template_item(
        "dre_category",
        "dre_despesas_operacionais",
        "Despesas Operacionais",
        {"nome": "Despesas Operacionais", "ordem": 3, "natureza": "despesa", "ativo": True},
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
        {"nome": "Produtos", "descricao": "Produtos comercializados pela loja.", "ativo": True},
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


class TenantOnboardingError(RuntimeError):
    pass


@dataclass
class OnboardingResult:
    tenant_id: str
    bundle_code: str
    bundle_version: str
    dry_run: bool
    created: dict[str, int] = field(default_factory=dict)
    skipped: dict[str, int] = field(default_factory=dict)
    would_create: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    template_source: str = "builtin"

    def bump(self, bucket: str, key: str) -> None:
        target = getattr(self, bucket)
        target[key] = target.get(key, 0) + 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "bundle_code": self.bundle_code,
            "bundle_version": self.bundle_version,
            "dry_run": self.dry_run,
            "created": self.created,
            "skipped": self.skipped,
            "would_create": self.would_create,
            "warnings": self.warnings,
            "template_source": self.template_source,
        }


def _enforce_required_onboarding(result: OnboardingResult) -> None:
    missing_sections = sorted(
        section
        for section in REQUIRED_ONBOARDING_SECTIONS
        if result.created.get(section, 0) + result.skipped.get(section, 0) <= 0
    )
    if not missing_sections and not result.warnings:
        return

    details: list[str] = []
    if missing_sections:
        details.append("secoes obrigatorias ausentes: " + ", ".join(missing_sections))
    if result.warnings:
        details.append("avisos: " + " | ".join(result.warnings))
    raise TenantOnboardingError(
        "Onboarding obrigatorio incompleto para novo tenant: " + "; ".join(details)
    )


def _warn_missing_template_infra_for_strict(db: Session, result: OnboardingResult) -> None:
    missing = [table_name for table_name in TEMPLATE_INFRA_TABLES if not _table_exists(db, table_name)]
    if missing:
        result.warnings.append(
            "Infraestrutura de templates ausente para onboarding estrito "
            f"({', '.join(missing)})."
        )


def _normalize_tenant_id(tenant_id: Any) -> str:
    if tenant_id is None or str(tenant_id).strip() == "":
        raise TenantOnboardingError("tenant_id e obrigatorio para onboarding.")
    return str(tenant_id)


def _normalize_user_id(user_id: Any) -> int:
    if user_id is None or str(user_id).strip() == "":
        raise TenantOnboardingError("user_id e obrigatorio para onboarding.")
    return int(user_id)


def _db_enum_label(value: Any, labels: dict[str, str], field_name: str, allow_none: bool = False) -> str | None:
    if value is None:
        if allow_none:
            return None
        raise TenantOnboardingError(f"{field_name} e obrigatorio no template.")
    normalized = str(value).strip()
    if not normalized:
        if allow_none:
            return None
        raise TenantOnboardingError(f"{field_name} e obrigatorio no template.")
    if normalized in labels.values():
        return normalized
    mapped = labels.get(normalized.lower())
    if mapped is None:
        raise TenantOnboardingError(f"{field_name} invalido no template: {value}.")
    return mapped


def _table_exists(db: Session, table_name: str) -> bool:
    return inspect(db.connection()).has_table(table_name)


def _tables_ready_or_warn(
    db: Session,
    result: OnboardingResult,
    section: str,
    table_names: tuple[str, ...],
) -> bool:
    missing = [table_name for table_name in table_names if not _table_exists(db, table_name)]
    if not missing:
        return True

    result.warnings.append(
        f"Onboarding parcial: schema ausente para {section} ({', '.join(missing)})."
    )
    return False


def _template_tables_ready(db: Session) -> bool:
    return _table_exists(db, "template_bundles") and _table_exists(db, "template_items")


def ensure_builtin_templates(db: Session) -> None:
    """Create system-owned builtin templates when template tables exist."""
    if not _template_tables_ready(db):
        return

    bundle = (
        db.query(TemplateBundle)
        .filter(
            TemplateBundle.bundle_code == DEFAULT_BUNDLE_CODE,
            TemplateBundle.version == DEFAULT_BUNDLE_VERSION,
        )
        .first()
    )
    if bundle is None:
        db.add(
            TemplateBundle(
                bundle_code=DEFAULT_BUNDLE_CODE,
                version=DEFAULT_BUNDLE_VERSION,
                name="Pet Shop Brasil",
                description="Pacote padrao inicial para tenants de pet shop.",
                active=True,
            )
        )
        db.flush()

    existing_codes = {
        row[0]
        for row in db.query(TemplateItem.template_code)
        .filter(
            TemplateItem.bundle_code == DEFAULT_BUNDLE_CODE,
            TemplateItem.bundle_version == DEFAULT_BUNDLE_VERSION,
        )
        .all()
    }
    for item in BUILTIN_TEMPLATE_ITEMS:
        if item["template_code"] in existing_codes:
            continue
        db.add(
            TemplateItem(
                bundle_code=DEFAULT_BUNDLE_CODE,
                bundle_version=DEFAULT_BUNDLE_VERSION,
                item_type=item["item_type"],
                template_code=item["template_code"],
                name=item["name"],
                payload=item["payload"],
                sort_order=item["sort_order"],
                active=True,
            )
        )
    db.flush()


def _query_template_items(db: Session, bundle_code: str, bundle_version: str) -> list[dict[str, Any]]:
    rows = (
        db.query(TemplateItem)
        .filter(
            TemplateItem.bundle_code == bundle_code,
            TemplateItem.bundle_version == bundle_version,
            TemplateItem.active == True,
        )
        .order_by(TemplateItem.sort_order.asc(), TemplateItem.id.asc())
        .all()
    )
    return [
        {
            "item_type": row.item_type,
            "template_code": row.template_code,
            "name": row.name,
            "payload": row.payload,
            "sort_order": row.sort_order,
        }
        for row in rows
    ]


def _missing_builtin_template_items(db: Session, bundle_code: str, bundle_version: str) -> list[dict[str, Any]]:
    existing_codes = {
        row[0]
        for row in db.query(TemplateItem.template_code)
        .filter(
            TemplateItem.bundle_code == bundle_code,
            TemplateItem.bundle_version == bundle_version,
        )
        .all()
    }
    return [item for item in BUILTIN_TEMPLATE_ITEMS if item["template_code"] not in existing_codes]


def _combine_template_items(
    db: Session,
    bundle_code: str,
    bundle_version: str,
    items: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], str] | None:
    if bundle_code != DEFAULT_BUNDLE_CODE or bundle_version != DEFAULT_BUNDLE_VERSION:
        return None

    missing_builtin_items = _missing_builtin_template_items(db, bundle_code, bundle_version)
    if not items and not missing_builtin_items:
        return None

    combined = items + missing_builtin_items
    combined.sort(key=lambda item: (int(item.get("sort_order") or 0), item["template_code"]))
    source = "database" if not missing_builtin_items else "database+builtin_pending"
    return combined, source


def _load_template_items(db: Session, bundle_code: str, bundle_version: str) -> tuple[list[dict[str, Any]], str]:
    if _template_tables_ready(db):
        items = _query_template_items(db, bundle_code, bundle_version)
        combined = _combine_template_items(db, bundle_code, bundle_version, items)
        if combined is not None:
            return combined
        if items:
            return items, "database"

    if bundle_code == DEFAULT_BUNDLE_CODE and bundle_version == DEFAULT_BUNDLE_VERSION:
        return list(BUILTIN_TEMPLATE_ITEMS), "builtin"

    raise TenantOnboardingError(
        f"Template bundle nao encontrado: {bundle_code}@{bundle_version}."
    )


def _count_items_by_type(items: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        item_type = str(item.get("item_type") or "")
        counts[item_type] = counts.get(item_type, 0) + 1
    return counts


def _template_codes_by_type(items: list[dict[str, Any]], item_type: str) -> set[str]:
    return {
        str(item.get("template_code"))
        for item in items
        if item.get("item_type") == item_type and item.get("template_code")
    }


def _validate_payload_reference(
    errors: list[str],
    item: dict[str, Any],
    payload_key: str,
    valid_codes: set[str],
    target_label: str,
) -> None:
    payload = item.get("payload") or {}
    reference = payload.get(payload_key)
    template_code = item.get("template_code")
    if not reference:
        errors.append(f"Template {template_code} sem {payload_key}.")
        return
    if str(reference) not in valid_codes:
        errors.append(
            f"Template {template_code} referencia {target_label} inexistente: {reference}."
        )


def _find_template_dependency_errors(
    items: list[dict[str, Any]],
    include_products: bool,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    dre_category_codes = _template_codes_by_type(items, "dre_category")
    dre_subcategory_codes = _template_codes_by_type(items, "dre_subcategory")
    product_department_codes = _template_codes_by_type(items, "product_department")
    product_category_codes = _template_codes_by_type(items, "product_category")

    for item in items:
        item_type = item.get("item_type")
        payload = item.get("payload") or {}
        if item_type == "dre_subcategory":
            _validate_payload_reference(errors, item, "categoria_code", dre_category_codes, "dre_category")
        elif item_type == "expense_type":
            _validate_payload_reference(
                errors,
                item,
                "dre_subcategory_code",
                dre_subcategory_codes,
                "dre_subcategory",
            )
        elif item_type == "financial_category":
            reference = payload.get("dre_subcategory_code")
            if reference and str(reference) not in dre_subcategory_codes:
                errors.append(
                    f"Template {item.get('template_code')} referencia dre_subcategory inexistente: {reference}."
                )
            elif not reference:
                warnings.append(
                    f"Template {item.get('template_code')} sem vinculo DRE opcional."
                )
        elif item_type == "product_category":
            _validate_payload_reference(
                errors,
                item,
                "departamento_code",
                product_department_codes,
                "product_department",
            )
        elif item_type == "product_reference":
            target = errors if include_products else warnings
            _validate_payload_reference(
                target,
                item,
                "departamento_code",
                product_department_codes,
                "product_department",
            )
            _validate_payload_reference(
                target,
                item,
                "categoria_code",
                product_category_codes,
                "product_category",
            )

    return errors, warnings


def validate_onboarding_template_contract(
    db: Session,
    bundle_code: str = DEFAULT_BUNDLE_CODE,
    bundle_version: str = DEFAULT_BUNDLE_VERSION,
    include_products: bool = False,
) -> dict[str, Any]:
    """
    Read-only validation for the global template bundle needed by future tenants.

    This check never creates tenants or tenant-owned rows. It validates the
    template infrastructure, required operational tables and template dependency
    graph before the strict signup onboarding path is exercised.
    """
    missing_template_tables = [
        table_name for table_name in TEMPLATE_INFRA_TABLES if not _table_exists(db, table_name)
    ]
    missing_operational_tables = {
        section: [table_name for table_name in table_names if not _table_exists(db, table_name)]
        for section, table_names in REQUIRED_ONBOARDING_TABLES.items()
    }
    missing_operational_tables = {
        section: missing
        for section, missing in missing_operational_tables.items()
        if missing
    }
    errors: list[str] = []
    items: list[dict[str, Any]] = []
    template_source = "unavailable"

    try:
        items, template_source = _load_template_items(db, bundle_code, bundle_version)
    except TenantOnboardingError as exc:
        errors.append(str(exc))

    counts_by_type = _count_items_by_type(items)
    missing_sections = sorted(
        section
        for section, item_type in REQUIRED_TEMPLATE_ITEM_TYPES.items()
        if counts_by_type.get(item_type, 0) <= 0
    )
    product_reference_count = counts_by_type.get("product_reference", 0)

    seen_codes: dict[str, int] = {}
    for item in items:
        code = str(item.get("template_code") or "")
        seen_codes[code] = seen_codes.get(code, 0) + 1
    duplicate_template_codes = sorted(code for code, count in seen_codes.items() if code and count > 1)

    dependency_errors, dependency_warnings = _find_template_dependency_errors(items, include_products)

    builtin_pending_count = 0
    if _template_tables_ready(db) and bundle_code == DEFAULT_BUNDLE_CODE and bundle_version == DEFAULT_BUNDLE_VERSION:
        builtin_pending_count = len(_missing_builtin_template_items(db, bundle_code, bundle_version))

    ok = not (
        missing_template_tables
        or missing_operational_tables
        or errors
        or missing_sections
        or duplicate_template_codes
        or dependency_errors
    )

    return {
        "ok": ok,
        "mode": "template_contract_check",
        "dry_run": True,
        "bundle_code": bundle_code,
        "bundle_version": bundle_version,
        "include_products": bool(include_products),
        "template_source": template_source,
        "template_item_counts": counts_by_type,
        "required_sections": sorted(REQUIRED_ONBOARDING_SECTIONS),
        "missing_sections": missing_sections,
        "missing_template_tables": missing_template_tables,
        "missing_operational_tables": missing_operational_tables,
        "duplicate_template_codes": duplicate_template_codes,
        "dependency_errors": dependency_errors,
        "dependency_warnings": dependency_warnings,
        "product_reference_count": product_reference_count,
        "builtin_pending_count": builtin_pending_count,
    }


def _items_by_type(items: list[dict[str, Any]], item_type: str) -> list[dict[str, Any]]:
    return [item for item in items if item["item_type"] == item_type]


def _scalar(db: Session, sql: str, params: dict[str, Any], tenant_id: str) -> Any:
    return execute_tenant_safe_scalar(db, sql, params, tenant_id=tenant_id)


def _execute_insert(db: Session, sql: str, params: dict[str, Any], tenant_id: str) -> None:
    execute_tenant_safe(
        db,
        sql,
        params,
        tenant_id=tenant_id,
        require_tenant=False,
    )


def _item_install_tables_ready(db: Session) -> bool:
    return _table_exists(db, "tenant_template_item_installs")


def _ensure_known_target_table(target_table: str) -> None:
    if target_table not in ITEM_INSTALL_TARGET_TABLES:
        raise TenantOnboardingError(f"Tabela alvo de template nao permitida: {target_table}.")


def _get_template_item_install(
    db: Session,
    tenant_id: str,
    result: OnboardingResult,
    item: dict[str, Any],
) -> TenantTemplateItemInstall | None:
    if not _item_install_tables_ready(db):
        return None

    tenant_uuid = uuid.UUID(tenant_id)
    return (
        db.query(TenantTemplateItemInstall)
        .filter(
            TenantTemplateItemInstall.tenant_id == tenant_uuid,
            TenantTemplateItemInstall.bundle_code == result.bundle_code,
            TenantTemplateItemInstall.bundle_version == result.bundle_version,
            TenantTemplateItemInstall.item_type == item["item_type"],
            TenantTemplateItemInstall.template_code == item["template_code"],
        )
        .first()
    )


def _mapped_template_row_id(
    db: Session,
    tenant_id: str,
    result: OnboardingResult,
    item: dict[str, Any],
    target_table: str,
) -> int | None:
    _ensure_known_target_table(target_table)
    install = _get_template_item_install(db, tenant_id, result, item)
    if install is None or install.target_id is None:
        return None
    if install.target_table != target_table:
        result.warnings.append(
            f"Template {item['template_code']} aponta para tabela inesperada: {install.target_table}."
        )
        return None

    existing_id = _scalar(
        db,
        f"""
        SELECT id
        FROM {target_table}
        WHERE {{tenant_filter}}
          AND id = :target_id
        LIMIT 1
        """,
        {"target_id": install.target_id},
        tenant_id,
    )
    if existing_id:
        return int(existing_id)

    result.warnings.append(
        f"Template {item['template_code']} tinha vinculo sem registro alvo em {target_table}."
    )
    return None


def _record_template_item_install(
    db: Session,
    tenant_id: str,
    user_id: int | None,
    result: OnboardingResult,
    item: dict[str, Any],
    target_table: str,
    target_id: Any,
) -> None:
    if result.dry_run or not target_id or not _item_install_tables_ready(db):
        return

    _ensure_known_target_table(target_table)
    tenant_uuid = uuid.UUID(tenant_id)
    install = _get_template_item_install(db, tenant_id, result, item)
    if install is None:
        db.add(
            TenantTemplateItemInstall(
                tenant_id=tenant_uuid,
                bundle_code=result.bundle_code,
                bundle_version=result.bundle_version,
                item_type=item["item_type"],
                template_code=item["template_code"],
                target_table=target_table,
                target_id=int(target_id),
                status="active",
                created_by_user_id=user_id,
            )
        )
    else:
        install.target_table = target_table
        install.target_id = int(target_id)
        install.status = "active"
        install.created_by_user_id = user_id
    db.flush()


def _copy_payment_methods(
    db: Session,
    items: list[dict[str, Any]],
    tenant_id: str,
    user_id: int,
    result: OnboardingResult,
) -> None:
    for item in items:
        payload = item["payload"]
        mapped_id = _mapped_template_row_id(db, tenant_id, result, item, "formas_pagamento")
        if mapped_id:
            result.bump("skipped", "payment_methods")
            continue

        existing_id = _scalar(
            db,
            """
            SELECT id
            FROM formas_pagamento
            WHERE {tenant_filter}
              AND lower(nome) = lower(:nome)
              AND tipo = :tipo
            LIMIT 1
            """,
            {"nome": payload["nome"], "tipo": payload["tipo"]},
            tenant_id,
        )
        if existing_id:
            _record_template_item_install(
                db,
                tenant_id,
                user_id,
                result,
                item,
                "formas_pagamento",
                existing_id,
            )
            result.bump("skipped", "payment_methods")
            continue
        if result.dry_run:
            result.bump("would_create", "payment_methods")
            continue

        params = {
            **payload,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "taxa_percentual": payload.get("taxa_percentual", 0),
            "taxa_fixa": payload.get("taxa_fixa", 0),
            "prazo_dias": payload.get("prazo_dias", 0),
            "prazo_recebimento": payload.get("prazo_recebimento", payload.get("prazo_dias", 0)),
            "operadora": payload.get("operadora"),
            "gera_contas_receber": bool(payload.get("gera_contas_receber", False)),
            "split_parcelas": bool(payload.get("split_parcelas", False)),
            "requer_nsu": bool(payload.get("requer_nsu", False)),
            "tipo_cartao": payload.get("tipo_cartao"),
            "bandeira": payload.get("bandeira"),
            "ativo": bool(payload.get("ativo", True)),
            "permite_parcelamento": bool(payload.get("permite_parcelamento", False)),
            "max_parcelas": payload.get("max_parcelas", 1),
            "parcelas_maximas": payload.get("parcelas_maximas", payload.get("max_parcelas", 1)),
            "icone": payload.get("icone"),
            "cor": payload.get("cor"),
        }
        _execute_insert(
            db,
            """
            INSERT INTO formas_pagamento (
                tenant_id, user_id, nome, tipo, taxa_percentual, taxa_fixa,
                prazo_dias, prazo_recebimento, operadora, gera_contas_receber,
                split_parcelas, requer_nsu, tipo_cartao, bandeira, ativo,
                permite_parcelamento, max_parcelas, parcelas_maximas, icone, cor,
                created_at, updated_at
            ) VALUES (
                :tenant_id, :user_id, :nome, :tipo, :taxa_percentual, :taxa_fixa,
                :prazo_dias, :prazo_recebimento, :operadora, :gera_contas_receber,
                :split_parcelas, :requer_nsu, :tipo_cartao, :bandeira, :ativo,
                :permite_parcelamento, :max_parcelas, :parcelas_maximas, :icone, :cor,
                CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            """,
            params,
            tenant_id,
        )
        created_id = _scalar(
            db,
            """
            SELECT id
            FROM formas_pagamento
            WHERE {tenant_filter}
              AND lower(nome) = lower(:nome)
              AND tipo = :tipo
            LIMIT 1
            """,
            {"nome": payload["nome"], "tipo": payload["tipo"]},
            tenant_id,
        )
        _record_template_item_install(
            db,
            tenant_id,
            user_id,
            result,
            item,
            "formas_pagamento",
            created_id,
        )
        result.bump("created", "payment_methods")


def _copy_dre_categories(
    db: Session,
    items: list[dict[str, Any]],
    tenant_id: str,
    result: OnboardingResult,
) -> dict[str, int]:
    category_ids: dict[str, int] = {}
    for item in items:
        payload = item["payload"]
        mapped_id = _mapped_template_row_id(db, tenant_id, result, item, "dre_categorias")
        if mapped_id:
            category_ids[item["template_code"]] = mapped_id
            result.bump("skipped", "dre_categories")
            continue

        existing_id = _scalar(
            db,
            """
            SELECT id
            FROM dre_categorias
            WHERE {tenant_filter}
              AND lower(nome) = lower(:nome)
            LIMIT 1
            """,
            {"nome": payload["nome"]},
            tenant_id,
        )
        if existing_id:
            category_ids[item["template_code"]] = int(existing_id)
            _record_template_item_install(
                db,
                tenant_id,
                None,
                result,
                item,
                "dre_categorias",
                existing_id,
            )
            result.bump("skipped", "dre_categories")
            continue
        if result.dry_run:
            category_ids[item["template_code"]] = -int(item.get("sort_order") or 1)
            result.bump("would_create", "dre_categories")
            continue

        _execute_insert(
            db,
            """
            INSERT INTO dre_categorias (
                tenant_id, nome, ordem, natureza, ativo, created_at, updated_at
            ) VALUES (
                :tenant_id, :nome, :ordem, :natureza, :ativo, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            """,
            {
                "tenant_id": tenant_id,
                "nome": payload["nome"],
                "ordem": payload.get("ordem", 0),
                "natureza": payload["natureza"],
                "ativo": bool(payload.get("ativo", True)),
            },
            tenant_id,
        )
        created_id = _scalar(
            db,
            """
            SELECT id
            FROM dre_categorias
            WHERE {tenant_filter}
              AND lower(nome) = lower(:nome)
            LIMIT 1
            """,
            {"nome": payload["nome"]},
            tenant_id,
        )
        category_ids[item["template_code"]] = int(created_id)
        _record_template_item_install(
            db,
            tenant_id,
            None,
            result,
            item,
            "dre_categorias",
            created_id,
        )
        result.bump("created", "dre_categories")
    return category_ids


def _copy_dre_subcategories(
    db: Session,
    items: list[dict[str, Any]],
    tenant_id: str,
    result: OnboardingResult,
    category_ids: dict[str, int],
) -> dict[str, int]:
    subcategory_ids: dict[str, int] = {}
    for item in items:
        payload = item["payload"]
        category_code = payload["categoria_code"]
        category_id = category_ids.get(category_code)
        if not category_id:
            result.warnings.append(f"Categoria DRE ausente para subcategoria {item['template_code']}.")
            continue

        mapped_id = _mapped_template_row_id(db, tenant_id, result, item, "dre_subcategorias")
        if mapped_id:
            subcategory_ids[item["template_code"]] = mapped_id
            result.bump("skipped", "dre_subcategories")
            continue

        existing_id = _scalar(
            db,
            """
            SELECT id
            FROM dre_subcategorias
            WHERE {tenant_filter}
              AND categoria_id = :categoria_id
              AND lower(nome) = lower(:nome)
            LIMIT 1
            """,
            {"categoria_id": category_id, "nome": payload["nome"]},
            tenant_id,
        )
        if existing_id:
            subcategory_ids[item["template_code"]] = int(existing_id)
            _record_template_item_install(
                db,
                tenant_id,
                None,
                result,
                item,
                "dre_subcategorias",
                existing_id,
            )
            result.bump("skipped", "dre_subcategories")
            continue
        if result.dry_run:
            subcategory_ids[item["template_code"]] = -int(item.get("sort_order") or 1)
            result.bump("would_create", "dre_subcategories")
            continue

        _execute_insert(
            db,
            """
            INSERT INTO dre_subcategorias (
                tenant_id, categoria_id, nome, tipo_custo, base_rateio,
                escopo_rateio, ativo, created_at, updated_at
            ) VALUES (
                :tenant_id, :categoria_id, :nome, :tipo_custo, :base_rateio,
                :escopo_rateio, :ativo, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            """,
            {
                "tenant_id": tenant_id,
                "categoria_id": category_id,
                "nome": payload["nome"],
                "tipo_custo": _db_enum_label(payload["tipo_custo"], TIPO_CUSTO_DB_LABELS, "tipo_custo"),
                "base_rateio": _db_enum_label(
                    payload.get("base_rateio"),
                    BASE_RATEIO_DB_LABELS,
                    "base_rateio",
                    allow_none=True,
                ),
                "escopo_rateio": _db_enum_label(
                    payload.get("escopo_rateio", "ambos"),
                    ESCOPO_RATEIO_DB_LABELS,
                    "escopo_rateio",
                ),
                "ativo": bool(payload.get("ativo", True)),
            },
            tenant_id,
        )
        created_id = _scalar(
            db,
            """
            SELECT id
            FROM dre_subcategorias
            WHERE {tenant_filter}
              AND categoria_id = :categoria_id
              AND lower(nome) = lower(:nome)
            LIMIT 1
            """,
            {"categoria_id": category_id, "nome": payload["nome"]},
            tenant_id,
        )
        subcategory_ids[item["template_code"]] = int(created_id)
        _record_template_item_install(
            db,
            tenant_id,
            None,
            result,
            item,
            "dre_subcategorias",
            created_id,
        )
        result.bump("created", "dre_subcategories")
    return subcategory_ids


def _copy_expense_types(
    db: Session,
    items: list[dict[str, Any]],
    tenant_id: str,
    result: OnboardingResult,
    subcategory_ids: dict[str, int],
) -> None:
    for item in items:
        payload = item["payload"]
        mapped_id = _mapped_template_row_id(db, tenant_id, result, item, "tipo_despesas")
        if mapped_id:
            result.bump("skipped", "expense_types")
            continue

        existing_id = _scalar(
            db,
            """
            SELECT id
            FROM tipo_despesas
            WHERE {tenant_filter}
              AND lower(nome) = lower(:nome)
            LIMIT 1
            """,
            {"nome": payload["nome"]},
            tenant_id,
        )
        if existing_id:
            _record_template_item_install(
                db,
                tenant_id,
                None,
                result,
                item,
                "tipo_despesas",
                existing_id,
            )
            result.bump("skipped", "expense_types")
            continue
        if result.dry_run:
            result.bump("would_create", "expense_types")
            continue

        dre_subcategory_id = subcategory_ids.get(payload.get("dre_subcategory_code"))
        if not dre_subcategory_id:
            result.warnings.append(f"Subcategoria DRE ausente para tipo de despesa {item['template_code']}.")
            continue

        _execute_insert(
            db,
            """
            INSERT INTO tipo_despesas (
                tenant_id, nome, e_custo_fixo, dre_subcategoria_id, ativo,
                created_at, updated_at
            ) VALUES (
                :tenant_id, :nome, :e_custo_fixo, :dre_subcategoria_id, :ativo,
                CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            """,
            {
                "tenant_id": tenant_id,
                "nome": payload["nome"],
                "e_custo_fixo": bool(payload.get("e_custo_fixo", True)),
                "dre_subcategoria_id": dre_subcategory_id,
                "ativo": bool(payload.get("ativo", True)),
            },
            tenant_id,
        )
        created_id = _scalar(
            db,
            """
            SELECT id
            FROM tipo_despesas
            WHERE {tenant_filter}
              AND lower(nome) = lower(:nome)
            LIMIT 1
            """,
            {"nome": payload["nome"]},
            tenant_id,
        )
        _record_template_item_install(
            db,
            tenant_id,
            None,
            result,
            item,
            "tipo_despesas",
            created_id,
        )
        result.bump("created", "expense_types")


def _copy_financial_categories(
    db: Session,
    items: list[dict[str, Any]],
    tenant_id: str,
    user_id: int,
    result: OnboardingResult,
    subcategory_ids: dict[str, int],
) -> None:
    for item in items:
        payload = item["payload"]
        mapped_id = _mapped_template_row_id(db, tenant_id, result, item, "categorias_financeiras")
        if mapped_id:
            result.bump("skipped", "financial_categories")
            continue

        existing_id = _scalar(
            db,
            """
            SELECT id
            FROM categorias_financeiras
            WHERE {tenant_filter}
              AND lower(nome) = lower(:nome)
              AND tipo = :tipo
            LIMIT 1
            """,
            {"nome": payload["nome"], "tipo": payload["tipo"]},
            tenant_id,
        )
        if existing_id:
            _record_template_item_install(
                db,
                tenant_id,
                user_id,
                result,
                item,
                "categorias_financeiras",
                existing_id,
            )
            result.bump("skipped", "financial_categories")
            continue
        if result.dry_run:
            result.bump("would_create", "financial_categories")
            continue

        _execute_insert(
            db,
            """
            INSERT INTO categorias_financeiras (
                tenant_id, user_id, nome, tipo, cor, icone, descricao,
                ativo, dre_subcategoria_id, tipo_custo, created_at, updated_at
            ) VALUES (
                :tenant_id, :user_id, :nome, :tipo, :cor, :icone, :descricao,
                :ativo, :dre_subcategoria_id, :tipo_custo, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            """,
            {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "nome": payload["nome"],
                "tipo": payload["tipo"],
                "cor": payload.get("cor"),
                "icone": payload.get("icone"),
                "descricao": payload.get("descricao"),
                "ativo": bool(payload.get("ativo", True)),
                "dre_subcategoria_id": subcategory_ids.get(payload.get("dre_subcategory_code")),
                "tipo_custo": payload.get("tipo_custo"),
            },
            tenant_id,
        )
        created_id = _scalar(
            db,
            """
            SELECT id
            FROM categorias_financeiras
            WHERE {tenant_filter}
              AND lower(nome) = lower(:nome)
              AND tipo = :tipo
            LIMIT 1
            """,
            {"nome": payload["nome"], "tipo": payload["tipo"]},
            tenant_id,
        )
        _record_template_item_install(
            db,
            tenant_id,
            user_id,
            result,
            item,
            "categorias_financeiras",
            created_id,
        )
        result.bump("created", "financial_categories")


def _copy_product_departments(
    db: Session,
    items: list[dict[str, Any]],
    tenant_id: str,
    user_id: int,
    result: OnboardingResult,
) -> dict[str, int]:
    department_ids: dict[str, int] = {}
    for item in items:
        payload = item["payload"]
        mapped_id = _mapped_template_row_id(db, tenant_id, result, item, "departamentos")
        if mapped_id:
            department_ids[item["template_code"]] = mapped_id
            result.bump("skipped", "product_departments")
            continue

        existing_id = _scalar(
            db,
            """
            SELECT id
            FROM departamentos
            WHERE {tenant_filter}
              AND lower(nome) = lower(:nome)
            LIMIT 1
            """,
            {"nome": payload["nome"]},
            tenant_id,
        )
        if existing_id:
            department_ids[item["template_code"]] = int(existing_id)
            _record_template_item_install(
                db,
                tenant_id,
                user_id,
                result,
                item,
                "departamentos",
                existing_id,
            )
            result.bump("skipped", "product_departments")
            continue
        if result.dry_run:
            department_ids[item["template_code"]] = -int(item.get("sort_order") or 1)
            result.bump("would_create", "product_departments")
            continue

        _execute_insert(
            db,
            """
            INSERT INTO departamentos (
                tenant_id, user_id, nome, descricao, ativo, created_at, updated_at
            ) VALUES (
                :tenant_id, :user_id, :nome, :descricao, :ativo, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            """,
            {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "nome": payload["nome"],
                "descricao": payload.get("descricao"),
                "ativo": bool(payload.get("ativo", True)),
            },
            tenant_id,
        )
        created_id = _scalar(
            db,
            """
            SELECT id
            FROM departamentos
            WHERE {tenant_filter}
              AND lower(nome) = lower(:nome)
            LIMIT 1
            """,
            {"nome": payload["nome"]},
            tenant_id,
        )
        department_ids[item["template_code"]] = int(created_id)
        _record_template_item_install(
            db,
            tenant_id,
            user_id,
            result,
            item,
            "departamentos",
            created_id,
        )
        result.bump("created", "product_departments")
    return department_ids


def _copy_product_categories(
    db: Session,
    items: list[dict[str, Any]],
    tenant_id: str,
    user_id: int,
    result: OnboardingResult,
    department_ids: dict[str, int],
) -> dict[str, int]:
    category_ids: dict[str, int] = {}
    for item in items:
        payload = item["payload"]
        department_id = department_ids.get(payload.get("departamento_code"))
        mapped_id = _mapped_template_row_id(db, tenant_id, result, item, "categorias")
        if mapped_id:
            category_ids[item["template_code"]] = mapped_id
            result.bump("skipped", "product_categories")
            continue

        existing_id = _scalar(
            db,
            """
            SELECT id
            FROM categorias
            WHERE {tenant_filter}
              AND lower(nome) = lower(:nome)
            LIMIT 1
            """,
            {"nome": payload["nome"]},
            tenant_id,
        )
        if existing_id:
            category_ids[item["template_code"]] = int(existing_id)
            _record_template_item_install(
                db,
                tenant_id,
                user_id,
                result,
                item,
                "categorias",
                existing_id,
            )
            result.bump("skipped", "product_categories")
            continue
        if result.dry_run:
            category_ids[item["template_code"]] = -int(item.get("sort_order") or 1)
            result.bump("would_create", "product_categories")
            continue

        _execute_insert(
            db,
            """
            INSERT INTO categorias (
                tenant_id, user_id, nome, departamento_id, descricao, icone,
                cor, ordem, ativo, created_at, updated_at
            ) VALUES (
                :tenant_id, :user_id, :nome, :departamento_id, :descricao, :icone,
                :cor, :ordem, :ativo, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            """,
            {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "nome": payload["nome"],
                "departamento_id": department_id,
                "descricao": payload.get("descricao"),
                "icone": payload.get("icone"),
                "cor": payload.get("cor"),
                "ordem": payload.get("ordem", 0),
                "ativo": bool(payload.get("ativo", True)),
            },
            tenant_id,
        )
        created_id = _scalar(
            db,
            """
            SELECT id
            FROM categorias
            WHERE {tenant_filter}
              AND lower(nome) = lower(:nome)
            LIMIT 1
            """,
            {"nome": payload["nome"]},
            tenant_id,
        )
        category_ids[item["template_code"]] = int(created_id)
        _record_template_item_install(
            db,
            tenant_id,
            user_id,
            result,
            item,
            "categorias",
            created_id,
        )
        result.bump("created", "product_categories")
    return category_ids


def _copy_products(
    db: Session,
    items: list[dict[str, Any]],
    tenant_id: str,
    user_id: int,
    result: OnboardingResult,
    department_ids: dict[str, int],
    category_ids: dict[str, int],
) -> None:
    for item in items:
        payload = item["payload"]
        mapped_id = _mapped_template_row_id(db, tenant_id, result, item, "produtos")
        if mapped_id:
            result.bump("skipped", "product_references")
            continue

        existing_id = _scalar(
            db,
            """
            SELECT id
            FROM produtos
            WHERE {tenant_filter}
              AND lower(trim(codigo)) = lower(trim(:codigo))
            LIMIT 1
            """,
            {"codigo": payload["codigo"]},
            tenant_id,
        )
        if existing_id:
            _record_template_item_install(
                db,
                tenant_id,
                user_id,
                result,
                item,
                "produtos",
                existing_id,
            )
            result.bump("skipped", "product_references")
            continue
        if result.dry_run:
            result.bump("would_create", "product_references")
            continue

        category_id = category_ids.get(payload.get("categoria_code"))
        department_id = department_ids.get(payload.get("departamento_code"))
        if not category_id or not department_id:
            result.warnings.append(
                f"Categoria/departamento ausente para produto opcional {item['template_code']}."
            )
            continue

        _execute_insert(
            db,
            """
            INSERT INTO produtos (
                tenant_id, user_id, codigo, nome, tipo, situacao, tipo_produto,
                is_parent, is_sellable, descricao_curta, categoria_id,
                departamento_id, preco_custo, preco_venda, estoque_atual,
                estoque_minimo, estoque_maximo, unidade, condicao, ativo,
                created_at, updated_at
            ) VALUES (
                :tenant_id, :user_id, :codigo, :nome, :tipo, :situacao, 'SIMPLES',
                :is_parent, :is_sellable, :descricao_curta, :categoria_id,
                :departamento_id, :preco_custo, :preco_venda, :estoque_atual,
                :estoque_minimo, :estoque_maximo, :unidade, :condicao, :ativo,
                CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            """,
            {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "codigo": payload["codigo"],
                "nome": payload["nome"],
                "tipo": payload.get("tipo", "produto"),
                "situacao": bool(payload.get("situacao", False)),
                "is_parent": False,
                "is_sellable": True,
                "descricao_curta": payload.get("descricao_curta"),
                "categoria_id": category_id,
                "departamento_id": department_id,
                "preco_custo": payload.get("preco_custo", 0),
                "preco_venda": payload.get("preco_venda", 0),
                "estoque_atual": payload.get("estoque_atual", 0),
                "estoque_minimo": payload.get("estoque_minimo", 0),
                "estoque_maximo": payload.get("estoque_maximo", 0),
                "unidade": payload.get("unidade", "UN"),
                "condicao": payload.get("condicao", "novo"),
                "ativo": bool(payload.get("ativo", False)),
            },
            tenant_id,
        )
        created_id = _scalar(
            db,
            """
            SELECT id
            FROM produtos
            WHERE {tenant_filter}
              AND lower(trim(codigo)) = lower(trim(:codigo))
            LIMIT 1
            """,
            {"codigo": payload["codigo"]},
            tenant_id,
        )
        _record_template_item_install(
            db,
            tenant_id,
            user_id,
            result,
            item,
            "produtos",
            created_id,
        )
        result.bump("created", "product_references")


def _record_install(db: Session, tenant_id: str, user_id: int, result: OnboardingResult) -> None:
    if not _table_exists(db, "tenant_template_installs"):
        result.warnings.append("Tabela tenant_template_installs ausente; auditoria de onboarding nao registrada.")
        return

    tenant_uuid = uuid.UUID(tenant_id)
    install = (
        db.query(TenantTemplateInstall)
        .filter(
            TenantTemplateInstall.tenant_id == tenant_uuid,
            TenantTemplateInstall.bundle_code == result.bundle_code,
            TenantTemplateInstall.bundle_version == result.bundle_version,
        )
        .first()
    )
    summary = result.to_dict()
    if install is None:
        db.add(
            TenantTemplateInstall(
                tenant_id=tenant_uuid,
                bundle_code=result.bundle_code,
                bundle_version=result.bundle_version,
                status="completed",
                dry_run=result.dry_run,
                created_by_user_id=user_id,
                summary=summary,
            )
        )
    else:
        install.status = "completed"
        install.dry_run = result.dry_run
        install.created_by_user_id = user_id
        install.summary = summary
    db.flush()


def _run_onboarding_steps(
    db: Session,
    tenant_id_str: str,
    user_id_int: int,
    bundle_code: str,
    bundle_version: str,
    dry_run: bool,
    include_products: bool,
    strict_required: bool,
    result: OnboardingResult,
) -> dict[str, Any]:
    if not dry_run:
        ensure_builtin_templates(db)
    if strict_required and not dry_run:
        _warn_missing_template_infra_for_strict(db, result)

    items, source = _load_template_items(db, bundle_code, bundle_version)
    result.template_source = source

    if _tables_ready_or_warn(db, result, "formas de pagamento", ("formas_pagamento",)):
        _copy_payment_methods(
            db,
            _items_by_type(items, "payment_method"),
            tenant_id_str,
            user_id_int,
            result,
        )

    category_ids: dict[str, int] = {}
    subcategory_ids: dict[str, int] = {}
    if _tables_ready_or_warn(
        db,
        result,
        "estrutura DRE",
        ("dre_categorias", "dre_subcategorias"),
    ):
        category_ids = _copy_dre_categories(
            db,
            _items_by_type(items, "dre_category"),
            tenant_id_str,
            result,
        )
        subcategory_ids = _copy_dre_subcategories(
            db,
            _items_by_type(items, "dre_subcategory"),
            tenant_id_str,
            result,
            category_ids,
        )

    if _tables_ready_or_warn(db, result, "categorias financeiras", ("categorias_financeiras",)):
        _copy_financial_categories(
            db,
            _items_by_type(items, "financial_category"),
            tenant_id_str,
            user_id_int,
            result,
            subcategory_ids,
        )
    if _tables_ready_or_warn(db, result, "tipos de despesa", ("tipo_despesas",)):
        _copy_expense_types(
            db,
            _items_by_type(items, "expense_type"),
            tenant_id_str,
            result,
            subcategory_ids,
        )

    department_ids: dict[str, int] = {}
    product_category_ids: dict[str, int] = {}
    if _tables_ready_or_warn(db, result, "departamentos de produtos", ("departamentos",)):
        department_ids = _copy_product_departments(
            db,
            _items_by_type(items, "product_department"),
            tenant_id_str,
            user_id_int,
            result,
        )
    if _tables_ready_or_warn(db, result, "categorias de produtos", ("categorias",)):
        product_category_ids = _copy_product_categories(
            db,
            _items_by_type(items, "product_category"),
            tenant_id_str,
            user_id_int,
            result,
            department_ids,
        )

    if include_products:
        if _tables_ready_or_warn(db, result, "produtos opcionais", ("produtos",)):
            _copy_products(
                db,
                _items_by_type(items, "product_reference"),
                tenant_id_str,
                user_id_int,
                result,
                department_ids,
                product_category_ids,
            )

    if not dry_run:
        _record_install(db, tenant_id_str, user_id_int, result)

    if strict_required and not dry_run:
        _enforce_required_onboarding(result)

    return result.to_dict()


def onboard_tenant_defaults(
    db: Session,
    tenant_id: Any,
    user_id: Any,
    bundle_code: str = DEFAULT_BUNDLE_CODE,
    bundle_version: str = DEFAULT_BUNDLE_VERSION,
    dry_run: bool = False,
    include_products: bool = False,
    strict_required: bool = False,
) -> dict[str, Any]:
    """
    Copy system templates into tenant-owned tables.

    The operation is idempotent: existing tenant records are skipped and missing
    records are created. Products are intentionally optional and not copied by
    default because catalog data is business-specific.
    """
    tenant_id_str = _normalize_tenant_id(tenant_id)
    user_id_int = _normalize_user_id(user_id)

    result = OnboardingResult(
        tenant_id=tenant_id_str,
        bundle_code=bundle_code,
        bundle_version=bundle_version,
        dry_run=dry_run,
    )

    try:
        return _run_onboarding_steps(
            db,
            tenant_id_str,
            user_id_int,
            bundle_code,
            bundle_version,
            dry_run,
            include_products,
            strict_required,
            result,
        )
    except SQLAlchemyError as exc:
        raise TenantOnboardingError(f"Falha no onboarding do tenant {tenant_id_str}: {exc}") from exc
