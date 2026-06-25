import assert from "node:assert/strict";
import test from "node:test";

import {
  getStatusBuscaDevolucao,
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
