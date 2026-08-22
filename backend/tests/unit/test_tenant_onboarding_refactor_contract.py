from pathlib import Path

from app.services import tenant_onboarding_contract as contract
from app.services import tenant_onboarding_core as core
from app.services import tenant_onboarding_catalog_templates as catalog_templates
from app.services import tenant_onboarding_financial_templates as financial_templates
from app.services import tenant_onboarding_service as service
from app.services import tenant_onboarding_template_contracts as template_contracts
from app.services import tenant_onboarding_templates as templates


BACKEND_DIR = Path(__file__).resolve().parents[2]


def _line_count(*parts: str) -> int:
    return len((BACKEND_DIR / Path(*parts)).read_text(encoding="utf-8").splitlines())


def test_tenant_onboarding_service_preserves_public_reexports() -> None:
    assert service.TenantOnboardingError is core.TenantOnboardingError
    assert service.OnboardingResult is core.OnboardingResult
    assert (
        service.validate_onboarding_template_contract
        is contract.validate_onboarding_template_contract
    )
    assert service.ensure_builtin_templates is contract.ensure_builtin_templates
    assert service._load_template_items is contract._load_template_items


def test_tenant_onboarding_service_stays_split_across_modules() -> None:
    assert _line_count("app", "services", "tenant_onboarding_service.py") < 300
    assert _line_count("app", "services", "tenant_onboarding_core.py") >= 100
    assert _line_count("app", "services", "tenant_onboarding_contract.py") >= 300
    assert _line_count("app", "services", "tenant_onboarding_sql.py") >= 80
    assert _line_count("app", "services", "tenant_onboarding_runner.py") >= 150
    assert (
        _line_count("app", "services", "tenant_onboarding_financial_copies.py") < 1000
    )
    assert _line_count("app", "services", "tenant_onboarding_catalog_copies.py") < 1000


def test_builtin_template_registry_stays_split_by_responsibility() -> None:
    assert _line_count("app", "services", "tenant_onboarding_templates.py") < 700
    assert (
        _line_count("app", "services", "tenant_onboarding_financial_templates.py") < 700
    )
    assert (
        _line_count("app", "services", "tenant_onboarding_catalog_templates.py") < 700
    )
    assert (
        _line_count("app", "services", "tenant_onboarding_template_contracts.py") < 700
    )

    assert templates.BUILTIN_TEMPLATE_ITEMS == [
        *templates.BASE_TEMPLATE_ITEMS,
        *financial_templates.FINANCIAL_TEMPLATE_ITEMS,
        *catalog_templates.CATALOG_TEMPLATE_ITEMS,
    ]
    assert (
        templates.ITEM_INSTALL_TARGET_TABLES
        is template_contracts.ITEM_INSTALL_TARGET_TABLES
    )
