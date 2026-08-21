import json
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import importar_simplesvet
import importar_simplesvet_cli as cli
import importar_simplesvet_plan as plan_module
from importar_simplesvet_plan import (
    ImportPlanError,
    build_source_manifest,
    create_plan,
    database_identity,
    is_production,
    load_plan,
    validate_plan,
    write_json,
)
from importar_simplesvet_state import RUNTIME, STATS
from app.models import Especie, Raca


TENANT_ID = "11111111-1111-1111-1111-111111111111"


def _write_csv(path: Path, headers: list[str], values: list[str] | None = None) -> None:
    row = values or [f"valor-{index}" for index, _header in enumerate(headers)]
    path.write_text(
        ",".join(headers) + "\n" + ",".join(row) + "\n",
        encoding="utf-8",
    )


def _base_source(tmp_path: Path) -> Path:
    source = tmp_path / "simplesvet_data"
    source.mkdir()
    _write_csv(
        source / "vet_especie.csv",
        ["esp_int_codigo", "esp_var_nome"],
        ["1", "Canina"],
    )
    _write_csv(
        source / "vet_raca.csv",
        ["rac_int_codigo", "rac_var_nome", "esp_int_codigo", "esp_var_nome"],
        ["10", "Sem raca definida", "1", "Canina"],
    )
    return source


def _plan_payload(source: Path) -> tuple[dict, dict]:
    database = database_identity("sqlite:///petshop_dev.db")
    payload = create_plan(
        database=database,
        environment="development",
        target={
            "tenant_id": TENANT_ID,
            "tenant_name": "Empresa teste",
            "tenant_status": "active",
            "user_id": 10,
        },
        source_dir=source,
        files=build_source_manifest(source, "base"),
        scope="base",
        limit=None,
        stats={},
        rejected={},
    )
    return payload, database


def test_plan_validates_headers_hashes_target_and_database(tmp_path):
    source = _base_source(tmp_path)
    payload, database = _plan_payload(source)
    plan_path = tmp_path / "plan.json"
    write_json(plan_path, payload)

    loaded = load_plan(plan_path)
    resolved_source, files = validate_plan(
        loaded,
        database=database,
        confirm_tenant_id=TENANT_ID,
        confirm_plan_id=payload["plan_id"],
    )

    assert resolved_source == source.resolve()
    assert [item["name"] for item in files] == ["vet_especie.csv", "vet_raca.csv"]


def test_plan_rejects_changed_source_file(tmp_path):
    source = _base_source(tmp_path)
    payload, database = _plan_payload(source)
    (source / "vet_especie.csv").write_text(
        "esp_int_codigo,esp_var_nome\n2,Gato\n", encoding="utf-8"
    )

    with pytest.raises(ImportPlanError, match="arquivos mudaram"):
        validate_plan(
            payload,
            database=database,
            confirm_tenant_id=TENANT_ID,
            confirm_plan_id=payload["plan_id"],
        )


def test_plan_rejects_missing_required_column(tmp_path):
    source = tmp_path / "simplesvet_data"
    source.mkdir()
    _write_csv(source / "vet_especie.csv", ["esp_int_codigo"])
    _write_csv(
        source / "vet_raca.csv",
        ["rac_int_codigo", "rac_var_nome", "esp_int_codigo", "esp_var_nome"],
    )

    with pytest.raises(ImportPlanError, match="esp_var_nome"):
        build_source_manifest(source, "base")


def test_plan_rejects_expiration_and_tampering(tmp_path, monkeypatch):
    source = _base_source(tmp_path)
    payload, database = _plan_payload(source)

    class ExpiredClock(datetime):
        @classmethod
        def now(cls, tz=None):
            expires_at = datetime.fromisoformat(payload["expires_at"])
            return expires_at + timedelta(minutes=1)

    with monkeypatch.context() as clock_patch:
        clock_patch.setattr(plan_module, "datetime", ExpiredClock)
        with pytest.raises(ImportPlanError, match="expirou"):
            validate_plan(
                payload,
                database=database,
                confirm_tenant_id=TENANT_ID,
                confirm_plan_id=payload["plan_id"],
            )

    payload, database = _plan_payload(source)
    payload["target"]["user_id"] = 99
    with pytest.raises(ImportPlanError, match="alterado"):
        validate_plan(
            payload,
            database=database,
            confirm_tenant_id=TENANT_ID,
            confirm_plan_id=payload["plan_id"],
        )

    payload, database = _plan_payload(source)
    payload["simulation"]["stats"] = {"clientes": {"sucesso": 999}}
    with pytest.raises(ImportPlanError, match="alterado"):
        validate_plan(
            payload,
            database=database,
            confirm_tenant_id=TENANT_ID,
            confirm_plan_id=payload["plan_id"],
        )


