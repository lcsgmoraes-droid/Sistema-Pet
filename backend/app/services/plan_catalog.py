"""Catalogo comercial canonico dos planos CorePet.

Este modulo concentra codigos, precos, limites e direitos dos planos. A cobranca
podera ser ligada a qualquer gateway sem espalhar regras comerciais pelo sistema.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class PlanDefinition:
    code: str
    name: str
    segment: str
    price_cents: int
    organization_types: frozenset[str]
    modules: frozenset[str]
    entitlements: frozenset[str]
    monthly_sales_limit: int | None = None
    simultaneous_sessions_limit: int | None = None

    def to_public_dict(self) -> dict:
        return {
            "codigo": self.code,
            "nome": self.name,
            "segmento": self.segment,
            "preco_centavos": self.price_cents,
            "modulos": sorted(self.modules),
            "recursos": sorted(self.entitlements),
            "limites": {
                "vendas_mensais": self.monthly_sales_limit,
                "acessos_simultaneos": self.simultaneous_sessions_limit,
            },
        }


CORE = frozenset({"core.pdv", "core.customers_pets", "core.catalog_stock"})
APP_AGENDA = frozenset({"app.customer", "scheduling.basic", "notifications.app"})


PLAN_CATALOG: Final[dict[str, PlanDefinition]] = {
    "pet-start": PlanDefinition(
        code="pet-start",
        name="Pet Start",
        segment="pet",
        price_cents=4_990,
        organization_types=frozenset({"petshop"}),
        modules=frozenset(),
        entitlements=CORE,
        monthly_sales_limit=300,
        simultaneous_sessions_limit=1,
    ),
    "pet-basico": PlanDefinition(
        code="pet-basico",
        name="Pet Basico",
        segment="pet",
        price_cents=19_700,
        organization_types=frozenset({"petshop"}),
        modules=frozenset(),
        entitlements=CORE | {"purchases.invoice_xml", "core.permissions"},
        simultaneous_sessions_limit=3,
    ),
    "pet-gestao": PlanDefinition(
        code="pet-gestao",
        name="Pet Gestao",
        segment="pet",
        price_cents=39_700,
        organization_types=frozenset({"petshop"}),
        modules=frozenset({"compras", "financeiro_erp"}),
        entitlements=CORE
        | {
            "purchases.invoice_xml",
            "purchases.suggestions",
            "finance.management",
            "finance.dre",
            "core.permissions",
        },
        simultaneous_sessions_limit=3,
    ),
    "pet-venda-ativa": PlanDefinition(
        code="pet-venda-ativa",
        name="Pet Venda Ativa",
        segment="pet",
        price_cents=69_700,
        organization_types=frozenset({"petshop"}),
        modules=frozenset(
            {
                "app_mobile",
                "campanhas",
                "comissoes",
                "compras",
                "ecommerce",
                "entregas",
                "financeiro_erp",
                "fiscal",
                "ia_avancada",
                "integracoes",
                "marketplaces",
                "rh",
            }
        ),
        entitlements=CORE
        | {
            "purchases.invoice_xml",
            "purchases.suggestions",
            "finance.management",
            "finance.dre",
            "sales.app_ecommerce",
            "sales.campaigns",
            "sales.recurrence",
            "delivery.routes",
            "fiscal.products",
            "core.permissions",
        },
        simultaneous_sessions_limit=3,
    ),
    "vet-start": PlanDefinition(
        code="vet-start",
        name="Vet Start",
        segment="vet",
        price_cents=7_990,
        organization_types=frozenset({"veterinary_clinic", "hospital"}),
        modules=frozenset({"app_mobile", "veterinario"}),
        entitlements=CORE | APP_AGENDA | {"veterinary.basic"},
        simultaneous_sessions_limit=1,
    ),
    "vet-gestao": PlanDefinition(
        code="vet-gestao",
        name="Vet Gestao",
        segment="vet",
        price_cents=24_700,
        organization_types=frozenset({"veterinary_clinic", "hospital"}),
        modules=frozenset({"app_mobile", "financeiro_erp", "veterinario"}),
        entitlements=CORE
        | APP_AGENDA
        | {
            "veterinary.basic",
            "veterinary.records",
            "veterinary.exams_vaccines",
            "finance.management",
        },
        simultaneous_sessions_limit=3,
    ),
    "vet-completo": PlanDefinition(
        code="vet-completo",
        name="Vet Completo",
        segment="vet",
        price_cents=49_700,
        organization_types=frozenset({"veterinary_clinic", "hospital"}),
        modules=frozenset(
            {"app_mobile", "financeiro_erp", "ia_avancada", "veterinario"}
        ),
        entitlements=CORE
        | APP_AGENDA
        | {
            "veterinary.basic",
            "veterinary.records",
            "veterinary.exams_vaccines",
            "veterinary.hospitalization",
            "veterinary.protocols_ai",
            "finance.management",
        },
        simultaneous_sessions_limit=3,
    ),
    "grooming-start": PlanDefinition(
        code="grooming-start",
        name="B&T Start",
        segment="grooming",
        price_cents=5_990,
        organization_types=frozenset({"grooming"}),
        modules=frozenset({"app_mobile", "banho_tosa"}),
        entitlements=CORE | APP_AGENDA | {"grooming.basic"},
        simultaneous_sessions_limit=1,
    ),
    "grooming-gestao": PlanDefinition(
        code="grooming-gestao",
        name="B&T Gestao",
        segment="grooming",
        price_cents=11_700,
        organization_types=frozenset({"grooming"}),
        modules=frozenset({"app_mobile", "banho_tosa", "comissoes", "financeiro_erp"}),
        entitlements=CORE
        | APP_AGENDA
        | {
            "grooming.basic",
            "grooming.team_queue",
            "grooming.packages_recurrence",
            "finance.management",
        },
        simultaneous_sessions_limit=3,
    ),
    "grooming-completo": PlanDefinition(
        code="grooming-completo",
        name="B&T Completo",
        segment="grooming",
        price_cents=15_700,
        organization_types=frozenset({"grooming"}),
        modules=frozenset(
            {
                "app_mobile",
                "banho_tosa",
                "campanhas",
                "comissoes",
                "entregas",
                "financeiro_erp",
            }
        ),
        entitlements=CORE
        | APP_AGENDA
        | {
            "grooming.basic",
            "grooming.team_queue",
            "grooming.packages_recurrence",
            "grooming.costs_margin",
            "grooming.campaigns_routes",
            "finance.management",
        },
        simultaneous_sessions_limit=3,
    ),
}

PLAN_ALIASES: Final[dict[str, str]] = {
    "basico": "pet-basico",
    "basico-pet": "pet-basico",
    "basic": "pet-basico",
    "base": "pet-basico",
    "básico": "pet-basico",
}

ORGANIZATION_TYPE_ALIASES: Final[dict[str, str]] = {
    "pet": "petshop",
    "pet_shop": "petshop",
    "loja_pet": "petshop",
    "vet": "veterinary_clinic",
    "veterinario": "veterinary_clinic",
    "clinica_veterinaria": "veterinary_clinic",
    "banho_tosa": "grooming",
}

PUBLIC_SIGNUP_PLANS: Final[frozenset[str]] = frozenset(PLAN_CATALOG)
ALL_PUBLIC_ENTITLEMENTS: Final[frozenset[str]] = frozenset(
    entitlement for plan in PLAN_CATALOG.values() for entitlement in plan.entitlements
)


def normalize_plan_code(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    return PLAN_ALIASES.get(normalized, normalized)


def get_plan(value: str | None) -> PlanDefinition | None:
    return PLAN_CATALOG.get(normalize_plan_code(value))


def normalize_organization_type(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    return ORGANIZATION_TYPE_ALIASES.get(normalized, normalized)


def resolve_signup_selection(
    plan_code: str | None, organization_type: str | None
) -> tuple[PlanDefinition, str]:
    plan = get_plan(plan_code or "pet-start")
    if plan is None:
        raise ValueError("Plano selecionado indisponivel")

    normalized_organization = normalize_organization_type(organization_type)
    if not normalized_organization:
        normalized_organization = sorted(plan.organization_types)[0]

    if normalized_organization not in plan.organization_types:
        raise ValueError("O plano selecionado nao pertence ao perfil informado")

    return plan, normalized_organization
