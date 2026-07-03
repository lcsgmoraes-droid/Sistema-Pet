from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]

SEED_DEMO_FILES = [
    "backend/app/scripts/seed_demo_operacional.py",
    "backend/app/scripts/seed_demo_operacional_data.py",
    "backend/app/scripts/seed_demo_operacional_db.py",
    "backend/app/scripts/seed_demo_operacional_accounting.py",
    "backend/app/scripts/seed_demo_operacional_payments.py",
    "backend/app/scripts/seed_demo_operacional_support.py",
    "backend/app/scripts/seed_demo_operacional_catalog.py",
    "backend/app/scripts/seed_demo_operacional_movements.py",
    "backend/app/scripts/seed_demo_operacional_sales_finance.py",
    "backend/app/scripts/seed_demo_operacional_logistics.py",
    "backend/app/scripts/seed_demo_operacional_sales_core.py",
    "backend/app/scripts/seed_demo_operacional_runner.py",
]


def _source(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def _non_empty_line_count(relative_path: str) -> int:
    return sum(1 for line in _source(relative_path).splitlines() if line.strip())


def test_seed_demo_operacional_fatia_54_divide_script_em_modulos_focados():
    facade_source = _source("backend/app/scripts/seed_demo_operacional.py")

    for relative_path in SEED_DEMO_FILES:
        assert (REPO_ROOT / relative_path).exists(), relative_path

    assert "from app.scripts.seed_demo_operacional_data import" in facade_source
    assert "from app.scripts.seed_demo_operacional_runner import" in facade_source
    assert "def _insert_sale(" not in facade_source
    assert "def _ensure_support_data(" not in facade_source


def test_seed_demo_operacional_fatia_54_fica_abaixo_de_700_linhas_nao_vazias():
    counts = {relative_path: _non_empty_line_count(relative_path) for relative_path in SEED_DEMO_FILES}

    assert all(lines < 700 for lines in counts.values()), counts


def test_seed_demo_operacional_fatia_54_preserva_exports_compatibilidade():
    from app.scripts import seed_demo_operacional as facade
    from app.scripts import seed_demo_operacional_catalog as catalog
    from app.scripts import seed_demo_operacional_data as data
    from app.scripts import seed_demo_operacional_runner as runner
    from app.scripts import seed_demo_operacional_support as support

    assert facade.SaleScenario is data.SaleScenario
    assert facade.FixedPayable is data.FixedPayable
    assert facade.build_demo_scenarios is data.build_demo_scenarios
    assert facade.build_fixed_payables is data.build_fixed_payables
    assert facade.money is data.money
    assert facade.apply_operational_seed is runner.apply_operational_seed
    assert facade._product_pool is catalog._product_pool
    assert facade._ensure_person is support._ensure_person


def test_seed_demo_operacional_fatia_54_preserva_parser_cli():
    from app.scripts.seed_demo_operacional import _build_parser

    parser = _build_parser()
    args = parser.parse_args(
        [
            "--target-email",
            "demo@sistemapet.local",
            "--source-email",
            "origem@sistemapet.local",
            "--base-date",
            "2026-07-03",
            "--skip-catalog-import",
            "--apply",
        ]
    )

    assert args.target_email == "demo@sistemapet.local"
    assert args.source_email == "origem@sistemapet.local"
    assert args.base_date == "2026-07-03"
    assert args.skip_catalog_import is True
    assert args.apply is True


def test_seed_demo_operacional_fatia_54_runner_preserva_dry_run_skip_catalog(
    monkeypatch,
):
    from datetime import date

    from app.scripts import seed_demo_operacional_runner as runner

    captured = {}

    monkeypatch.setattr(
        runner,
        "_resolve_tenant_context",
        lambda db, email: {
            "email": email,
            "tenant_id": "tenant-demo",
            "user_id": 10,
            "user_name": "Lucas Demo",
        },
    )
    monkeypatch.setattr(runner, "_set_tenant_context", lambda db, tenant_id: None)

    def fake_import_catalog(**kwargs):
        captured["skip"] = kwargs["skip"]
        return {"status": "skipped"}

    monkeypatch.setattr(runner, "_maybe_import_catalog", fake_import_catalog)

    result = runner.apply_operational_seed(
        object(),
        target_email="demo@sistemapet.local",
        source_email="origem@sistemapet.local",
        base_date=date(2026, 7, 3),
        dry_run=True,
        skip_catalog_import=True,
    )

    assert captured["skip"] is True
    assert result["dry_run"] is True
    assert result["sales_scenarios"]
    assert result["fixed_payables"]
