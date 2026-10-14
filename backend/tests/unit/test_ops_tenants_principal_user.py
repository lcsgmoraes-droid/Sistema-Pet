from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.services.ops_tenants_read_service import _principal_user


def test_principal_user_prefers_active_user_after_account_move():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(
            text("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                tenant_id TEXT,
                email TEXT,
                nome TEXT,
                is_active BOOLEAN,
                is_admin BOOLEAN,
                email_verified BOOLEAN,
                last_login_at TEXT
            )
        """)
        )
        connection.execute(
            text("""
            CREATE TABLE user_tenants (
                user_id INTEGER,
                tenant_id TEXT,
                is_active BOOLEAN
            )
        """)
        )
        connection.execute(
            text("""
            INSERT INTO users VALUES
            (48, 'andradina', NULL, 'Historico', 0, 0, 1, NULL),
            (49, 'andradina', 'viralata.andradina@hotmail.com', 'Mariana', 1, 0, 1, NULL),
            (50, 'tres-lagoas', 'viralatatl067@gmail.com', 'Silvio', 1, 0, 1, NULL)
        """)
        )
        connection.execute(
            text("""
            INSERT INTO user_tenants VALUES
            (48, 'andradina', 0),
            (49, 'andradina', 1),
            (50, 'tres-lagoas', 1)
        """)
        )

    with Session(engine) as db:
        andradina = _principal_user(db, "andradina")
        tres_lagoas = _principal_user(db, "tres-lagoas")

    assert andradina["email"] == "viralata.andradina@hotmail.com"
    assert tres_lagoas["email"] == "viralatatl067@gmail.com"
