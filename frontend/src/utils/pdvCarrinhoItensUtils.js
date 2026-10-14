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
  // A venda e o estoque armazenam tres casas decimais. Calcula o subtotal
  // com o mesmo peso que sera salvo, inclusive quando informado pelo valor.
  return Math.max(QUANTIDADE_MINIMA_PDV, Math.round((numero + Number.EPSILON) * 1000) / 1000);
}

export function calcularQuantidadePorSubtotal(subtotal, precoUnitario) {
  const valor = Number(subtotal);
  const preco = Number(precoUnitario);
  if (!Number.isFinite(valor) || !Number.isFinite(preco) || valor <= 0 || preco <= 0) return null;
  return normalizarQuantidadePDV(valor / preco);
}

export function obterPrecoVendaPDV(produto) {
  const preco = produto?.preco_venda_pdv ?? produto?.preco_venda_efetivo ?? produto?.preco_venda;
  const numero = Number.parseFloat(preco);
  return Number.isFinite(numero) ? numero : 0;
}

export function colocarItemProdutoNoTopo(itens, itemAtualizado) {
  const outrosItens = itens.filter(
    (item) => item.produto_id !== itemAtualizado.produto_id || item.etiqueta_balanca,
  );
  return [itemAtualizado, ...outrosItens];
}

export function recalcularSubtotalItem(item, novaQuantidade) {
  const quantidade = normalizarQuantidadePDV(novaQuantidade);
  const precoUnitario = Number(item.preco_unitario ?? item.preco_venda ?? 0) || 0;
  const subtotalSemDesconto = arredondarDinheiro(precoUnitario * quantidade);
  let novoDescontoValor = Number(item.desconto_valor ?? item.desconto_item ?? 0) || 0;

  if (item.tipo_desconto_aplicado === "percentual" && Number(item.desconto_percentual) > 0) {
    novoDescontoValor = (subtotalSemDesconto * Number(item.desconto_percentual)) / 100;
  }

  novoDescontoValor = arredondarDinheiro(Math.min(novoDescontoValor, subtotalSemDesconto));

  return {
    ...item,
    quantidade,
    preco_unitario: precoUnitario,
    desconto_valor: arredondarDinheiro(novoDescontoValor),
    subtotal: arredondarDinheiro(subtotalSemDesconto - novoDescontoValor),
  };
}
