import assert from "node:assert/strict";
import { test } from "node:test";

import {
  colocarItemProdutoNoTopo,
  prepararItensAposMudancaCarrinho,
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

test("invalida o cupom e restaura os valores brutos quando o carrinho muda", () => {
  const resultado = prepararItensAposMudancaCarrinho(
    [
      {
        produto_id: 1,
        quantidade: 2,
        preco_unitario: 5.5,
        desconto_valor: 1.99,
        desconto_item: 1.99,
        desconto_percentual: 18.09,
        tipo_desconto_aplicado: "valor",
        preco_com_desconto: 4.505,
        subtotal: 9.01,
      },
      {
        produto_id: 2,
        quantidade: 3,
        preco_unitario: 19.9,
        desconto_valor: 0,
        subtotal: 59.7,
      },
    ],
    true,
  );

  assert.equal(resultado.cupomInvalidado, true);
  assert.deepEqual(resultado.extras, {
    cupom_code: null,
    cupom_discount_applied: null,
  });
  assert.deepEqual(
    resultado.itens.map((item) => ({
      subtotal: item.subtotal,
      desconto_valor: item.desconto_valor,
      desconto_item: item.desconto_item,
    })),
    [
      { subtotal: 11, desconto_valor: 0, desconto_item: 0 },
      { subtotal: 59.7, desconto_valor: 0, desconto_item: 0 },
    ],
  );
});

test("preserva os descontos quando nao existe cupom ativo", () => {
  const itens = [{ produto_id: 1, quantidade: 1, subtotal: 9, desconto_valor: 1 }];
  const resultado = prepararItensAposMudancaCarrinho(itens, false);

  assert.equal(resultado.cupomInvalidado, false);
  assert.equal(resultado.itens, itens);
  assert.deepEqual(resultado.extras, {});
});
