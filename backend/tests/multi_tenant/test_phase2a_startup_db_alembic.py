import importlib
import importlib.util
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy import event
from sqlalchemy.orm import Session


def _listeners(event_name):
    return list(getattr(Session.dispatch, event_name)._clslevel.get(Session, ()))


def _semantic_listener_count(event_name, module_name, function_name):
    return sum(
        1
        for listener in _listeners(event_name)
        if getattr(listener, "__module__", None) == module_name
        and getattr(listener, "__name__", None) == function_name
    )


def _sqlite_engine_with_alembic_version(version="phase2a_head"):
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(64) NOT NULL)"))
        conn.execute(
            text("INSERT INTO alembic_version (version_num) VALUES (:version)"),
            {"version": version},
        )
    return engine


def _set_runtime_environment(monkeypatch, environment, debug="false"):
    for name in ("ENVIRONMENT", "ENV", "APP_ENV"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DEBUG", debug)
    monkeypatch.setenv("ENVIRONMENT", environment)


def _raise_head_error(*_args, **_kwargs):
    raise RuntimeError("head unavailable")


def test_app_main_imports_with_debug_false_and_runtime_modules_loaded(monkeypatch):
    monkeypatch.setenv("DEBUG", "false")

    main = importlib.import_module("app.main")
    db_package = importlib.import_module("app.db")
    models = importlib.import_module("app.models")
    produtos_models = importlib.import_module("app.produtos_models")
    tenant_filters = importlib.import_module("app.tenancy.filters")
    orm_guards = importlib.import_module("app.database.orm_guards")

    assert main.DEBUG is False
    assert hasattr(main, "app")
    assert models.User.metadata is db_package.Base.metadata
    assert produtos_models.Produto.__table__.metadata is db_package.Base.metadata
    assert event.contains(Session, "do_orm_execute", tenant_filters._add_tenant_filter)
    assert event.contains(Session, "before_flush", orm_guards.force_identity_ids)


def test_database_url_allows_sqlite_only_in_local_or_test_environments(monkeypatch):
    config = importlib.import_module("app.config")

    for name in ("APP_ENV", "ENVIRONMENT", "ENV"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.db")
    monkeypatch.setenv("ENVIRONMENT", "testing")

    assert config.get_database_url() == "sqlite:///./test.db"

    monkeypatch.setenv("ENVIRONMENT", "production")

    with pytest.raises(RuntimeError, match="SQLite is allowed only"):
        config.get_database_url()


def test_db_exports_canonical_identity_and_reimport_does_not_create_engine():
    db_package = importlib.import_module("app.db")
    db_core = importlib.import_module("app.db.core")
    produtos_models = importlib.import_module("app.produtos_models")

    assert db_package.Base is db_core.Base
    assert db_package.engine is db_core.engine
    assert db_package.SessionLocal is db_core.SessionLocal
    assert db_package.SessionLocal.kw["bind"] is db_package.engine
    assert produtos_models.Produto.__table__.metadata is db_package.Base.metadata

    engine_before = db_package.engine
    sessionlocal_before = db_package.SessionLocal
    reimported = importlib.import_module("app.db")
    reloaded = importlib.reload(db_package)

    assert reimported.engine is engine_before
    assert reloaded.engine is engine_before
    assert reloaded.SessionLocal is sessionlocal_before
    assert "backend.app.db" not in sys.modules


def test_db_py_compat_wrapper_reexports_canonical_objects():
    db_core = importlib.import_module("app.db.core")
    db_py_path = Path(__file__).resolve().parents[2] / "app" / "db.py"

    spec = importlib.util.spec_from_file_location("_phase2a_db_compat", db_py_path)
    compat_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(compat_module)

    assert compat_module.Base is db_core.Base
    assert compat_module.engine is db_core.engine
    assert compat_module.SessionLocal is db_core.SessionLocal
    assert compat_module.get_session is db_core.get_session


def test_hooks_are_unique_after_db_and_main_reimports():
    db_package = importlib.import_module("app.db")
    tenant_filters = importlib.import_module("app.tenancy.filters")
    orm_guards = importlib.import_module("app.database.orm_guards")

    importlib.import_module("app.main")
    importlib.import_module("app.main")
    importlib.reload(db_package)
    tenant_filters = importlib.reload(tenant_filters)
    orm_guards = importlib.reload(orm_guards)

    assert event.contains(Session, "do_orm_execute", tenant_filters._add_tenant_filter)
    assert event.contains(Session, "before_flush", orm_guards.force_identity_ids)
    assert (
        _semantic_listener_count(
            "do_orm_execute",
            "app.tenancy.filters",
            "_add_tenant_filter",
        )
        == 1
    )
    assert (
        _semantic_listener_count(
            "before_flush",
            "app.database.orm_guards",
            "force_identity_ids",
        )
        == 1
    )


def test_alembic_external_import_is_lazy_and_explicit():
    migration_check = importlib.import_module("app.db.migration_check")

    assert hasattr(migration_check, "ensure_db_ready")
    try:
        config_cls, script_directory_cls, migration_context_cls = migration_check._load_external_alembic()
    except RuntimeError as exc:
        assert "backend/alembic" in str(exc)
        assert "pacote externo" in str(exc).lower()
    else:
        assert config_cls.__module__ == "alembic.config"
        assert script_directory_cls.__module__ == "alembic.script.base"
        assert migration_context_cls.__module__ == "alembic.runtime.migration"


def test_ensure_db_ready_fail_closed_when_alembic_head_fails_in_production(monkeypatch):
    migration_check = importlib.import_module("app.db.migration_check")
    engine = _sqlite_engine_with_alembic_version()
    _set_runtime_environment(monkeypatch, "production", debug="true")
    monkeypatch.setattr(migration_check, "_get_alembic_head", _raise_head_error)

    with pytest.raises(migration_check.DatabaseMigrationError) as exc_info:
        migration_check.ensure_db_ready(engine)

    message = str(exc_info.value)
    assert "Could not determine Alembic head" in message
    assert "guaranteeing that database migrations are up to date" in message
    assert "PYTHONPATH" in message
    assert "alembic upgrade head" in message


def test_ensure_db_ready_fail_closed_when_alembic_head_fails_in_staging(monkeypatch):
    migration_check = importlib.import_module("app.db.migration_check")
    engine = _sqlite_engine_with_alembic_version()
    _set_runtime_environment(monkeypatch, "staging")
    monkeypatch.setattr(migration_check, "_get_alembic_head", _raise_head_error)

    with pytest.raises(migration_check.DatabaseMigrationError) as exc_info:
        migration_check.ensure_db_ready(engine)

    assert "Could not determine Alembic head" in str(exc_info.value)
    assert "alembic upgrade head" in str(exc_info.value)


@pytest.mark.parametrize("environment", ["development", "test"])
def test_ensure_db_ready_tolerates_alembic_head_failure_only_in_dev_or_test(
    monkeypatch,
    caplog,
    environment,
):
    migration_check = importlib.import_module("app.db.migration_check")
    engine = _sqlite_engine_with_alembic_version()
    _set_runtime_environment(monkeypatch, environment)
    monkeypatch.setattr(migration_check, "_get_alembic_head", _raise_head_error)

    caplog.set_level("WARNING", logger=migration_check.logger.name)

    migration_check.ensure_db_ready(engine)

    assert "Could not determine Alembic head" in caplog.text
    assert "Skipping head comparison only because this environment is development/test/local" in caplog.text
