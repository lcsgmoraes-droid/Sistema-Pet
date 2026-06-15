from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND_CI_WORKFLOW = ROOT / ".github" / "workflows" / "backend-ci.yml"


def test_backend_ci_has_blocking_tenancy_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Tenancy lint (blocking)" in source
    assert "ruff check app/tenancy" in source


def test_backend_ci_has_blocking_auth_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Auth lint (blocking)" in source
    assert "ruff check app/auth app/auth_routes_multitenant.py app/usuarios_routes.py" in source


def test_backend_ci_has_blocking_db_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Database lint (blocking)" in source
    assert "ruff check app/db" in source


def test_backend_ci_has_blocking_schemas_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Schemas lint (blocking)" in source
    assert "ruff check app/schemas" in source


def test_backend_ci_has_blocking_security_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Security lint (blocking)" in source
    assert "ruff check app/security" in source


def test_backend_ci_has_blocking_core_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Core lint (blocking)" in source
    assert "ruff check app/core" in source


def test_backend_ci_has_blocking_events_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Events lint (blocking)" in source
    assert "ruff check app/events" in source


def test_backend_ci_has_blocking_utils_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Utils lint (blocking)" in source
    assert "ruff check app/utils" in source


def test_backend_ci_has_blocking_constants_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Constants lint (blocking)" in source
    assert "ruff check app/constants" in source


def test_backend_ci_has_blocking_cache_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Cache lint (blocking)" in source
    assert "ruff check app/cache" in source


def test_backend_ci_has_blocking_replay_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Replay lint (blocking)" in source
    assert "ruff check app/replay" in source


def test_backend_ci_has_blocking_application_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Application lint (blocking)" in source
    assert "ruff check app/application" in source


def test_backend_ci_has_blocking_analytics_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Analytics lint (blocking)" in source
    assert "ruff check app/analytics" in source


def test_backend_ci_has_blocking_fiscal_models_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Fiscal models lint (blocking)" in source
    assert "ruff check app/fiscal_models" in source


def test_backend_ci_has_blocking_caixa_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Caixa lint (blocking)" in source
    assert "ruff check app/caixa" in source


def test_backend_ci_has_blocking_parsers_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Parsers lint (blocking)" in source
    assert "ruff check app/parsers" in source


def test_backend_ci_has_blocking_scripts_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Scripts lint (blocking)" in source
    assert "ruff check app/scripts" in source


def test_backend_ci_has_blocking_middlewares_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Middlewares lint (blocking)" in source
    assert "ruff check app/middlewares" in source


def test_backend_ci_has_blocking_notas_entrada_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Notas entrada lint (blocking)" in source
    assert "ruff check app/notas_entrada" in source


def test_backend_ci_has_blocking_produtos_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Produtos lint (blocking)" in source
    assert "ruff check app/produtos" in source


def test_backend_ci_has_blocking_insights_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Insights lint (blocking)" in source
    assert "ruff check app/insights" in source


def test_backend_ci_has_blocking_schedulers_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Schedulers lint (blocking)" in source
    assert "ruff check app/schedulers" in source


def test_backend_ci_has_blocking_audit_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Audit lint (blocking)" in source
    assert "ruff check app/audit" in source


def test_backend_ci_has_blocking_financeiro_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Financeiro lint (blocking)" in source
    assert "ruff check app/financeiro" in source


def test_backend_ci_has_blocking_routers_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Routers lint (blocking)" in source
    assert "ruff check app/routers" in source


def test_backend_ci_has_blocking_domain_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Domain lint (blocking)" in source
    assert "ruff check app/domain" in source


def test_backend_ci_has_blocking_read_models_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Read models lint (blocking)" in source
    assert "ruff check app/read_models" in source


def test_backend_ci_has_blocking_banho_tosa_api_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Banho Tosa API lint (blocking)" in source
    assert "ruff check app/banho_tosa_api" in source


def test_backend_ci_has_blocking_estoque_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Estoque lint (blocking)" in source
    assert "ruff check app/estoque" in source


def test_backend_ci_has_blocking_configuracoes_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Configuracoes lint (blocking)" in source
    assert "ruff check app/configuracoes" in source


def test_backend_ci_has_blocking_clean_package_lint_steps():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    expected_steps = [
        ("Database package lint (blocking)", "ruff check app/database"),
        ("DRE lint (blocking)", "ruff check app/dre"),
        ("Migrations lint (blocking)", "ruff check app/migrations"),
        (
            "Banho Tosa model parts lint (blocking)",
            "ruff check app/banho_tosa_model_parts",
        ),
        (
            "Banho Tosa schema parts lint (blocking)",
            "ruff check app/banho_tosa_schema_parts",
        ),
    ]

    for step_name, command in expected_steps:
        assert step_name in source
        assert command in source


def test_backend_ci_has_blocking_services_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Services lint (blocking)" in source
    assert "ruff check app/services" in source


def test_backend_ci_has_blocking_campaigns_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Campaigns lint (blocking)" in source
    assert "ruff check app/campaigns" in source


def test_backend_ci_has_blocking_vendas_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Vendas lint (blocking)" in source
    assert "ruff check app/vendas" in source


def test_backend_ci_has_blocking_whatsapp_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "WhatsApp lint (blocking)" in source
    assert "ruff check app/whatsapp" in source
