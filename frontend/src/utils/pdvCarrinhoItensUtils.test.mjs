import assert from "node:assert/strict";
import { test } from "node:test";

import { recalcularSubtotalItem } from "./pdvCarrinhoItensUtils.js";

test("recalcula subtotal mantendo quantidade fracionada menor que uma unidade", () => {
  const item = {
    preco_unitario: 20,
    quantidade: 1,
    subtotal: 20,
  };

  const resultado = recalcularSubtotalItem(item, 0.8);

  assert.equal(resultado.quantidade, 0.8);
  assert.equal(resultado.subtotal, 16);
});

test("aceita virgula como separador decimal na quantidade do item", () => {
  const item = {
    preco_unitario: 20,
    quantidade: 1,
    subtotal: 20,
  };

  const resultado = recalcularSubtotalItem(item, "0,8");

  assert.equal(resultado.quantidade, 0.8);
  assert.equal(resultado.subtotal, 16);
});
