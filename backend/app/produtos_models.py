# -*- coding: utf-8 -*-
"""Compatibilidade para imports legados dos modelos de produtos."""

from .produtos_catalogo_models import Categoria, Departamento, Marca, Produto
from .produtos_compras_models import (
    NotaEntrada,
    NotaEntradaItem,
    PedidoCompra,
    PedidoCompraItem,
    PedidoCompraNotaEntrada,
    ProdutoHistoricoPreco,
)
from .produtos_estoque_models import (
    CampanhaValidadeAutomatica,
    CampanhaValidadeExclusao,
    EstoqueMovimentacao,
    GranelConversao,
    ListaPreco,
    ProdutoBlingSync,
    ProdutoBlingSyncQueue,
    ProdutoFornecedor,
    ProdutoGranelVinculo,
    ProdutoImagem,
    ProdutoKitComponente,
    ProdutoListaPreco,
    ProdutoLote,
)
from .funcionario_contagem_models import (
    FuncionarioContagem,
    FuncionarioContagemItem,
)
from .produtos_lembretes_variacoes_models import (
    Lembrete,
    ProdutoAtributo,
    ProdutoAtributoOpcao,
    ProdutoVariacaoAtributo,
)

__all__ = [
    "CampanhaValidadeAutomatica",
    "CampanhaValidadeExclusao",
    "Categoria",
    "Departamento",
    "EstoqueMovimentacao",
    "FuncionarioContagem",
    "FuncionarioContagemItem",
    "GranelConversao",
    "Lembrete",
    "ListaPreco",
    "Marca",
    "NotaEntrada",
    "NotaEntradaItem",
    "PedidoCompra",
    "PedidoCompraItem",
    "PedidoCompraNotaEntrada",
    "Produto",
    "ProdutoAtributo",
    "ProdutoAtributoOpcao",
    "ProdutoBlingSync",
    "ProdutoBlingSyncQueue",
    "ProdutoFornecedor",
    "ProdutoGranelVinculo",
    "ProdutoHistoricoPreco",
    "ProdutoImagem",
    "ProdutoKitComponente",
    "ProdutoListaPreco",
    "ProdutoLote",
    "ProdutoVariacaoAtributo",
]
