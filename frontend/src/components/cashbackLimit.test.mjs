import assert from "node:assert/strict";
import { test } from "node:test";

import { calcularCashbackDisponivelNaVenda } from "./modalPagamentoUtils.js";

test("compra de R$ 100 limita cashback a R$ 20 quando configurado 20%", () => {
  assert.equal(
    calcularCashbackDisponivelNaVenda({ saldo: 100, valorTotal: 100, limitePercentual: 20 }),
    20,
  );
  assert.equal(
    calcularCashbackDisponivelNaVenda({ saldo: 100, valorTotal: 100, limitePercentual: null }),
    100,
  );
});

test("resgates anteriores e pendentes consomem o mesmo limite da venda", () => {
  assert.equal(
    calcularCashbackDisponivelNaVenda({
      saldo: 100,
      valorTotal: 100,
      limitePercentual: 20,
      pagamentosExistentes: [{ forma_pagamento: "Cashback", valor: 7 }],
      pagamentos: [{ is_cashback: true, valor: 5 }],
    }),
    8,
  );
});

test("saldo menor que o teto e centavos pequenos não ultrapassam o limite", () => {
  assert.equal(
    calcularCashbackDisponivelNaVenda({ saldo: 8, valorTotal: 100, limitePercentual: 20 }),
    8,
  );
  assert.equal(
    calcularCashbackDisponivelNaVenda({ saldo: 1, valorTotal: 0.03, limitePercentual: 20 }),
    0,
  );
});
