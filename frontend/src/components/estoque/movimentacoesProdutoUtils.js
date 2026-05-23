function numeroSeguro(valor) {
  const numero = Number(valor || 0);
  return Number.isFinite(numero) ? numero : 0;
}

export function produtoUsaEstoqueVirtual(produto) {
  return (
    produto?.tipo_produto === 'KIT' || produto?.tipo_produto === 'VARIACAO'
  ) && produto?.tipo_kit === 'VIRTUAL';
}

export function resolverEstoqueAtualMovimentacoes(produto) {
  if (produtoUsaEstoqueVirtual(produto)) {
    return numeroSeguro(produto?.estoque_virtual ?? produto?.estoque_disponivel);
  }

  return numeroSeguro(produto?.estoque_atual);
}

export function resolverSaldoDisponivelMovimentacoes(produto) {
  if (produtoUsaEstoqueVirtual(produto)) {
    return numeroSeguro(produto?.estoque_disponivel ?? produto?.estoque_virtual);
  }

  const estoqueAtual = resolverEstoqueAtualMovimentacoes(produto);
  const estoqueReservado = numeroSeguro(produto?.estoque_reservado);
  return estoqueAtual - estoqueReservado;
}
