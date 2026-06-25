from pathlib import Path

from app import produtos_models
from app import produtos_catalogo_models as catalogo
from app import produtos_compras_models as compras
from app import produtos_estoque_models as estoque
from app import produtos_lembretes_variacoes_models as lembretes_variacoes


BACKEND_ROOT = Path(__file__).resolve().parents[2]

EXPECTED_EXPORTS = {
    "Categoria",
    "Marca",
    "Departamento",
    "Produto",
    "ProdutoImagem",
    "ProdutoKitComponente",
    "ProdutoGranelVinculo",
    "GranelConversao",
    "ProdutoLote",
    "CampanhaValidadeAutomatica",
    "CampanhaValidadeExclusao",
    "ProdutoFornecedor",
    "ListaPreco",
    "ProdutoListaPreco",
    "EstoqueMovimentacao",
    "ProdutoBlingSync",
    "ProdutoBlingSyncQueue",
    "PedidoCompra",
    "PedidoCompraNotaEntrada",
    "PedidoCompraItem",
    "NotaEntrada",
    "NotaEntradaItem",
    "ProdutoHistoricoPreco",
    "Lembrete",
    "ProdutoAtributo",
    "ProdutoAtributoOpcao",
    "ProdutoVariacaoAtributo",
}


def _line_count(relative_path: str) -> int:
    return sum(1 for _ in (BACKEND_ROOT / relative_path).open(encoding="utf-8"))


def test_produtos_models_preserva_reexports_legados() -> None:
    assert EXPECTED_EXPORTS <= set(produtos_models.__all__)
    assert produtos_models.Produto is catalogo.Produto
    assert produtos_models.ProdutoLote is estoque.ProdutoLote
    assert produtos_models.EstoqueMovimentacao is estoque.EstoqueMovimentacao
    assert produtos_models.PedidoCompra is compras.PedidoCompra
    assert produtos_models.NotaEntrada is compras.NotaEntrada
    assert produtos_models.Lembrete is lembretes_variacoes.Lembrete
    assert produtos_models.ProdutoAtributo is lembretes_variacoes.ProdutoAtributo


def test_produtos_models_preserva_tabelas_principais() -> None:
    assert produtos_models.Produto.__tablename__ == "produtos"
    assert produtos_models.ProdutoLote.__tablename__ == "produto_lotes"
    assert produtos_models.EstoqueMovimentacao.__tablename__ == "estoque_movimentacoes"
    assert produtos_models.PedidoCompra.__tablename__ == "pedidos_compra"
    assert produtos_models.NotaEntrada.__tablename__ == "notas_entrada"
    assert produtos_models.Lembrete.__tablename__ == "lembretes"
    assert produtos_models.ProdutoAtributo.__tablename__ == "produtos_atributos"


def test_produtos_models_split_mantem_arquivos_focados() -> None:
    limits = {
        "app/produtos_models.py": 100,
        "app/produtos_catalogo_models.py": 700,
        "app/produtos_estoque_models.py": 700,
        "app/produtos_compras_models.py": 700,
        "app/produtos_lembretes_variacoes_models.py": 700,
    }

    for relative_path, max_lines in limits.items():
        assert _line_count(relative_path) < max_lines, relative_path
