import assert from "node:assert/strict";
import test from "node:test";

import { getDreAlertDetail, getDreAlertMetrics } from "./dreAlertMetrics.js";

test("alerta de custo da devolução não exibe métricas de CMV provisório", () => {
  assert.deepEqual(
    getDreAlertMetrics({
      codigo: "devolucao_custo_original_pendente",
      quantidade_itens: 1,
      valor_vendas: 100,
      quantidade_produtos: 0,
      valor_estimado: 0,
    }),
    [
      { tipo: "quantidade", rotulo: "itens devolvidos com custo a conferir", valor: 1 },
      { tipo: "moeda", rotulo: "Devoluções afetadas", valor: 100 },
    ],
  );
});

test("alertas de imposto e CMV usam somente os valores próprios", () => {
  assert.deepEqual(
    getDreAlertMetrics({ codigo: "devolucao_imposto_a_conciliar", valor_vendas: 100 }),
    [{ tipo: "moeda", rotulo: "Devoluções a conciliar", valor: 100 }],
  );
  assert.deepEqual(
    getDreAlertMetrics({
      codigo: "cmv_produtos_sem_custo",
      quantidade_produtos: 2,
      valor_vendas: 200,
      valor_estimado: 60,
    }).map((metrica) => metrica.rotulo),
    ["produto(s) sem custo", "Vendas afetadas", "CMV provisório"],
  );
});

test("alerta da devolução aponta para o detalhe das devoluções", () => {
  assert.deepEqual(getDreAlertDetail({ codigo: "devolucao_custo_original_pendente" }), {
    campo: "devolucoes",
    rotulo: "Ver devoluções",
  });
  assert.equal(getDreAlertDetail({ codigo: "cmv_rateio_ambiguo" }), null);
});
