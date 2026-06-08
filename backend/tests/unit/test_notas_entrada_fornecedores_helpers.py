import os
from types import SimpleNamespace

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL") or "sqlite:///./test.db"
os.environ["DEBUG"] = "false"

from app.notas_entrada import fornecedores  # noqa: E402


class _FakeQuery:
    def __init__(self, resultado=None):
        self.resultado = resultado

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.resultado


class _FakeDb:
    def __init__(self, resultado=None):
        self.resultado = resultado
        self.adicionado = None
        self.commits = 0

    def query(self, *_args, **_kwargs):
        return _FakeQuery(self.resultado)

    def add(self, obj):
        self.adicionado = obj

    def commit(self):
        self.commits += 1

    def refresh(self, _obj):
        return None


class _FakeColumn:
    def __eq__(self, _other):
        return True


class _FakeCliente:
    cnpj = _FakeColumn()
    tenant_id = _FakeColumn()

    def __init__(self, **kwargs):
        for chave, valor in kwargs.items():
            setattr(self, chave, valor)


def test_gerar_prefixo_fornecedor_remove_palavras_comuns():
    assert fornecedores.gerar_prefixo_fornecedor("Reino das Aves LTDA") == "RA"
    assert fornecedores.gerar_prefixo_fornecedor("Megazoo") == "MEG"


def test_criar_fornecedor_automatico_cria_com_codigo_user_e_tenant(monkeypatch):
    monkeypatch.setattr(
        fornecedores,
        "gerar_codigo_cliente",
        lambda db, tipo, pessoa, tenant_id: f"{tipo}-{pessoa}-{tenant_id}",
    )
    monkeypatch.setattr(fornecedores, "Cliente", _FakeCliente)
    db = _FakeDb()
    current_user = SimpleNamespace(id=42)

    fornecedor, criado = fornecedores.criar_fornecedor_automatico(
        {
            "fornecedor_cnpj": "63287129000495",
            "fornecedor_nome": "SPECIAL DOG PET FOOD LTDA",
            "fornecedor_fantasia": "Special Dog",
            "fornecedor_ie": "123",
            "fornecedor_endereco": "Rua A",
            "fornecedor_numero": "10",
            "fornecedor_bairro": "Centro",
            "fornecedor_cidade": "Presidente Prudente",
            "fornecedor_uf": "SP",
            "fornecedor_cep": "19000000",
            "fornecedor_telefone": "18999999999",
        },
        db,
        current_user,
        tenant_id=7,
    )

    assert criado is True
    assert db.adicionado is fornecedor
    assert db.commits == 1
    assert fornecedor.codigo == "fornecedor-PJ-7"
    assert fornecedor.user_id == 42
    assert fornecedor.tenant_id == 7
    assert fornecedor.tipo_cadastro == "fornecedor"
    assert fornecedor.nome_fantasia == "Special Dog"
