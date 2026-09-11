import {
  calcularMargemSobreVenda,
  calcularPrecoVendaPorMargem,
} from "../../utils/produtoMargem.js";

export const MARGEM_PADRAO_CRIACAO_PRODUTO = 50;

export function calcularPrecoVendaInicialProduto(
  custoBase,
  margem = MARGEM_PADRAO_CRIACAO_PRODUTO,
) {
  const precoVenda = calcularPrecoVendaPorMargem(custoBase, margem);
  return precoVenda === null ? "" : precoVenda.toFixed(2);
}

export function calcularMargemLucroProduto(custo, venda) {
  const margem = calcularMargemSobreVenda(custo, venda);
  return margem === null ? "" : margem.toFixed(2);
}