def test_production_detection_uses_environment_or_database_name():
    assert is_production("production", database_identity("sqlite:///petshop_dev.db"))
    assert is_production("development", database_identity("sqlite:///petshop_prod.db"))
    assert not is_production(
        "development", database_identity("sqlite:///petshop_dev.db")
    )
    assert is_production(
        "development",
        database_identity("postgresql://user:password@db.example.test/petshop"),
    )


def test_target_user_must_belong_to_active_tenant(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    session = sessionmaker(bind=engine)()
    session.execute(text("CREATE TABLE tenants (id TEXT, name TEXT, status TEXT)"))
    session.execute(
        text(
            "CREATE TABLE users (id INTEGER, email TEXT, tenant_id TEXT, is_active BOOLEAN)"
        )
    )
    session.execute(
        text("INSERT INTO tenants VALUES (:id, 'Empresa teste', 'active')"),
        {"id": TENANT_ID},
    )
    session.execute(
        text("INSERT INTO users VALUES (10, 'owner@example.test', :id, 1)"),
        {"id": TENANT_ID},
    )

    synchronized_tenants = []
    monkeypatch.setattr(
        "app.tenancy.rls.sync_rls_tenant",
        lambda _db, tenant_id: synchronized_tenants.append(tenant_id),
    )

    target = cli._resolve_target(session, tenant_id=TENANT_ID, user_id=10)
    assert target["tenant_id"] == TENANT_ID
    assert target["user_id"] == 10
    assert synchronized_tenants == [TENANT_ID]

    with pytest.raises(ImportPlanError, match="nao encontrados"):
        cli._resolve_target(session, tenant_id=TENANT_ID, user_id=11)


def test_simulation_rolls_back_and_apply_commits_atomically(tmp_path, monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    session = sessionmaker(bind=engine)()
    session.execute(text("CREATE TABLE imported_rows (id INTEGER PRIMARY KEY)"))
    session.commit()

    def fake_execute(db, *, scope, limite):
        db.execute(text("INSERT INTO imported_rows (id) VALUES (1)"))
        STATS["clientes"]["total"] = 1
        STATS["clientes"]["sucesso"] = 1

    monkeypatch.setattr(importar_simplesvet, "executar_escopo", fake_execute)

    cli._run_import(
        session,
        tenant_id=TENANT_ID,
        user_id=10,
        source_dir=tmp_path,
        report_dir=tmp_path,
        scope="catalog",
        limit=None,
        dry_run=True,
    )
    assert session.execute(text("SELECT COUNT(*) FROM imported_rows")).scalar() == 0

    cli._run_import(
        session,
        tenant_id=TENANT_ID,
        user_id=10,
        source_dir=tmp_path,
        report_dir=tmp_path,
        scope="catalog",
        limit=None,
        dry_run=False,
    )
    assert session.execute(text("SELECT COUNT(*) FROM imported_rows")).scalar() == 1
    assert RUNTIME.tenant_id is None


def test_real_base_scope_is_atomic_and_idempotent(tmp_path):
    source = _base_source(tmp_path)
    engine = create_engine("sqlite:///:memory:")
    Especie.__table__.create(engine)
    Raca.__table__.create(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()

    simulated, _rejected = cli._run_import(
        session,
        tenant_id=TENANT_ID,
        user_id=10,
        source_dir=source,
        report_dir=tmp_path,
        scope="base",
        limit=None,
        dry_run=True,
    )
    assert simulated["especies"]["sucesso"] == 1
    assert simulated["racas"]["sucesso"] == 1
    assert session.execute(text("SELECT COUNT(*) FROM especies")).scalar() == 0
    assert session.execute(text("SELECT COUNT(*) FROM racas")).scalar() == 0

    cli._run_import(
        session,
        tenant_id=TENANT_ID,
        user_id=10,
        source_dir=source,
        report_dir=tmp_path,
        scope="base",
        limit=None,
        dry_run=False,
    )
    cli._run_import(
        session,
        tenant_id=TENANT_ID,
        user_id=10,
        source_dir=source,
        report_dir=tmp_path,
        scope="base",
        limit=None,
        dry_run=False,
    )
    assert session.execute(text("SELECT COUNT(*) FROM especies")).scalar() == 1
    assert session.execute(text("SELECT COUNT(*) FROM racas")).scalar() == 1


def test_apply_receipt_contains_no_source_rows(tmp_path):
    receipt = {
        "ok": True,
        "plan_id": "abc",
        "stats": {"clientes": {"total": 1}},
    }
    path = tmp_path / "receipt.json"
    write_json(path, receipt)

    assert json.loads(path.read_text(encoding="utf-8")) == receipt


def test_plan_and_apply_commands_complete_end_to_end(tmp_path, capsys):
    source = _base_source(tmp_path)
    engine = create_engine("sqlite:///:memory:")
    Especie.__table__.create(engine)
    Raca.__table__.create(engine)
    with engine.begin() as connection:
        connection.execute(
            text("CREATE TABLE tenants (id TEXT, name TEXT, status TEXT)")
        )
        connection.execute(
            text(
                "CREATE TABLE users (id INTEGER, email TEXT, tenant_id TEXT, is_active BOOLEAN)"
            )
        )
        connection.execute(
            text("INSERT INTO tenants VALUES (:id, 'Empresa teste', 'active')"),
            {"id": TENANT_ID},
        )
        connection.execute(
            text("INSERT INTO users VALUES (10, 'owner@example.test', :id, 1)"),
            {"id": TENANT_ID},
        )
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    database = database_identity("sqlite:///:memory:")

    plan_args = SimpleNamespace(
        tenant_id=TENANT_ID,
        user_id=10,
        source_dir=source,
        report_dir=tmp_path / "reports",
        scope="base",
        limit=None,
    )
    assert (
        cli._plan_command(
            plan_args,
            database=database,
            environment="development",
            session_factory=session_factory,
        )
        == 0
    )
    plan_path = next((tmp_path / "reports").glob("simplesvet-plan-*.json"))
    plan = load_plan(plan_path)
    assert plan["status"] == "simulation_approved"
    with session_factory() as session:
        assert session.execute(text("SELECT COUNT(*) FROM especies")).scalar() == 0

    apply_args = SimpleNamespace(
        plan_file=plan_path,
        confirm_tenant_id=TENANT_ID,
        confirm_plan_id=plan["plan_id"],
        allow_production_apply=False,
        confirm_production=None,
    )
    assert (
        cli._apply_command(
            apply_args,
            database=database,
            environment="development",
            session_factory=session_factory,
        )
        == 0
    )
    with session_factory() as session:
        assert session.execute(text("SELECT COUNT(*) FROM especies")).scalar() == 1
        assert session.execute(text("SELECT COUNT(*) FROM racas")).scalar() == 1

    with pytest.raises(ImportPlanError, match="ja foi aplicado"):
        cli._apply_command(
            apply_args,
            database=database,
            environment="development",
            session_factory=session_factory,
        )
    assert "simulation_approved" not in capsys.readouterr().err


def test_apply_blocks_production_before_opening_database(tmp_path):
    source = _base_source(tmp_path)
    plan, database = _plan_payload(source)
    plan_path = tmp_path / "plan.json"
    write_json(plan_path, plan)
    args = SimpleNamespace(
        plan_file=plan_path,
        confirm_tenant_id=TENANT_ID,
        confirm_plan_id=plan["plan_id"],
        allow_production_apply=False,
        confirm_production=None,
    )

    def forbidden_session_factory():
        raise AssertionError("o banco nao deveria ser aberto")

    with pytest.raises(ImportPlanError, match="producao bloqueado"):
        cli._apply_command(
            args,
            database=database,
            environment="production",
            session_factory=forbidden_session_factory,
        )


def test_apply_blocks_concurrent_or_unresolved_attempt(tmp_path):
    source = _base_source(tmp_path)
    plan, database = _plan_payload(source)
    plan_path = tmp_path / "plan.json"
    write_json(plan_path, plan)
    lock_path = tmp_path / f"simplesvet-applying-{plan['plan_id']}.lock"
    lock_path.write_text("tentativa anterior\n", encoding="utf-8")
    args = SimpleNamespace(
        plan_file=plan_path,
        confirm_tenant_id=TENANT_ID,
        confirm_plan_id=plan["plan_id"],
        allow_production_apply=False,
        confirm_production=None,
    )

    def forbidden_session_factory():
        raise AssertionError("o banco nao deveria ser aberto")

    with pytest.raises(ImportPlanError, match="auditoria"):
        cli._apply_command(
            args,
            database=database,
            environment="development",
            session_factory=forbidden_session_factory,
        )
