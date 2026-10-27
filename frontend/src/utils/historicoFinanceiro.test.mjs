import assert from "node:assert/strict";
import test from "node:test";
import {
  camposDetalhesHistorico,
  formatarDataHistorico,
  formatarFormaPagamentoHistorico,
  obterStatusHistorico,
  statusFinanceiroVenda,
} from "./historicoFinanceiro.js";

test("datas de negócio mantêm o dia e usam dd-mm-aaaa sem interpretar UTC", () => {
  for (const valor of ["2026-10-26", "2026-10-26T00:00:00", "2026-10-26 00:00:00", "26/10/2026"]) {
    assert.equal(formatarDataHistorico(valor), "26-10-2026");
  }
  assert.equal(formatarDataHistorico("2026-10-26T09:05:00", { comHora: true }), "26-10-2026 09:05");
  assert.equal(
    formatarDataHistorico("2026-10-27T01:30:00Z", { comHora: true }),
    "26-10-2026 22:30",
  );
  for (const valor of [null, "inválida", "2026-02-30", "31/04/2026"]) {
    assert.equal(formatarDataHistorico(valor), "—");
  }
});

test("situação financeira usa pagamento explícito e não confunde finalização com quitação", () => {
  const casos = [
    [{ status: "finalizada", status_pagamento: "pago" }, "Pago"],
    [{ status: "finalizada", status_pagamento: "em_aberto" }, "Em aberto"],
    [{ status: "aberta", detalhes: { status_pagamento: "parcial" } }, "Parcial"],
    [{ status: "cancelada", status_pagamento: "pago" }, "Cancelada"],
    [{ status: "finalizada" }, "Pagamento não informado"],
    [{ status: "aberta" }, "Em aberto"],
  ];
  for (const [venda, label] of casos) assert.equal(statusFinanceiroVenda(venda), label);
});

test("recebimento tem contexto Recebido ou Estornado, sem expor efetivado", () => {
  assert.equal(
    obterStatusHistorico({ tipo: "recebimento", status: "efetivado", valor: 40 }).label,
    "Recebido",
  );
  assert.equal(
    obterStatusHistorico({ tipo: "recebimento", status: "efetivado", valor: -40 }).label,
    "Estornado",
  );
  assert.equal(
    obterStatusHistorico({
      tipo: "recebimento",
      detalhes: { status_recebimento: "estornado" },
      valor: 40,
    }).label,
    "Estornado",
  );
  assert.equal(
    obterStatusHistorico({ tipo: "conta_receber", status: "recebido" }).label,
    "Recebido",
  );
  assert.equal(obterStatusHistorico({ tipo: "credito", status: "efetivado" }).label, "Registrado");
});

test("detalhes tipados preservam referências e observação completa sem moeda em IDs nem data técnica", () => {
  const observacoes =
    "Cliente pagou na data informada.\nConferência posterior preservada integralmente.";
  const campos = camposDetalhesHistorico({
    tipo: "recebimento",
    data: "2026-10-26T00:00:00",
    detalhes: {
      recebimento_id: 12595,
      conta_receber_id: 11119,
      venda_id: 1340080,
      numero_venda: "IMP-20260915-112020",
      data_baixa: "2026-10-26",
      registrado_em: "2026-10-27T01:30:00Z",
      forma_pagamento: "Pix",
      observacoes,
    },
  });
  assert.equal(campos.find((item) => item.chave === "recebimento_id").valor, "#12595");
  assert.equal(campos.find((item) => item.chave === "data_baixa").valor, "26-10-2026");
  assert.equal(campos.find((item) => item.chave === "observacoes").valor, observacoes);
  assert.equal(campos.find((item) => item.chave === "numero_venda").valor, "#IMP-20260915-112020");
  assert.ok(campos.every((item) => !item.valor.includes("R$")));
  assert.ok(!campos.some((item) => ["registrado_em", "venda_id"].includes(item.chave)));
});

test("só campos monetários conhecidos recebem formatação BRL, inclusive milhar", () => {
  const campos = camposDetalhesHistorico({
    tipo: "conta_receber",
    detalhes: {
      conta_receber_id: 11119,
      valor_recebido: "1234.56",
      data_vencimento: "2026-10-26",
      observacoes: "Acerto",
    },
  });
  assert.equal(campos.find((item) => item.chave === "valor_recebido").valor, "R$ 1.234,56");
  assert.equal(campos.find((item) => item.chave === "conta_receber_id").valor, "#11119");
  assert.equal(campos.find((item) => item.chave === "data_vencimento").valor, "26-10-2026");
});

test("forma de pagamento traduz apenas aliases conhecidos e preserva nomes personalizados", () => {
  for (const [valor, esperado] of [
    ["pix", "Pix"],
    ["dinheiro", "Dinheiro"],
    ["cartao_credito", "Cartão de crédito"],
    ["credito", "Cartão de crédito"],
    ["cartão de débito", "Cartão de débito"],
    ["debito", "Cartão de débito"],
    ["crediario", "Crediário"],
    ["Vale aniversário QA", "Vale aniversário QA"],
    [null, "Não informado"],
  ])
    assert.equal(formatarFormaPagamentoHistorico(valor), esperado);
  const campos = camposDetalhesHistorico({
    tipo: "recebimento",
    detalhes: { forma_pagamento: "cartao_credito" },
  });
  assert.equal(campos.find((item) => item.chave === "forma_pagamento").valor, "Cartão de crédito");
});
