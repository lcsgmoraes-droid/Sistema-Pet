from types import SimpleNamespace

from app.estoque.service import EstoqueService
from app.produtos.schemas import ProdutoCreate, ProdutoUpdate
from app.produtos_models import Produto


class _ProdutoQuery:
    def __init__(self, produto):
        self.produto = produto

    def get(self, produto_id):
        if self.produto and self.produto.id == produto_id:
            return self.produto
        return None


class _FakeDB:
    def __init__(self, produto):
        self.produto = produto

    def query(self, model):
        assert model is Produto
        return _ProdutoQuery(self.produto)


def test_produto_schemas_preservam_tipo_comercial():
    create = ProdutoCreate(
        codigo="CONS-001",
        nome="Consulta clinica",
        tipo="servico",
        preco_venda=120,
    )
    update = ProdutoUpdate(tipo="ambos")
    update_com_acento = ProdutoUpdate(tipo="servi\u00e7o")

    assert create.model_dump().get("tipo") == "servico"
    assert update.model_dump(exclude_none=True).get("tipo") == "produto_servico"
    assert update_com_acento.model_dump(exclude_none=True).get("tipo") == "servico"


def test_validar_disponibilidade_nao_considera_servico_estocavel():
    produto = SimpleNamespace(
        id=10,
        nome="Consulta clinica",
        tipo="servico",
        estoque_atual=99,
    )

    resultado = EstoqueService.validar_disponibilidade(10, 1, _FakeDB(produto))

    assert resultado["disponivel"] is False
    assert resultado["estoque_atual"] == 0
    assert "servico" in resultado["mensagem"].lower()
