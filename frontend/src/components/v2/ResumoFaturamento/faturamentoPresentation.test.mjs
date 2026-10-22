import assert from "node:assert/strict";
import { test } from "node:test";
import {
  formatarDataFaturamento,
  formulaFaturamento,
  linhasFaturamento,
  linhasQuitacao,
  periodoFaturamento,
} from "./faturamentoPresentation.js";

test("apresentação distingue líquido comercial, entrega e quitação", () => {
  const composicao = {
    faturamento_bruto: 100,
    descontos: 10,
    devolucoes: 0,
    faturamento_liquido: 90,
    taxa_entrega: 15,
    total_vendas: 105,
    valor_pago: 40,
    creditos_utilizados: 10,
    crediario_receber: 30,
    em_aberto: 25,
  };
  assert.equal(formulaFaturamento(composicao), "Vendas − descontos");
  assert.deepEqual(linhasFaturamento(composicao), [
    ["Faturamento bruto", 100],
    ["Descontos", 10],
    ["Faturamento líquido", 90],
    ["Entrega cobrada à parte", 15],
    ["Total das vendas com entrega", 105],
  ]);
  assert.deepEqual(linhasQuitacao(composicao), [
    ["Pago", 40],
    ["Créditos e cashback utilizados", 10],
    ["Crediário a receber", 30],
    ["Aguardando pagamento, sem crediário", 25],
  ]);
  assert.equal(
    formulaFaturamento({ ...composicao, devolucoes: 20 }),
    "Vendas − descontos − devoluções",
  );
  assert.deepEqual(linhasFaturamento(null), []);
});

test("datas do faturamento preservam o dia civil do servidor em qualquer fuso", () => {
  assert.equal(formatarDataFaturamento("2026-10-20T00:01:00-03:00"), "20/10/2026");
  assert.equal(
    periodoFaturamento({ data_inicio: "2026-10-20", data_fim: "2026-10-20" }),
    "20/10/2026",
  );
  assert.equal(
    periodoFaturamento({ data_inicio: "2026-10-19", data_fim: "2026-10-20" }),
    "19/10/2026 a 20/10/2026",
  );
  assert.equal(periodoFaturamento(null, "Hoje"), "Hoje");
  assert.equal(formatarDataFaturamento(null), "—");
});
