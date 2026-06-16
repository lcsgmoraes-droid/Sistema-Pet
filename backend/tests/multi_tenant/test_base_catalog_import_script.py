import json

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.scripts import run_base_catalog_import


SOURCE_TENANT = "11111111-1111-1111-1111-111111111111"
TARGET_TENANT = "22222222-2222-2222-2222-222222222222"


class _SessionProxy:
    def __init__(self, session):
        self._session = session

    def __getattr__(self, name):
        return getattr(self._session, name)

    def close(self):
        return None


def _script_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    session.execute(
        text(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                is_active BOOLEAN
            )
            """
        )
    )
    session.execute(
        text(
            "INSERT INTO users (email, tenant_id, is_active) VALUES ('atacadaopetpp@gmail.com', :tenant, 1)"
        ),
        {"tenant": SOURCE_TENANT},
    )
    session.commit()
    return session


def test_base_catalog_script_defaults_to_dry_run(monkeypatch, capsys):
    session = _script_session()
    calls = []

    def fake_import_base_catalog(**kwargs):
        calls.append(kwargs)
        return {
            "ok": True,
            "dry_run": kwargs["dry_run"],
            "source_tenant_id": kwargs["source_tenant_id"],
            "target_tenant_id": kwargs["target_tenant_id"],
            "would_create": {"produtos": 1},
            "created": {},
            "skipped": {},
            "warnings": [],
            "errors": [],
        }

    monkeypatch.setattr(
        run_base_catalog_import, "SessionLocal", lambda: _SessionProxy(session)
    )
    monkeypatch.setattr(
        run_base_catalog_import, "import_base_catalog", fake_import_base_catalog
    )

    code = run_base_catalog_import.main(
        ["--target-tenant-id", TARGET_TENANT, "--target-user-id", "10"]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert code == 0
    assert payload["dry_run"] is True
    assert payload["source_tenant_id"] == SOURCE_TENANT
    assert payload["target_tenant_id"] == TARGET_TENANT
    assert calls[0]["dry_run"] is True
    assert calls[0]["user_id"] == 10
    session.close()


def test_base_catalog_script_apply_blocks_production_without_override(
    monkeypatch, capsys
):
    monkeypatch.setenv("APP_ENV", "production")

    code = run_base_catalog_import.main(
        ["--target-tenant-id", TARGET_TENANT, "--target-user-id", "10", "--apply"]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert code == 1
    assert payload["dry_run"] is False
    assert "production/prod" in payload["error"]


def test_base_catalog_script_reports_missing_source_email(monkeypatch, capsys):
    session = _script_session()
    monkeypatch.setattr(
        run_base_catalog_import, "SessionLocal", lambda: _SessionProxy(session)
    )

    code = run_base_catalog_import.main(
        [
            "--target-tenant-id",
            TARGET_TENANT,
            "--target-user-id",
            "10",
            "--source-email",
            "naoexiste@example.com",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert code == 1
    assert payload["dry_run"] is True
    assert "Usuario fonte nao encontrado" in payload["error"]
    session.close()
