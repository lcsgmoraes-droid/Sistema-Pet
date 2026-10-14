import assert from "node:assert/strict";
import { test } from "node:test";

import {
  calcularQuantidadePorSubtotal,
  colocarItemProdutoNoTopo,
  normalizarQuantidadePDV,
  recalcularSubtotalItem,
} from "./pdvCarrinhoItensUtils.js";

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

test("mantem etiquetas de pesos distintos quando o mesmo produto e adicionado manualmente", () => {
  const itens = [
    { produto_id: 2024, quantidade: 0.538, etiqueta_balanca: "2002024015556" },
    { produto_id: 2024, quantidade: 0.228, etiqueta_balanca: "2002024006592" },
    { produto_id: 2024, quantidade: 1, etiqueta_balanca: null },
  ];
  const resultado = colocarItemProdutoNoTopo(itens, {
    produto_id: 2024,
    quantidade: 2,
  });
  assert.equal(resultado.length, 3);
  assert.deepEqual(
    resultado.map((item) => item.quantidade),
    [2, 0.538, 0.228],
  );
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

test("valor digitado do granel usa o mesmo peso de tres casas que sera salvo", () => {
  for (const caso of [
    { digitado: 29, preco: 19.9, quantidade: 1.457, subtotal: 28.99 },
    { digitado: 34.9, preco: 29.9, quantidade: 1.167, subtotal: 34.89 },
  ]) {
    const quantidade = calcularQuantidadePorSubtotal(caso.digitado, caso.preco);
    const item = recalcularSubtotalItem({ preco_unitario: caso.preco }, quantidade);
    assert.equal(quantidade, caso.quantidade);
    assert.equal(item.quantidade, caso.quantidade);
    assert.equal(item.subtotal, caso.subtotal);
  }
});

test("quantidade digitada diretamente respeita gramas antes de calcular subtotal", () => {
  const item = recalcularSubtotalItem({ preco_unitario: 29.9 }, "1,1672");
  assert.equal(item.quantidade, 1.167);
  assert.equal(item.subtotal, 34.89);
  assert.equal(normalizarQuantidadePDV(0.0004), 0.001);
  assert.equal(calcularQuantidadePorSubtotal(0, 29.9), null);
  assert.equal(calcularQuantidadePorSubtotal(29, 0), null);
});
