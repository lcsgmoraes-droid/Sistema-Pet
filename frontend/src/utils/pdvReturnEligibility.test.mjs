import assert from "node:assert/strict";
import test from "node:test";

import {
  getStatusBuscaDevolucao,
  getTextoDevolucaoVendaPDV,
  podeAbrirDevolucaoVenda,
  podeRegistrarRecebimentoVenda,
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

test("recebimento fica bloqueado em devoluções totais, cancelamentos e trocas", () => {
  for (const status of [
    "devolvida_total",
    "finalizada_devolucao_total",
    "cancelada",
    "cancelado",
    "trocada",
    "finalizada",
    "pago_nf",
  ]) {
    assert.equal(podeRegistrarRecebimentoVenda({ id: 14, status }), false, status);
  }
});

test("devolução parcial e venda reaberta continuam permitindo saldo ou ajuste legítimo", () => {
  for (const status of [
    "aberta",
    "baixa_parcial",
    "finalizada_devolucao",
    "finalizada_devolucao_parcial",
  ]) {
    assert.equal(podeRegistrarRecebimentoVenda({ id: 14, status }), true, status);
  }
  assert.equal(
    podeRegistrarRecebimentoVenda({ id: 14, status: "aberta", total: 100, total_pago: 100 }),
    true,
  );
  assert.equal(podeRegistrarRecebimentoVenda({ itens: [{ produto_id: 5 }], total: 10 }), true);
});
