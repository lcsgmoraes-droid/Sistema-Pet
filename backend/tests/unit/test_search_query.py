import os
from types import SimpleNamespace

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.utils.search_query import desativar_jit_busca


class _FakeDb:
    def __init__(self, dialect_name):
        self.bind = SimpleNamespace(dialect=SimpleNamespace(name=dialect_name))
        self.executed = []

    def get_bind(self):
        return self.bind

    def execute(self, statement):
        self.executed.append(str(statement))


def test_busca_postgres_desativa_jit_apenas_na_transacao():
    db = _FakeDb("postgresql")

    desativar_jit_busca(db, "special dog")

    assert db.executed == ["SET LOCAL jit = off"]


@pytest.mark.parametrize(
    ("dialect_name", "termo_busca"),
    [
        ("postgresql", None),
        ("postgresql", ""),
        ("postgresql", " \t\n "),
        ("sqlite", "special dog"),
        ("mysql", "special dog"),
    ],
)
def test_busca_vazia_ou_outro_banco_nao_altera_jit(dialect_name, termo_busca):
    db = _FakeDb(dialect_name)

    desativar_jit_busca(db, termo_busca)

    assert db.executed == []


@pytest.mark.parametrize("fim_transacao", ["commit", "rollback"])
@pytest.mark.skipif(
    make_url(os.environ.get("DATABASE_URL", "sqlite://")).get_backend_name()
    != "postgresql",
    reason="Nao precisa criar schema SQLite para verificar SET LOCAL do PostgreSQL",
)
def test_jit_postgres_restaura_configuracao_apos_transacao(db_engine, fim_transacao):
    if db_engine.dialect.name != "postgresql":
        pytest.skip("SET LOCAL jit precisa de PostgreSQL real")

    # Mantem a mesma conexao fisica depois do commit/rollback, para que o pool
    # nao esconda um eventual vazamento da configuracao na sessao original.
    with db_engine.connect() as connection, db_engine.connect() as other_connection:
        jit_original = connection.execute(text("SHOW jit")).scalar_one()
        connection.rollback()
        jit_outra_sessao = other_connection.execute(text("SHOW jit")).scalar_one()
        other_connection.rollback()

        with Session(bind=connection) as db:
            desativar_jit_busca(db, "special dog")

            assert db.execute(text("SHOW jit")).scalar_one() == "off"
            assert (
                other_connection.execute(text("SHOW jit")).scalar_one()
                == jit_outra_sessao
            )
            other_connection.rollback()

            getattr(db, fim_transacao)()

        assert connection.execute(text("SHOW jit")).scalar_one() == jit_original
        connection.rollback()
