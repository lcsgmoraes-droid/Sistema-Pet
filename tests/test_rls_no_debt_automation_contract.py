from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION_SMOKE_SCRIPT = ROOT / "scripts" / "ci_migration_smoke.py"
PROD_DEPLOY_SCRIPT = ROOT / "scripts" / "deploy_producao_seguro.sh"


def _load_migration_smoke_module():
    spec = importlib.util.spec_from_file_location("ci_migration_smoke", MIGRATION_SMOKE_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_migration_smoke_runs_rls_no_debt_guard_after_upgrade(monkeypatch):
    smoke = _load_migration_smoke_module()
    calls: list[tuple[str, object]] = []

    monkeypatch.setattr(smoke, "_database_url", lambda: smoke.make_url("postgresql://example"))
    monkeypatch.setattr(smoke, "_expected_head", lambda database_url: "head123")
    monkeypatch.setattr(
        smoke,
        "_database_plan",
        lambda: [smoke.SmokeDatabase("clean", "petshop_smoke_clean", None)],
    )
    monkeypatch.setattr(smoke, "_prepare_database", lambda *args: calls.append(("prepare", args)))
    monkeypatch.setattr(smoke, "_drop_database", lambda *args: calls.append(("drop", args)))
    monkeypatch.setattr(smoke, "_run_alembic", lambda *args: calls.append(("alembic", args)))
    monkeypatch.setattr(smoke, "_assert_database_at_head", lambda *args: calls.append(("head", args)))
    monkeypatch.setattr(smoke, "_assert_rls_no_debt", lambda *args: calls.append(("rls", args)))

    assert smoke.main() == 0

    call_names = [name for name, _ in calls]
    assert call_names == ["prepare", "alembic", "head", "rls", "drop"]


def test_prod_deploy_runs_rls_no_debt_guard_after_migrations_before_services():
    source = PROD_DEPLOY_SCRIPT.read_text(encoding="utf-8")

    migration_index = source.index("docker compose -f \"$COMPOSE_FILE\" run --rm --no-deps backend alembic upgrade head")
    guard_index = source.index("python scripts/check_rls_no_debt.py")
    services_index = source.index("mark_step \"subir_servicos\"")

    assert migration_index < guard_index < services_index
    assert "PYTHONPATH=/app" in source
