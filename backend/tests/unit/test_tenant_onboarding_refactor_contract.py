from pathlib import Path

from app.services import tenant_onboarding_contract as contract
from app.services import tenant_onboarding_core as core
from app.services import tenant_onboarding_service as service


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
    assert _line_count("app", "services", "tenant_onboarding_service.py") < 1900
    assert _line_count("app", "services", "tenant_onboarding_core.py") >= 100
    assert _line_count("app", "services", "tenant_onboarding_contract.py") >= 300
