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
      escopo: "caixa",
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

  assert.equal(resumo.tituloVendas, "Vendas deste caixa de 09/10/2026");
  assert.match(resumo.descricaoVendas, /^Origem neste caixa\./);
  assert.equal(resumo.tituloRecebimentos, "Recebimentos neste caixa");
  assert.equal(resumo.tituloFormas, "Formas de recebimento");
  assert.equal(resumo.periodoRecebimentos, "09/10/2026");
  assert.equal(new Map(resumo.linhasVendas).get("Faturamento líquido"), 185);
  assert.equal(new Map(resumo.linhasRecebimentos).get("Recebimentos neste caixa"), 185);
  assert.equal(new Map(resumo.linhasRecebimentos).get("De outras datas ou sem data"), 60);
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
    recebimentos_por_forma_pagamento: { PIX: { total: 175 }, Cashback: { total: 5 } },
  });

  assert.equal(resumo.tituloVendas, "Vendas vinculadas ao caixa");
  assert.equal(resumo.novoContrato, false);
  assert.equal(resumo.tituloRecebimentos, "Quitações registradas no caixa (legado)");
  assert.equal(resumo.tituloFormas, "Formas de quitação (legado)");
  assert.match(resumo.notaRecebimentos, /podem incluir créditos e cashback/);
  assert.doesNotMatch(resumo.notaRecebimentos, /ficam separados/);
  assert.deepEqual(resumo.linhasRecebimentos, [["Quitações registradas no caixa (legado)", 180]]);
  assert.deepEqual(resumo.formas, [
    ["PIX", { total: 175 }],
    ["Cashback", { total: 5 }],
  ]);
});
