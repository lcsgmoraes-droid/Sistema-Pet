import assert from "node:assert/strict";
import test from "node:test";
import {
  formatarQuantidade,
  montarPlanilhaLimites,
  parametrosLimites,
} from "./estoqueLimitesUtils.js";

test("quantidades brasileiras preservam frações e limites ausentes", () => {
  assert.equal(formatarQuantidade(17555.25), "17.555,25");
  assert.equal(formatarQuantidade(-2.125), "-2,125");
  assert.equal(formatarQuantidade(0), "0");
  assert.equal(formatarQuantidade(null), "—");
});

test("exportação mantém números para somar no Excel e códigos como texto", () => {
  const dados = montarPlanilhaLimites([
    {
      nome: "=Produto",
      codigo: "00123",
      estoque_atual: 2.75,
      estoque_minimo: 10,
      estoque_maximo: null,
      situacao: "abaixo_minimo",
      falta_minimo: 7.25,
      excesso_maximo: null,
    },
  ]);
  assert.equal(dados[0].length, 12);
  assert.deepEqual(dados[1][0], { value: "=Produto", type: String });
  assert.deepEqual(dados[1][1], { value: "00123", type: String });
  assert.equal(dados[1][6].value, 2.75);
  assert.equal(dados[1][6].type, Number);
  assert.equal(dados[1][8].value, "");
  assert.equal(dados[1][9].value, "Abaixo do mínimo");
  assert.equal(dados[1][10].value, 7.25);
});

test("filtros vazios não são enviados como IDs inválidos", () => {
  assert.deepEqual(parametrosLimites({ busca: "ração", marca_id: "", page: 1, export_all: true }), {
    busca: "ração",
    page: 1,
    export_all: true,
  });
});
