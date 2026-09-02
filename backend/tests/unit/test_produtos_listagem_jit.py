import os
from types import SimpleNamespace

import pytest

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL") or "sqlite:///./test.db"
os.environ["DEBUG"] = "false"

from app.produtos import listagem_routes as produtos_listagem_routes


class _FakeJitDb:
    def __init__(self, dialect_name):
        self.bind = SimpleNamespace(dialect=SimpleNamespace(name=dialect_name))
        self.executed = []

    def get_bind(self):
        return self.bind

    def execute(self, statement):
        self.executed.append(str(statement))


def test_busca_rapida_produtos_desativa_jit_apenas_na_transacao_postgres():
    db = _FakeJitDb("postgresql")

    produtos_listagem_routes._desativar_jit_busca_rapida_produtos(
        db,
        termo_busca="special dog",
        contar_total=False,
    )

    assert db.executed == ["SET LOCAL jit = off"]


@pytest.mark.parametrize(
    ("dialect_name", "termo_busca", "contar_total"),
    [
        ("sqlite", "special dog", False),
        ("postgresql", "", False),
        ("postgresql", "special dog", True),
    ],
)
def test_busca_produtos_nao_altera_jit_fora_do_autocomplete_postgres(
    dialect_name,
    termo_busca,
    contar_total,
):
    db = _FakeJitDb(dialect_name)

    produtos_listagem_routes._desativar_jit_busca_rapida_produtos(
        db,
        termo_busca=termo_busca,
        contar_total=contar_total,
    )

    assert db.executed == []
