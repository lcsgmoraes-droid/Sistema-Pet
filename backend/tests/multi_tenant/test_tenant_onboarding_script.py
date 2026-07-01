import json

from sqlalchemy import text

from app.scripts import run_tenant_onboarding
from app.services.tenant_onboarding_service import onboard_tenant_defaults
from tests.multi_tenant.tenant_onboarding_test_helpers import (
    TENANT_A,
    TENANT_B,
    _count,
    _SessionProxy,
)


pytest_plugins = ["tests.multi_tenant.tenant_onboarding_test_helpers"]


def test_onboarding_script_defaults_to_dry_run(monkeypatch, capsys, onboarding_session):
    monkeypatch.setattr(
        run_tenant_onboarding,
        "SessionLocal",
        lambda: _SessionProxy(onboarding_session),
    )

    code = run_tenant_onboarding.main(["--tenant-id", TENANT_A, "--user-id", "1"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert code == 0
    assert payload["dry_run"] is True
    assert payload["would_create"]["payment_methods"] == 4
    assert _count(onboarding_session, "formas_pagamento", TENANT_A) == 0


def test_onboarding_script_apply_persists(monkeypatch, capsys, onboarding_session):
    monkeypatch.setattr(
        run_tenant_onboarding,
        "SessionLocal",
        lambda: _SessionProxy(onboarding_session),
    )

    code = run_tenant_onboarding.main(
        ["--tenant-id", TENANT_A, "--user-id", "1", "--apply"]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert code == 0
    assert payload["dry_run"] is False
    assert payload["created"]["payment_methods"] == 4
    assert _count(onboarding_session, "formas_pagamento", TENANT_A) == 4


def test_onboarding_script_all_active_tenants_dry_run(
    monkeypatch, capsys, onboarding_session
):
    onboarding_session.execute(
        text("INSERT INTO tenants (id, status) VALUES (:id, 'active')"),
        {"id": TENANT_A},
    )
    onboarding_session.execute(
        text("INSERT INTO tenants (id, status) VALUES (:id, 'active')"),
        {"id": TENANT_B},
    )
    onboarding_session.execute(
        text("INSERT INTO tenants (id, status) VALUES (:id, 'inactive')"),
        {"id": "33333333-3333-3333-3333-333333333333"},
    )
    onboarding_session.execute(
        text("INSERT INTO users (tenant_id, is_active) VALUES (:tenant_id, 1)"),
        {"tenant_id": TENANT_A},
    )
    onboarding_session.execute(
        text("INSERT INTO users (tenant_id, is_active) VALUES (:tenant_id, 1)"),
        {"tenant_id": TENANT_B},
    )
    onboarding_session.commit()
    monkeypatch.setattr(
        run_tenant_onboarding,
        "SessionLocal",
        lambda: _SessionProxy(onboarding_session),
    )

    code = run_tenant_onboarding.main(["--all-active-tenants"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert code == 0
    assert payload["dry_run"] is True
    assert payload["mode"] == "all_active_tenants"
    assert payload["tenant_count"] == 2
    assert payload["totals"]["would_create"]["payment_methods"] == 8
    assert _count(onboarding_session, "formas_pagamento", TENANT_A) == 0
    assert _count(onboarding_session, "formas_pagamento", TENANT_B) == 0


def test_onboarding_script_future_tenant_check_does_not_read_or_update_existing_tenants(
    monkeypatch,
    capsys,
    onboarding_session,
):
    onboarding_session.execute(
        text("INSERT INTO tenants (id, status) VALUES (:id, 'active')"),
        {"id": TENANT_A},
    )
    onboarding_session.execute(
        text("INSERT INTO users (tenant_id, is_active) VALUES (:tenant_id, 1)"),
        {"tenant_id": TENANT_A},
    )
    onboarding_session.commit()
    monkeypatch.setattr(
        run_tenant_onboarding,
        "SessionLocal",
        lambda: _SessionProxy(onboarding_session),
    )

    code = run_tenant_onboarding.main(["--future-tenant-check"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert code == 0
    assert payload["mode"] == "future_tenant_check"
    assert payload["tenant_scope"] == "synthetic_future_tenant"
    assert payload["dry_run"] is True
    assert payload["result"]["would_create"]["payment_methods"] == 4
    assert payload["result"]["would_create"]["dre_categories"] == 3
    assert payload["result"]["would_create"]["product_categories"] == 2
    assert TENANT_A not in captured.out
    assert _count(onboarding_session, "formas_pagamento", TENANT_A) == 0
    assert _count(onboarding_session, "tenant_template_installs") == 0


def test_onboarding_script_all_active_tenants_apply_blocks_bulk_existing_by_default(
    monkeypatch,
    capsys,
    onboarding_session,
):
    onboarding_session.execute(
        text("INSERT INTO tenants (id, status) VALUES (:id, 'active')"),
        {"id": TENANT_A},
    )
    onboarding_session.execute(
        text("INSERT INTO users (tenant_id, is_active) VALUES (:tenant_id, 1)"),
        {"tenant_id": TENANT_A},
    )
    onboarding_session.commit()
    monkeypatch.setattr(
        run_tenant_onboarding,
        "SessionLocal",
        lambda: _SessionProxy(onboarding_session),
    )

    code = run_tenant_onboarding.main(["--all-active-tenants", "--apply"])

    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert code == 1
    assert payload["dry_run"] is False
    assert "tenants existentes" in payload["error"]
    assert _count(onboarding_session, "formas_pagamento", TENANT_A) == 0


def test_onboarding_script_all_active_tenants_apply_with_explicit_override(
    monkeypatch, capsys, onboarding_session
):
    onboarding_session.execute(
        text("INSERT INTO tenants (id, status) VALUES (:id, 'active')"),
        {"id": TENANT_A},
    )
    onboarding_session.execute(
        text("INSERT INTO tenants (id, status) VALUES (:id, 'ativo')"), {"id": TENANT_B}
    )
    onboarding_session.execute(
        text("INSERT INTO users (tenant_id, is_active) VALUES (:tenant_id, 1)"),
        {"tenant_id": TENANT_A},
    )
    onboarding_session.execute(
        text("INSERT INTO users (tenant_id, is_active) VALUES (:tenant_id, 1)"),
        {"tenant_id": TENANT_B},
    )
    onboarding_session.commit()
    monkeypatch.setattr(
        run_tenant_onboarding,
        "SessionLocal",
        lambda: _SessionProxy(onboarding_session),
    )

    code = run_tenant_onboarding.main(
        ["--all-active-tenants", "--apply", "--allow-existing-tenant-apply"]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert code == 0
    assert payload["dry_run"] is False
    assert payload["tenant_count"] == 2
    assert payload["totals"]["created"]["payment_methods"] == 8
    assert _count(onboarding_session, "formas_pagamento", TENANT_A) == 4
    assert _count(onboarding_session, "formas_pagamento", TENANT_B) == 4


def test_onboarding_script_health_check_reports_incomplete_and_complete(
    monkeypatch, capsys, onboarding_session
):
    onboarding_session.execute(
        text("INSERT INTO tenants (id, status) VALUES (:id, 'active')"),
        {"id": TENANT_A},
    )
    onboarding_session.execute(
        text("INSERT INTO tenants (id, status) VALUES (:id, 'active')"),
        {"id": TENANT_B},
    )
    onboarding_session.execute(
        text("INSERT INTO users (tenant_id, is_active) VALUES (:tenant_id, 1)"),
        {"tenant_id": TENANT_A},
    )
    onboarding_session.execute(
        text("INSERT INTO users (tenant_id, is_active) VALUES (:tenant_id, 1)"),
        {"tenant_id": TENANT_B},
    )
    onboarding_session.commit()
    onboard_tenant_defaults(
        onboarding_session, tenant_id=TENANT_A, user_id=1, dry_run=False
    )
    onboarding_session.commit()
    monkeypatch.setattr(
        run_tenant_onboarding,
        "SessionLocal",
        lambda: _SessionProxy(onboarding_session),
    )

    code = run_tenant_onboarding.main(["--health-check"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert code == 1
    assert payload["mode"] == "health_check"
    assert payload["dry_run"] is True
    assert payload["tenant_count"] == 2
    assert payload["complete_count"] == 1
    assert payload["incomplete_count"] == 1
    assert payload["complete_tenants"] == [TENANT_A]
    assert payload["incomplete_tenants"][0]["tenant_id"] == TENANT_B
    assert payload["incomplete_tenants"][0]["would_create"]["payment_methods"] == 4
    assert _count(onboarding_session, "formas_pagamento", TENANT_B) == 0


def test_onboarding_script_health_check_can_include_optional_products(
    monkeypatch, capsys, onboarding_session
):
    onboarding_session.execute(
        text("INSERT INTO tenants (id, status) VALUES (:id, 'active')"),
        {"id": TENANT_A},
    )
    onboarding_session.execute(
        text("INSERT INTO users (tenant_id, is_active) VALUES (:tenant_id, 1)"),
        {"tenant_id": TENANT_A},
    )
    onboarding_session.commit()
    onboard_tenant_defaults(
        onboarding_session, tenant_id=TENANT_A, user_id=1, dry_run=False
    )
    onboarding_session.commit()
    monkeypatch.setattr(
        run_tenant_onboarding,
        "SessionLocal",
        lambda: _SessionProxy(onboarding_session),
    )

    code = run_tenant_onboarding.main(["--health-check", "--include-products"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert code == 1
    assert payload["include_products"] is True
    assert payload["incomplete_count"] == 1
    assert payload["incomplete_tenants"][0]["would_create"]["product_references"] == 3
    assert _count(onboarding_session, "produtos", TENANT_A) == 0


def test_onboarding_script_blocks_production_apply(monkeypatch, capsys):
    monkeypatch.setenv("APP_ENV", "production")

    code = run_tenant_onboarding.main(
        ["--tenant-id", TENANT_A, "--user-id", "1", "--apply"]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert code == 1
    assert payload["dry_run"] is False
    assert "production/prod" in payload["error"]


def test_onboarding_script_health_check_rejects_apply(capsys):
    code = run_tenant_onboarding.main(["--health-check", "--apply"])

    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert code == 1
    assert payload["dry_run"] is True
    assert "somente leitura" in payload["error"]


def test_onboarding_script_future_tenant_check_rejects_apply(capsys):
    code = run_tenant_onboarding.main(["--future-tenant-check", "--apply"])

    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert code == 1
    assert payload["dry_run"] is True
    assert "somente leitura" in payload["error"]


def test_onboarding_script_template_check_reports_contract(
    monkeypatch, capsys, onboarding_session
):
    monkeypatch.setattr(
        run_tenant_onboarding,
        "SessionLocal",
        lambda: _SessionProxy(onboarding_session),
    )

    code = run_tenant_onboarding.main(["--template-check", "--include-products"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert code == 0
    assert payload["ok"] is True
    assert payload["mode"] == "template_contract_check"
    assert payload["template_item_counts"]["payment_method"] == 4
    assert payload["template_item_counts"]["bank_account"] == 2
    assert payload["template_item_counts"]["pet_species"] == 2
    assert payload["template_item_counts"]["ration_line"] == 4
    assert payload["template_item_counts"]["product_reference"] == 3
    assert _count(onboarding_session, "formas_pagamento", TENANT_A) == 0


def test_onboarding_script_template_check_rejects_apply(capsys):
    code = run_tenant_onboarding.main(["--template-check", "--apply"])

    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert code == 1
    assert payload["dry_run"] is True
    assert "somente leitura" in payload["error"]


def test_migration_status_reports_pending_head(monkeypatch, onboarding_session):
    onboarding_session.execute(
        text("CREATE TABLE alembic_version (version_num TEXT NOT NULL)")
    )
    onboarding_session.execute(
        text("INSERT INTO alembic_version (version_num) VALUES ('old_head')")
    )
    onboarding_session.commit()
    monkeypatch.setattr(
        run_tenant_onboarding, "_get_alembic_heads", lambda: ["new_head"]
    )

    status = run_tenant_onboarding._migration_status(onboarding_session)

    assert status["ok"] is False
    assert status["current"] == ["old_head"]
    assert status["heads"] == ["new_head"]
    assert status["pending_heads"] == ["new_head"]
    assert status["extra_current_versions"] == ["old_head"]


def test_onboarding_script_signup_readiness_check_combines_migrations_and_templates(
    monkeypatch,
    capsys,
    onboarding_session,
):
    onboarding_session.execute(
        text("CREATE TABLE alembic_version (version_num TEXT NOT NULL)")
    )
    onboarding_session.execute(
        text("INSERT INTO alembic_version (version_num) VALUES ('test_head')")
    )
    onboarding_session.commit()
    monkeypatch.setattr(
        run_tenant_onboarding,
        "SessionLocal",
        lambda: _SessionProxy(onboarding_session),
    )
    monkeypatch.setattr(
        run_tenant_onboarding, "_get_alembic_heads", lambda: ["test_head"]
    )

    code = run_tenant_onboarding.main(
        ["--signup-readiness-check", "--include-products"]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert code == 0
    assert payload["ok"] is True
    assert payload["mode"] == "signup_readiness_check"
    assert payload["blockers"] == []
    assert payload["migration"]["ok"] is True
    assert payload["template_contract"]["ok"] is True
    assert payload["future_tenant_simulation"]["ok"] is True
    assert _count(onboarding_session, "formas_pagamento", TENANT_A) == 0


def test_onboarding_script_signup_readiness_check_rejects_apply(capsys):
    code = run_tenant_onboarding.main(["--signup-readiness-check", "--apply"])

    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert code == 1
    assert payload["dry_run"] is True
    assert "somente leitura" in payload["error"]
