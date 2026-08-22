import assert from "node:assert/strict";
import { test } from "node:test";

import { colocarItemProdutoNoTopo, recalcularSubtotalItem } from "./pdvCarrinhoItensUtils.js";

test("coloca um novo produto no topo do carrinho", () => {
  const itens = [
    { produto_id: 1, produto_nome: "Primeiro" },
    { produto_id: 2, produto_nome: "Segundo" },
  ];

  const resultado = colocarItemProdutoNoTopo(itens, {
    produto_id: 3,
    produto_nome: "Recem bipado",
  });

  assert.deepEqual(
    resultado.map((item) => item.produto_id),
    [3, 1, 2],
  );
});

test("traz para o topo um produto bipado novamente sem duplica-lo", () => {
  const itens = [
    { produto_id: 1, quantidade: 1 },
    { produto_id: 2, quantidade: 1 },
  ];

  const resultado = colocarItemProdutoNoTopo(itens, {
    produto_id: 2,
    quantidade: 2,
  });

  assert.deepEqual(resultado, [
    { produto_id: 2, quantidade: 2 },
    { produto_id: 1, quantidade: 1 },
  ]);
});

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
