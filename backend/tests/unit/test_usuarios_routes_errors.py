import os

from sqlalchemy.exc import IntegrityError

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ["DEBUG"] = "false"

from app import usuarios_routes


class _FakeExecuteResult:
    def __init__(self, row):
        self._row = row

    def first(self):
        return self._row


class _FakeDb:
    def __init__(self, row):
        self.row = row
        self.statement = None
        self.params = None

    def execute(self, statement, params):
        self.statement = str(statement)
        self.params = params
        return _FakeExecuteResult(self.row)


def test_email_ja_cadastrado_globalmente_consulta_users_sem_filtro_de_tenant():
    db = _FakeDb(row=(123,))

    exists = usuarios_routes._email_ja_cadastrado_globalmente(
        db,
        "usuario@empresa.com.br",
    )

    assert exists is True
    assert "FROM users" in db.statement
    assert "lower(email)" in db.statement
    assert db.params == {"email": "usuario@empresa.com.br"}


def test_email_ja_cadastrado_globalmente_retorna_false_sem_linha():
    db = _FakeDb(row=None)

    assert (
        usuarios_routes._email_ja_cadastrado_globalmente(
            db,
            "novo@empresa.com.br",
        )
        is False
    )


def test_is_unique_email_violation_reconhece_constraint_de_email():
    exc = IntegrityError(
        "INSERT INTO users",
        {},
        Exception('duplicate key value violates unique constraint "users_email_key"'),
    )

    assert usuarios_routes._is_unique_email_violation(exc) is True
