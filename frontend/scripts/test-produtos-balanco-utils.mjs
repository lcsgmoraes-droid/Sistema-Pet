import assert from "node:assert/strict";

import {
  formatQtd,
  montarMovimentoBalanco,
  parseNumeroBR,
} from "../src/components/produtoBalanco/produtosBalancoUtils.js";

assert.equal(parseNumeroBR("31,50"), 31.5);
assert.equal(parseNumeroBR("31.5"), 31.5);
assert.equal(parseNumeroBR("1.234,5"), 1234.5);
assert.equal(formatQtd("31,00"), "31");

const saida = montarMovimentoBalanco({ id: 10, estoque_atual: "31,00" }, 28, {});

assert.deepEqual(saida, {
  endpoint: "/estoque/saida",
  payload: {
    produto_id: 10,
    quantidade: 3,
    motivo: "balanco",
    observacao: "Balanco rapido: estoque ajustado para 28",
  },
  diferenca: -3,
  estoqueAtual: 31,
});

const entrada = montarMovimentoBalanco({ id: 11, estoque_atual: "2.5" }, 4, {
  numeroLote: "L-1",
  dataValidade: "2026-12-31",
});

assert.deepEqual(entrada, {
  endpoint: "/estoque/entrada",
  payload: {
    produto_id: 11,
    quantidade: 1.5,
    motivo: "balanco",
    observacao: "Balanco rapido: estoque ajustado para 4",
    numero_lote: "L-1",
    data_validade: "2026-12-31",
  },
  diferenca: 1.5,
  estoqueAtual: 2.5,
});

assert.deepEqual(montarMovimentoBalanco({ id: 12, estoque_atual: "7" }, 7, {}), {
  semAlteracao: true,
  diferenca: 0,
  estoqueAtual: 7,
});

assert.equal(
  montarMovimentoBalanco({ id: 13, estoque_atual: "??" }, 1, {}).erro,
  "Estoque atual invalido.",
);
