import assert from "node:assert/strict";
import { test } from "node:test";
import { dataRecebimentoBR, planilhasRecebimentos } from "./recebimentosVendasUtils.js";

test("Excel mantém datas distintas, parcelas, devoluções e total da tela", () => {
  const relatorio = {
    data_inicio: "2026-08-01",
    data_fim: "2026-08-31",
    resumo: { recebimentos: 1000, devolucoes: 100, total: 900 },
    movimentos: [
      {
        numero_venda: "TEST-1",
        data_venda: "2026-07-01",
        data_recebimento: "2026-08-15",
        cliente_nome: "Teste",
        forma_pagamento: "Pix",
        tipo: "recebimento",
        valor: 1000,
      },
      {
        numero_venda: "TEST-1",
        data_venda: "2026-07-01",
        data_recebimento: "2026-08-20",
        cliente_nome: "Teste",
        forma_pagamento: "Dinheiro",
        tipo: "devolucao",
        valor: -100,
      },
    ],
  };
  const planilhas = planilhasRecebimentos(relatorio, "Todos os canais");
  assert.deepEqual(planilhas[0].linhas.at(-1), ["Total no período", 900]);
  assert.equal(planilhas[1].linhas[1][0], "15/08/2026");
  assert.equal(planilhas[1].linhas[1][2], "01/07/2026");
  assert.equal(planilhas[1].linhas[2].at(-1), -100);
  assert.equal(dataRecebimentoBR("2026-08-01"), "01/08/2026");
});
