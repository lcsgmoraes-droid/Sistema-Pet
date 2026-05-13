from collections.abc import Callable

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker


TENANT_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
TENANT_B = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"


def make_dre_session(seed_data: Callable[[Session], None]) -> Session:
    engine = create_engine("sqlite:///:memory:")
    session_factory = sessionmaker(bind=engine)
    db = session_factory()
    create_dre_link_schema(db)
    seed_data(db)
    db.commit()
    return db


def create_dre_link_schema(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                tenant_id TEXT NULL,
                nome TEXT NULL,
                email TEXT NULL,
                documento TEXT NULL
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE dre_periodos (
                id INTEGER PRIMARY KEY,
                tenant_id TEXT NULL,
                usuario_id INTEGER NULL,
                data_inicio DATE NULL,
                data_fim DATE NULL,
                mes INTEGER NULL,
                ano INTEGER NULL,
                canal TEXT NULL
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE dre_detalhe_canais (
                id INTEGER PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                usuario_id INTEGER NULL,
                data_inicio DATE NULL,
                data_fim DATE NULL,
                mes INTEGER NULL,
                ano INTEGER NULL,
                canal TEXT NULL,
                receita_bruta NUMERIC NULL
            )
            """
        )
    )


def seed_sensitive_dre_users(db: Session) -> None:
    db.execute(
        text(
            """
            INSERT INTO users (id, tenant_id, nome, email, documento)
            VALUES
                (1, :tenant_a, 'SENSITIVE_NAME_A', 'SENSITIVE_EMAIL_A', 'SENSITIVE_DOC_A'),
                (2, :tenant_b, 'SENSITIVE_NAME_B', 'SENSITIVE_EMAIL_B', 'SENSITIVE_DOC_B')
            """
        ),
        {"tenant_a": TENANT_A, "tenant_b": TENANT_B},
    )
