import {
  calcularQuantidadeTotalUnidadesPedido,
  normalizarQuantidadePorEmbalagemPedido,
  normalizarUnidadeCompraPedido,
  numeroSeguro,
} from "./pedidoCompraUtils.js";

export function calcularQuantidadeReposicaoProduto(produto) {
  const quantidadeSugerida = numeroSeguro(produto?.quantidade_sugerida);
  if (quantidadeSugerida > 0) return Math.max(1, Math.ceil(quantidadeSugerida));

  const estoqueAtual = numeroSeguro(produto?.estoque_atual);
  const estoqueMinimo = numeroSeguro(produto?.estoque_minimo);
  return Math.max(1, Math.ceil(estoqueMinimo - estoqueAtual));
}

function formatarQuantidadeGiro(valor) {
  return numeroSeguro(valor).toLocaleString("pt-BR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 3,
  });
}

export function montarTooltipGiroCatalogo(produto) {
  const janelas = produto?.vendas_janelas || {};
  const vendas = [7, 15, 30, 60, 90]
    .map((dias) => {
      const valor = janelas[String(dias)] ?? produto?.[`vendas_${dias}d`] ?? 0;
      return `${dias} dias: ${formatarQuantidadeGiro(valor)}`;
    })
    .join("\n");
  const media = formatarQuantidadeGiro(produto?.media_diaria_30);
  const diasAteMinimo = Number(produto?.dias_ate_minimo);
  const previsao = Number.isFinite(diasAteMinimo)
    ? `\nPrevisão até o mínimo: ${formatarQuantidadeGiro(diasAteMinimo)} dia(s)`
    : "";

  return `Vendas por período\n${vendas}\nMédia diária (30 dias): ${media}${previsao}`;
}

export function criarItemCatalogoPedido({ custoUnitario, itemAtual, produto, quantidade }) {
  const quantidadePedida = numeroSeguro(quantidade);
  if (!produto?.id || quantidadePedida <= 0) {
    return null;
  }

  const unidadeCompra = normalizarUnidadeCompraPedido(itemAtual?.unidade_compra || "UN");
  const quantidadePorEmbalagem = normalizarQuantidadePorEmbalagemPedido(
    unidadeCompra,
    itemAtual?.quantidade_por_embalagem || "1",
  );
  const quantidadeTotalUnidades = calcularQuantidadeTotalUnidadesPedido({
    quantidade_pedida: quantidadePedida,
    unidade_compra: unidadeCompra,
    quantidade_por_embalagem: quantidadePorEmbalagem,
  });
  const precoUnitario = Math.max(0, numeroSeguro(custoUnitario));
  const descontoItem = Math.max(0, numeroSeguro(itemAtual?.desconto_item));

  return {
    ...itemAtual,
    produto_id: Number(produto.id),
    produto_nome: produto.nome,
    produto_codigo: produto.codigo || produto.sku || itemAtual?.produto_codigo || "",
    quantidade_pedida: quantidadePedida,
    unidade_compra: unidadeCompra,
    quantidade_por_embalagem: quantidadePorEmbalagem,
    quantidade_total_unidades: quantidadeTotalUnidades,
    preco_unitario: precoUnitario,
    desconto_item: descontoItem,
    total: Math.max(0, precoUnitario - descontoItem) * quantidadeTotalUnidades,
  };
}
