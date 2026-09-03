export function arredondarDinheiro(valor) {
  const numero = Number(valor);
  if (!Number.isFinite(numero)) return 0;
  return Math.round((numero + Number.EPSILON) * 100) / 100;
}

export const QUANTIDADE_MINIMA_PDV = 0.001;

export function normalizarQuantidadePDV(valor, fallback = 1) {
  if (valor === null || valor === undefined || valor === "") return fallback;

  const valorNormalizado = typeof valor === "string" ? valor.replace(",", ".") : valor;
  const numero = Number(valorNormalizado);

  if (!Number.isFinite(numero)) return fallback;
  return Math.max(QUANTIDADE_MINIMA_PDV, numero);
}

export function obterPrecoVendaPDV(produto) {
  const preco = produto?.preco_venda_pdv ?? produto?.preco_venda_efetivo ?? produto?.preco_venda;
  const numero = Number.parseFloat(preco);
  return Number.isFinite(numero) ? numero : 0;
}

export function colocarItemProdutoNoTopo(itens, itemAtualizado) {
  const outrosItens = itens.filter((item) => item.produto_id !== itemAtualizado.produto_id);
  return [itemAtualizado, ...outrosItens];
}

export function recalcularSubtotalItem(item, novaQuantidade) {
  const quantidade = normalizarQuantidadePDV(novaQuantidade);
  const precoUnitario = Number(item.preco_unitario ?? item.preco_venda ?? 0) || 0;
  const subtotalSemDesconto = precoUnitario * quantidade;
  let novoDescontoValor = Number(item.desconto_valor || 0) || 0;

  if (item.tipo_desconto_aplicado === "percentual" && Number(item.desconto_percentual) > 0) {
    novoDescontoValor = (subtotalSemDesconto * Number(item.desconto_percentual)) / 100;
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

export function prepararItensAposMudancaCarrinho(itens, cupomAtivo = false) {
  if (!cupomAtivo) {
    return {
      itens,
      extras: {},
      cupomInvalidado: false,
    };
  }

  const itensSemDescontoDoCupom = itens.map((item) => {
    const quantidade = normalizarQuantidadePDV(item.quantidade);
    const precoUnitario = Number(item.preco_unitario ?? item.preco_venda ?? 0) || 0;

    return {
      ...item,
      quantidade,
      desconto_valor: 0,
      desconto_item: 0,
      desconto_percentual: 0,
      tipo_desconto_aplicado: null,
      preco_com_desconto: precoUnitario,
      subtotal: arredondarDinheiro(precoUnitario * quantidade),
    };
  });

  return {
    itens: itensSemDescontoDoCupom,
    extras: {
      cupom_code: null,
      cupom_discount_applied: null,
    },
    cupomInvalidado: true,
  };
}
