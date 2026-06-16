import json

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.scripts import update_user_email


SOURCE_TENANT = "11111111-1111-1111-1111-111111111111"
OLD_EMAIL = "admin@mlprohub.com.br"
NEW_EMAIL = "atacadaopetpp@gmail.com"


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
                email TEXT NOT NULL UNIQUE,
                tenant_id TEXT NOT NULL,
                nome TEXT,
                is_active BOOLEAN,
                is_admin BOOLEAN,
                email_verified BOOLEAN,
                email_verification_token_hash TEXT,
                email_verification_token_expires TEXT,
                email_verification_sent_at TEXT,
                reset_token TEXT,
                reset_token_expires TEXT,
                updated_at TEXT
            )
            """
        )
    )
    session.execute(
        text(
            """
            INSERT INTO users (
                email, tenant_id, nome, is_active, is_admin, email_verified,
                email_verification_token_hash, reset_token
            ) VALUES (
                :email, :tenant, 'Lucas Admin', 1, 1, 1, 'old-verification-token', 'old-reset-token'
            )
            """
        ),
        {"email": OLD_EMAIL, "tenant": SOURCE_TENANT},
    )
    session.commit()
    return session


def test_update_user_email_dry_run_does_not_persist(monkeypatch, capsys):
    session = _script_session()
    monkeypatch.setattr(
        update_user_email, "SessionLocal", lambda: _SessionProxy(session)
    )

    code = update_user_email.main(["--old-email", OLD_EMAIL, "--new-email", NEW_EMAIL])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert code == 0
    assert payload["dry_run"] is True
    assert payload["before"]["email"] == OLD_EMAIL
    assert payload["after"]["email"] == NEW_EMAIL
    assert payload["before"]["id"] == payload["after"]["id"]
    assert payload["before"]["tenant_id"] == payload["after"]["tenant_id"]

    old_row = session.execute(
        text("SELECT id FROM users WHERE email = :email"), {"email": OLD_EMAIL}
    ).first()
    new_row = session.execute(
        text("SELECT id FROM users WHERE email = :email"), {"email": NEW_EMAIL}
    ).first()
    assert old_row is not None
    assert new_row is None
    session.close()


def test_update_user_email_apply_persists_and_clears_pending_tokens(
    monkeypatch, capsys
):
    session = _script_session()
    monkeypatch.setattr(
        update_user_email, "SessionLocal", lambda: _SessionProxy(session)
    )

    code = update_user_email.main(
        [
            "--old-email",
            OLD_EMAIL,
            "--new-email",
            NEW_EMAIL,
            "--expected-tenant-id",
            SOURCE_TENANT,
            "--apply",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert code == 0
    assert payload["dry_run"] is False
    assert payload["after"]["email"] == NEW_EMAIL

    row = (
        session.execute(
            text(
                """
            SELECT id, email, tenant_id, email_verification_token_hash, reset_token
            FROM users
            WHERE id = :id
            """
            ),
            {"id": payload["after"]["id"]},
        )
        .mappings()
        .first()
    )
    assert row["email"] == NEW_EMAIL
    assert row["tenant_id"] == SOURCE_TENANT
    assert row["email_verification_token_hash"] is None
    assert row["reset_token"] is None
    session.close()


def test_update_user_email_rejects_duplicate_new_email(monkeypatch, capsys):
    session = _script_session()
    session.execute(
        text("INSERT INTO users (email, tenant_id) VALUES (:email, :tenant)"),
        {"email": NEW_EMAIL, "tenant": SOURCE_TENANT},
    )
    session.commit()
    monkeypatch.setattr(
        update_user_email, "SessionLocal", lambda: _SessionProxy(session)
    )

    code = update_user_email.main(
        ["--old-email", OLD_EMAIL, "--new-email", NEW_EMAIL, "--apply"]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert code == 1
    assert "ja esta em uso" in payload["error"]
    session.close()


def test_update_user_email_blocks_production_apply_without_override(
    monkeypatch, capsys
):
    monkeypatch.setenv("APP_ENV", "production")

    code = update_user_email.main(
        ["--old-email", OLD_EMAIL, "--new-email", NEW_EMAIL, "--apply"]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert code == 1
    assert payload["dry_run"] is False
    assert "production/prod" in payload["error"]
