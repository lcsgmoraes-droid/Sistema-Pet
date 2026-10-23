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
  // A venda e o estoque armazenam tres casas decimais. Ao digitar o valor,
  // somente o peso e arredondado; o subtotal informado continua em centavos.
  return Math.max(QUANTIDADE_MINIMA_PDV, Math.round((numero + Number.EPSILON) * 1000) / 1000);
}

function quantidadeArredondadaPorValor(subtotal, precoUnitario) {
  const centavos = Math.round((subtotal + Number.EPSILON) * 100);
  const precoCentavos = Math.round((precoUnitario + Number.EPSILON) * 100);
  // Divide centavos inteiros para que meios gramas sigam o mesmo HALF_UP
  // usado pelo backend, sem depender da aproximacao binaria de reais.
  return precoCentavos > 0 ? Math.round((centavos * 1000) / precoCentavos) / 1000 : 0;
}

export function calcularQuantidadePorSubtotal(subtotal, precoUnitario) {
  const valor = Number(subtotal);
  const preco = Number(precoUnitario);
  if (!Number.isFinite(valor) || !Number.isFinite(preco) || valor <= 0 || preco <= 0) return null;
  return Math.max(QUANTIDADE_MINIMA_PDV, quantidadeArredondadaPorValor(valor, preco));
}

export function obterSubtotalBrutoItem(item) {
  const preco = Number(item.preco_unitario ?? item.preco_venda ?? 0) || 0;
  const quantidade = normalizarQuantidadePDV(item.quantidade);
  const calculado = arredondarDinheiro(preco * quantidade);
  const desconto = Number(item.desconto_valor ?? item.desconto_item ?? 0) || 0;
  const informado = arredondarDinheiro(Number(item.subtotal) + desconto);
  // O valor informado pode representar uma fracao de grama que o estoque
  // arredonda. Preserva-o somente quando ele corresponde ao mesmo peso.
  return item.subtotal != null &&
    informado >= 0 &&
    preco > 0 &&
    quantidadeArredondadaPorValor(informado, preco) === quantidade
    ? informado
    : calculado;
}

export function recalcularItemPorSubtotal(item, novoSubtotal) {
  const valor = Number(novoSubtotal);
  const preco = Number(item.preco_unitario ?? item.preco_venda ?? 0);
  if (!Number.isFinite(valor) || valor <= 0 || !Number.isFinite(preco) || preco <= 0) {
    return item;
  }

  const subtotal = arredondarDinheiro(valor);
  let desconto = Math.max(0, arredondarDinheiro(item.desconto_valor ?? item.desconto_item ?? 0));
  if (item.tipo_desconto_aplicado === "percentual") {
    const percentual = Math.max(0, Number(item.desconto_percentual) || 0);
    if (percentual >= 100) return item;
    desconto = arredondarDinheiro(subtotal / (1 - percentual / 100) - subtotal);
  }

  const bruto = arredondarDinheiro(subtotal + desconto);
  const quantidade = quantidadeArredondadaPorValor(bruto, preco);
  if (quantidade <= 0) return item;
  return {
    ...item,
    quantidade,
    preco_unitario: preco,
    desconto_valor: desconto,
    subtotal,
  };
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
