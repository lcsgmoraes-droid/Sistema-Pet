import os
from pathlib import Path

from sqlalchemy.exc import IntegrityError

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ["DEBUG"] = "false"

from app import usuarios_routes


REPO_ROOT = Path(__file__).resolve().parents[3]


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


def test_criacao_direta_de_usuario_recusa_perfil_cliente():
    role = type("Role", (), {"name": " Cliente "})()

    try:
        usuarios_routes._ensure_role_is_not_cliente(role)
    except usuarios_routes.UserAccountError as exc:
        assert exc.status_code == 400
        assert "reservado" in exc.detail
    else:
        raise AssertionError("Perfil Cliente deveria ser recusado no cadastro direto")


def test_usuarios_routes_contract_vincula_pessoa_operacional():
    source = (REPO_ROOT / "backend/app/usuarios_routes.py").read_text(encoding="utf-8")

    assert "pessoa_id: int | None = None" in source
    assert "Cliente.auth_user_id == User.id" in source
    assert 'tipo_cadastro="funcionario"' in source
    assert 'origem_cliente="cadastro_usuario"' in source
