import assert from "node:assert/strict";
import { test } from "node:test";

import {
  calcularQuantidadePorSubtotal,
  colocarItemProdutoNoTopo,
  normalizarQuantidadePDV,
  obterSubtotalBrutoItem,
  recalcularItemPorSubtotal,
  recalcularSubtotalItem,
} from "./pdvCarrinhoItensUtils.js";
import { recalcularItemComPrecoEDesconto } from "./pdvDescontoItensUtils.js";
import { recalcularVendaComDescontos } from "./pdvDescontosUtils.js";
import { montarPayloadVenda } from "./pdvVendaPayload.js";

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

test("valor digitado do granel permanece exato com peso salvo em tres casas", () => {
  for (const caso of [
    { digitado: 20, preco: 13, quantidade: 1.538 },
    { digitado: 29, preco: 19.9, quantidade: 1.457 },
    { digitado: 34.9, preco: 29.9, quantidade: 1.167 },
    { digitado: 29.93, preco: 19.9, quantidade: 1.504 },
    { digitado: 99.99, preco: 100, quantidade: 1 },
    { digitado: 189.9, preco: 178.9, quantidade: 1.061 },
    { digitado: 2.05, preco: 0.16, quantidade: 12.813 },
  ]) {
    const item = recalcularItemPorSubtotal({ preco_unitario: caso.preco }, caso.digitado);
    assert.equal(item.quantidade, caso.quantidade);
    assert.equal(item.preco_unitario, caso.preco);
    assert.equal(item.subtotal, caso.digitado);
    assert.equal(obterSubtotalBrutoItem(item), caso.digitado);
  }
});

test("valor informado inclui o desconto fixo ao calcular o peso e conserva o payload", () => {
  const item = recalcularItemPorSubtotal({ preco_unitario: 13, desconto_item: 2 }, 20);
  assert.equal(item.quantidade, 1.692);
  assert.equal(item.desconto_valor, 2);
  const venda = recalcularVendaComDescontos({ desconto_venda_valor: 1 }, [item]);
  assert.equal(venda.subtotal, 20);
  assert.equal(venda.total, 19);
  assert.equal(venda.desconto_valor, 3);
  const payload = montarPayloadVenda(venda);
  assert.equal(payload.itens[0].quantidade, 1.692);
  assert.equal(payload.itens[0].subtotal, 20);
  assert.equal(payload.itens[0].desconto_item, 2);
});

test("valor informado mantem desconto percentual sem descontar duas vezes", () => {
  const item = recalcularItemPorSubtotal(
    {
      preco_unitario: 13,
      tipo_desconto_aplicado: "percentual",
      desconto_percentual: 10,
    },
    20,
  );
  assert.equal(item.quantidade, 1.709);
  assert.equal(item.desconto_valor, 2.22);
  assert.equal(item.subtotal, 20);
  assert.equal(obterSubtotalBrutoItem(item), 22.22);
});

test("editar desconto preserva o bruto informado e editar preco volta a calcular pelo peso", () => {
  const item = recalcularItemPorSubtotal({ preco_unitario: 13 }, 20);
  const comDesconto = recalcularItemComPrecoEDesconto(item, {
    preco: 13,
    tipoDesconto: "valor",
    descontoValor: 2,
  });
  assert.equal(comDesconto.subtotal, 18);
  assert.equal(comDesconto.desconto_valor, 2);
  const novoPreco = recalcularItemComPrecoEDesconto(item, {
    preco: 14,
    tipoDesconto: "valor",
    descontoValor: 0,
  });
  assert.equal(novoPreco.subtotal, 21.53);
  assert.equal(recalcularSubtotalItem(item, 2).subtotal, 26);
});

test("subtotal invalido ou sem peso representavel nao altera o item", () => {
  const item = { preco_unitario: 100, quantidade: 1, subtotal: 100 };
  for (const valor of [0, -1, NaN, Infinity, "invalido", 0.01]) {
    assert.equal(recalcularItemPorSubtotal(item, valor), item);
  }
  assert.equal(recalcularItemPorSubtotal({ ...item, preco_unitario: 0 }, 20).subtotal, 100);
  const gratuito = { ...item, tipo_desconto_aplicado: "percentual", desconto_percentual: 100 };
  assert.equal(recalcularItemPorSubtotal(gratuito, 20), gratuito);
  assert.equal(obterSubtotalBrutoItem({ ...item, subtotal: 10 }), 100);
});

test("quantidade digitada diretamente respeita gramas antes de calcular subtotal", () => {
  const item = recalcularSubtotalItem({ preco_unitario: 29.9 }, "1,1672");
  assert.equal(item.quantidade, 1.167);
  assert.equal(item.subtotal, 34.89);
  assert.equal(normalizarQuantidadePDV(0.0004), 0.001);
  assert.equal(calcularQuantidadePorSubtotal(0, 29.9), null);
  assert.equal(calcularQuantidadePorSubtotal(29, 0), null);
});
