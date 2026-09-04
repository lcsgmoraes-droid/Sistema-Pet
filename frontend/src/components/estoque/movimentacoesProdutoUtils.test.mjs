import assert from "node:assert/strict";
import test from "node:test";

import {
  CANAIS_DESTAQUE,
  LABELS_CANAIS,
  getMotivoLabelMovimentacao,
  getOrigemMovimentacao,
  movimentacaoEstoqueProtegida,
  resolverEstoqueAtualMovimentacoes,
  resolverSaldoDisponivelMovimentacoes,
} from "./movimentacoesProdutoUtils.js";

test("movimentacoes exibe o nome correto da loja fisica", () => {
  assert.equal(LABELS_CANAIS.loja_fisica, "Loja Física");
});

test("movimentacoes destaca os seis canais da demonstracao", () => {
  assert.deepEqual(CANAIS_DESTAQUE, [
    "app",
    "ecommerce",
    "loja_fisica",
    "mercado_livre",
    "shopee",
    "amazon",
  ]);
});

test("movimentacoes usa estoque virtual calculado para kit virtual", () => {
  const produto = {
    tipo_produto: "KIT",
    tipo_kit: "VIRTUAL",
    estoque_atual: -1,
    estoque_virtual: 31,
    estoque_disponivel: 31,
    estoque_reservado: 0,
  };

  assert.equal(resolverEstoqueAtualMovimentacoes(produto), 31);
  assert.equal(resolverSaldoDisponivelMovimentacoes(produto), 31);
});

test("movimentacoes mantem estoque fisico para produto simples", () => {
  const produto = {
    tipo_produto: "SIMPLES",
    tipo_kit: null,
    estoque_atual: 12,
    estoque_virtual: 31,
    estoque_disponivel: 31,
    estoque_reservado: 2,
  };

  assert.equal(resolverEstoqueAtualMovimentacoes(produto), 12);
  assert.equal(resolverSaldoDisponivelMovimentacoes(produto), 10);
});

test("movimentacao clinica aponta para a consulta que consumiu o insumo", () => {
  const origem = getOrigemMovimentacao({
    referencia_tipo: "procedimento_veterinario",
    referencia_id: 91,
    documento: "42",
    tipo: "saida",
  });

  assert.equal(origem.texto, "Consulta #42");
  assert.equal(origem.link, "/veterinario/consultas/42");
  assert.equal(getMotivoLabelMovimentacao("fracionamento_clinico"), "Fracionamento clinico");
  assert.equal(movimentacaoEstoqueProtegida({ referencia_tipo: "procedimento_veterinario" }), true);
});
