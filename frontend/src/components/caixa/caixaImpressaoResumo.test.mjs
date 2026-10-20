import assert from "node:assert/strict";
import test from "node:test";
import { criarResumoImpressaoCaixa } from "./caixaImpressaoResumo.js";

test("impressões usam a composição nova e formas que correspondem ao recebido", () => {
  const resumo = criarResumoImpressaoCaixa({
    total_vendido: 500,
    total_recebido: 500,
    vendas_por_forma_pagamento: { Cashback: { total: 5 } },
    vendas_periodo: {
      data_inicio: "2026-10-09",
      data_fim: "2026-10-09",
      faturamento_liquido: 185,
      total_vendas: 185,
    },
    composicao_recebimentos: {
      data_inicio: "2026-10-09",
      data_fim: "2026-10-09",
      vendas_periodo: 150,
      vendas_anteriores: 60,
      devolucoes: 25,
      total_recebido: 185,
      creditos_utilizados: 5,
      por_forma_pagamento: {
        Dinheiro: { total: 35 },
        Cartao: { total: 100 },
        PIX: { total: 50 },
      },
    },
  });

  assert.equal(resumo.tituloVendas, "Vendas de 09/10/2026");
  assert.equal(resumo.periodoRecebimentos, "09/10/2026");
  assert.equal(new Map(resumo.linhasVendas).get("Faturamento líquido"), 185);
  assert.equal(new Map(resumo.linhasRecebimentos).get("Recebimentos neste caixa"), 185);
  assert.equal(
    Math.round(resumo.formas.reduce((total, [, forma]) => total + forma.total, 0) * 100),
    18500,
  );
  assert.equal(
    resumo.formas.some(([nome]) => nome === "Cashback"),
    false,
  );
});

test("fallback legado deixa explícito o vínculo ao caixa, sem afirmar venda do dia", () => {
  const resumo = criarResumoImpressaoCaixa({
    total_vendido: 230,
    total_recebido: 180,
    total_vendas_crediario: 35,
    recebimentos_por_forma_pagamento: { PIX: { total: 180 } },
  });

  assert.equal(resumo.tituloVendas, "Vendas vinculadas ao caixa");
  assert.equal(resumo.novoContrato, false);
  assert.deepEqual(resumo.linhasRecebimentos, [["Quitações registradas no caixa (legado)", 180]]);
  assert.deepEqual(resumo.formas, [["PIX", { total: 180 }]]);
});
