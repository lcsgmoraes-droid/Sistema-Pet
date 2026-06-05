export function arredondarDinheiro(valor) {
  const numero = Number(valor);
  if (!Number.isFinite(numero)) return 0;
  return Math.round((numero + Number.EPSILON) * 100) / 100;
}

export function obterPrecoVendaPDV(produto) {
  const preco =
    produto?.preco_venda_pdv ??
    produto?.preco_venda_efetivo ??
    produto?.preco_venda;
  const numero = Number.parseFloat(preco);
  return Number.isFinite(numero) ? numero : 0;
}

export function recalcularSubtotalItem(item, novaQuantidade) {
  const quantidade = Math.max(1, Number(novaQuantidade) || 1);
  const precoUnitario = Number(item.preco_unitario ?? item.preco_venda ?? 0) || 0;
  const subtotalSemDesconto = precoUnitario * quantidade;
  let novoDescontoValor = Number(item.desconto_valor || 0) || 0;

  if (
    item.tipo_desconto_aplicado === "percentual" &&
    Number(item.desconto_percentual) > 0
  ) {
    novoDescontoValor =
      (subtotalSemDesconto * Number(item.desconto_percentual)) / 100;
  }

  novoDescontoValor = Math.min(novoDescontoValor, subtotalSemDesconto);

  return {
    ...item,
    quantidade,
    preco_unitario: precoUnitario,
    desconto_valor: arredondarDinheiro(novoDescontoValor),
    subtotal: arredondarDinheiro(subtotalSemDesconto - novoDescontoValor),
  };
}
