import os
from types import SimpleNamespace

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL") or "sqlite:///./test.db"
os.environ["DEBUG"] = "false"

from app.produtos.fornecedores import _garantir_fornecedor_principal_quando_unico


class _FakeField:
    def __eq__(self, other):
        return ("eq", other)

    def is_(self, other):
        return ("is", other)

    def asc(self):
        return ("asc", self)


class _FakeProdutoFornecedor:
    produto_id = _FakeField()
    tenant_id = _FakeField()
    ativo = _FakeField()
    id = _FakeField()


class _FakeQuery:
    def __init__(self, all_result):
        self.all_result = all_result

    def filter(self, *expressions):
        return self

    def order_by(self, *expressions):
        return self

    def all(self):
        return self.all_result


class _FakeDb:
    def __init__(self, vinculos):
        self.vinculos = vinculos

    def query(self, *entities):
        return _FakeQuery(self.vinculos)


def test_garantir_fornecedor_principal_quando_unico_promove_unico_vinculo(monkeypatch):
    from app.produtos import fornecedores

    monkeypatch.setattr(fornecedores, "ProdutoFornecedor", _FakeProdutoFornecedor)
    produto = SimpleNamespace(id=10, fornecedor_id=None)
    vinculo = SimpleNamespace(fornecedor_id=77, e_principal=False)

    _garantir_fornecedor_principal_quando_unico(_FakeDb([vinculo]), produto, "tenant-1")

    assert vinculo.e_principal is True
    assert produto.fornecedor_id == 77


def test_garantir_fornecedor_principal_quando_unico_limpa_sem_vinculo(monkeypatch):
    from app.produtos import fornecedores

    monkeypatch.setattr(fornecedores, "ProdutoFornecedor", _FakeProdutoFornecedor)
    produto = SimpleNamespace(id=10, fornecedor_id=77)

    _garantir_fornecedor_principal_quando_unico(_FakeDb([]), produto, "tenant-1")

    assert produto.fornecedor_id is None


def test_garantir_fornecedor_principal_quando_unico_preserva_multiplos(monkeypatch):
    from app.produtos import fornecedores

    monkeypatch.setattr(fornecedores, "ProdutoFornecedor", _FakeProdutoFornecedor)
    produto = SimpleNamespace(id=10, fornecedor_id=77)
    vinculos = [
        SimpleNamespace(fornecedor_id=77, e_principal=True),
        SimpleNamespace(fornecedor_id=88, e_principal=False),
    ]

    _garantir_fornecedor_principal_quando_unico(_FakeDb(vinculos), produto, "tenant-1")

    assert produto.fornecedor_id == 77
    assert [vinculo.e_principal for vinculo in vinculos] == [True, False]
