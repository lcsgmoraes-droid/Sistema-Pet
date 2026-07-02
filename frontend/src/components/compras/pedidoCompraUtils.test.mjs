import assert from "node:assert/strict";
import { test } from "node:test";

import {
  calcularQuantidadeTotalUnidadesPedido,
  formatarQuantidadeCompraPedido,
  montarTooltipQuantidadeCompraPedido,
  normalizarItemPedido,
} from "./pedidoCompraUtils.js";

test("formatarQuantidadeCompraPedido mostra embalagem com total em unidades", () => {
  const item = {
    quantidade_pedida: 2,
    unidade_compra: "CX",
    quantidade_por_embalagem: 12,
  };

  assert.equal(calcularQuantidadeTotalUnidadesPedido(item), 24);
  assert.equal(formatarQuantidadeCompraPedido(item), "2 CX (24 unid)");
  assert.equal(
    montarTooltipQuantidadeCompraPedido(item),
    "Cada CX contem 12 unidades vendaveis. Este item representa 24 unidades no total.",
  );
});

test("formatarQuantidadeCompraPedido preserva unitario simples", () => {
  const item = normalizarItemPedido({
    produto_id: 15,
    produto_nome: "Sache Frango",
    quantidade_pedida: 12,
    unidade_compra: "UN",
    quantidade_por_embalagem: 12,
    preco_unitario: 3.5,
  });

  assert.equal(item.unidade_compra, "UN");
  assert.equal(item.quantidade_por_embalagem, 1);
  assert.equal(item.quantidade_total_unidades, 12);
  assert.equal(formatarQuantidadeCompraPedido(item), "12 UN");
  assert.equal(montarTooltipQuantidadeCompraPedido(item), "");
});
