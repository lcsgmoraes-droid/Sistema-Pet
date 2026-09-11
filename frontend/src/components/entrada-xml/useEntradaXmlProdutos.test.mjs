import assert from "node:assert/strict";
import test from "node:test";

import {
  calcularMargemLucroProduto,
  calcularPrecoVendaInicialProduto,
} from "./entradaXmlProdutosPricing.js";

test("calcula margem de produto criado pela NF sobre o preco de venda", () => {
  assert.equal(calcularPrecoVendaInicialProduto(24.99, 50), "49.98");
  assert.equal(calcularMargemLucroProduto(24.99, 45), "44.47");
  assert.equal(calcularMargemLucroProduto(10, 14.2857142857), "30.00");
});
