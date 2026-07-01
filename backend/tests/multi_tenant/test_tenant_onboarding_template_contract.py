from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.db  # noqa: F401 - registra hooks multitenant
from app.services.tenant_onboarding_service import validate_onboarding_template_contract
from tests.multi_tenant.tenant_onboarding_test_helpers import (
    TENANT_A,
    _count,
)


pytest_plugins = ["tests.multi_tenant.tenant_onboarding_test_helpers"]


def test_template_contract_check_is_read_only_and_accepts_complete_builtin_contract(
    onboarding_session,
):
    result = validate_onboarding_template_contract(
        onboarding_session, include_products=True
    )

    assert result["ok"] is True
    assert result["mode"] == "template_contract_check"
    assert result["dry_run"] is True
    assert result["missing_sections"] == []
    assert result["missing_template_tables"] == []
    assert result["missing_operational_tables"] == {}
    assert result["dependency_errors"] == []
    assert result["template_item_counts"]["payment_method"] == 4
    assert result["template_item_counts"]["bank_account"] == 2
    assert result["template_item_counts"]["pet_species"] == 2
    assert result["template_item_counts"]["pet_breed"] == 2
    assert result["template_item_counts"]["ration_line"] == 4
    assert result["template_item_counts"]["animal_size"] == 6
    assert result["template_item_counts"]["life_stage"] == 4
    assert result["template_item_counts"]["treatment_type"] == 9
    assert result["template_item_counts"]["protein_flavor"] == 10
    assert result["template_item_counts"]["package_weight"] == 11
    assert result["template_item_counts"]["product_reference"] == 3
    assert _count(onboarding_session, "template_items") == 0
    assert _count(onboarding_session, "formas_pagamento", TENANT_A) == 0


def test_template_contract_check_reports_missing_infra_without_writes():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        result = validate_onboarding_template_contract(session)
    finally:
        session.close()

    assert result["ok"] is False
    assert "template_bundles" in result["missing_template_tables"]
    assert "formas_pagamento" in result["missing_operational_tables"]["payment_methods"]
    assert "payment_methods" not in result["missing_sections"]
