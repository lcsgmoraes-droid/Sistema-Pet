import assert from "node:assert/strict";
import test from "node:test";

import {
  getStatusBuscaDevolucao,
  getTextoDevolucaoVendaPDV,
  podeAbrirDevolucaoVenda,
  STATUS_DEVOLUCAO_DIRETA,
} from "./pdvReturnEligibility.js";

test("permite reabrir venda ja devolvida parcialmente", () => {
  assert.equal(podeAbrirDevolucaoVenda({ id: 123, status: "finalizada_devolucao" }), true);
});

test("inclui devolucao parcial na busca do modal de devolucao", () => {
  assert.deepEqual(getStatusBuscaDevolucao(), [
    "finalizada",
    "baixa_parcial",
    "pago_nf",
    "finalizada_devolucao",
  ]);
  assert.equal(STATUS_DEVOLUCAO_DIRETA.has("finalizada_devolucao"), true);
});

test("PDV informa o estado da devolução sem chamar a venda de aberta", () => {
  assert.deepEqual(getTextoDevolucaoVendaPDV({ status: "finalizada_devolucao" }), {
    situacao: "com Devolução",
    orientacao: "Consulte o saldo disponível em Devolução.",
  });
  assert.deepEqual(getTextoDevolucaoVendaPDV({ status: "devolvida_total" }), {
    situacao: "com Todos os Itens Devolvidos",
    orientacao: "O reembolso dos itens não inclui o frete.",
  });
  assert.equal(getTextoDevolucaoVendaPDV({ status: "finalizada" }), null);
});
