import assert from "node:assert/strict";
import test from "node:test";

import {
  calcularMargemSobreVenda,
  calcularPrecoVendaPorMargem,
  formatarDivisorMargem,
  normalizarMargensPreco,
} from "./produtoMargem.js";

test("calcula o preco de venda pela margem sobre a venda", () => {
  assert.equal(calcularPrecoVendaPorMargem(10, 30).toFixed(2), "14.29");
  assert.equal(calcularPrecoVendaPorMargem(10, 34).toFixed(2), "15.15");
});

test("deriva a margem do custo e do preco sem alterar o preco existente", () => {
  assert.equal(calcularMargemSobreVenda(10, 20), 50);
  assert.equal(calcularMargemSobreVenda(10, 14.2857142857).toFixed(2), "30.00");
});

test("recusa valores que nao permitem calcular um preco valido", () => {
  assert.equal(calcularPrecoVendaPorMargem(10, 100), null);
  assert.equal(calcularPrecoVendaPorMargem(0, 30), null);
  assert.equal(calcularMargemSobreVenda(10, 0), null);
});

test("aceita margem negativa para representar venda abaixo do custo", () => {
  assert.equal(calcularPrecoVendaPorMargem(10, -25), 8);
  assert.equal(calcularMargemSobreVenda(10, 8), -25);
});

test("normaliza as duas sugestoes e mostra o divisor correspondente", () => {
  assert.deepEqual(normalizarMargensPreco({}), [30, 34]);
  assert.deepEqual(
    normalizarMargensPreco({ margem_preco_sugestao_1: 25, margem_preco_sugestao_2: 40 }),
    [25, 40],
  );
  assert.equal(formatarDivisorMargem(30), "0,70");
  assert.equal(formatarDivisorMargem(34), "0,66");
});
