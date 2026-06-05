import { arredondarDinheiro } from "./pdvCarrinhoItensUtils.js";

export function recalcularItemComPrecoEDesconto(item, itemEditando) {
  const precoUnitario =
    Number(itemEditando?.preco ?? item.preco_unitario ?? 0) || 0;
  const quantidade = Math.max(
    1,
    Number(item.quantidade || itemEditando?.quantidade) || 1,
  );
  const subtotalSemDesconto = precoUnitario * quantidade;
  let descontoValor = 0;
  let descontoPercentual = 0;

  if (itemEditando?.tipoDesconto === "valor") {
    descontoValor = Number.parseFloat(itemEditando.descontoValor) || 0;
    descontoValor = Math.min(Math.max(descontoValor, 0), subtotalSemDesconto);
    descontoPercentual =
      subtotalSemDesconto > 0 ? (descontoValor / subtotalSemDesconto) * 100 : 0;
  } else {
    descontoPercentual = Number.parseFloat(itemEditando?.descontoPercentual) || 0;
    descontoPercentual = Math.min(Math.max(descontoPercentual, 0), 100);
    descontoValor = (subtotalSemDesconto * descontoPercentual) / 100;
  }

  const precoComDesconto =
    quantidade > 0 ? precoUnitario - descontoValor / quantidade : precoUnitario;

  return {
    ...item,
    preco_unitario: arredondarDinheiro(precoUnitario),
    desconto_valor: arredondarDinheiro(descontoValor),
    desconto_percentual: descontoPercentual,
    tipo_desconto_aplicado: itemEditando?.tipoDesconto || "valor",
    preco_com_desconto: arredondarDinheiro(precoComDesconto),
    subtotal: arredondarDinheiro(subtotalSemDesconto - descontoValor),
  };
}
