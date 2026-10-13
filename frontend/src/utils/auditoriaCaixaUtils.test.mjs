import assert from "node:assert/strict";
import { test } from "node:test";
import {
  FILTRO_SEM_PAGAMENTOS,
  chaveFormaAuditoria,
  filtrarLancamentosAuditoria,
  filtrarVendasAuditoria,
  formasAuditoria,
  paginarAuditoria,
  pagamentosVendaAuditoria,
} from "./auditoriaCaixaUtils.js";

test("auditoria percorre todas as vendas com no máximo 25 por página sem perder referências", () => {
  const registros = Array.from({ length: 72 }, (_, id) => ({ id, assinatura: `assinatura-${id}` }));
  const paginas = [1, 2, 3].map((pagina) => paginarAuditoria(registros, pagina));
  assert.ok(paginas.every((pagina) => pagina.itens.length <= 25 && pagina.total === 72));
  assert.deepEqual(
    paginas.flatMap((pagina) => pagina.itens),
    registros,
  );
  assert.equal(paginas[1].itens[0], registros[25]);
  assert.equal(registros.length, 72);
});

test("auditoria limita a página quando a seleção fica menor e mantém filtros completos", () => {
  const registros = Array.from({ length: 60 }, (_, id) => ({
    id,
    pagamentos: [{ forma_pagamento: id < 3 ? "Pix" : "Dinheiro", valor: 10 }],
  }));
  const selecionadas = filtrarVendasAuditoria(registros, "pix");
  const pagina = paginarAuditoria(selecionadas, 3);
  assert.equal(pagina.pagina, 1);
  assert.equal(pagina.total, 3);
  assert.deepEqual(
    pagina.itens.map((item) => item.id),
    [0, 1, 2],
  );
  assert.equal(formasAuditoria({ vendas: registros }).length, 2);
});

test("auditoria sem registros mantém página válida e não mostra itens de outra seleção", () => {
  assert.deepEqual(paginarAuditoria([], 4), {
    itens: [],
    pagina: 1,
    total: 0,
    totalPaginas: 1,
  });
});

const vendas = [
  {
    id: 1,
    caixa_origem_id: 227,
    pagamentos: [
      { id: 11, forma_pagamento: "PIX", valor: 120, caixa_id: null, status: "pendente" },
      { id: 12, forma_pagamento: "cartao", modalidade_cartao: "credito", valor: 90, caixa_id: 228 },
      { id: 13, forma_pagamento: "Dinheiro", valor: 10, caixa_id: null },
    ],
    recebimentos: [{ tipo: "movimentacao", id: 101, forma_pagamento: "Dinheiro", valor: 10 }],
  },
  {
    id: 2,
    caixa_origem_id: 227,
    pagamentos: [],
    recebimentos: [],
  },
  {
    id: 3,
    caixa_origem_id: 227,
    pagamentos: [{ id: 31, forma_pagamento: "Crediário", intervalo_crediario: "30", valor: 80 }],
    recebimentos: [],
  },
  {
    id: 4,
    caixa_origem_id: 226,
    pagamentos: [{ id: 41, forma_pagamento: "Cartão de débito", valor: 35, caixa_id: 226 }],
    recebimentos: [{ tipo: "pagamento", id: 42, forma_pagamento: "pix", valor: 20 }],
  },
];

test("sem filtro mantém todas as vendas, inclusive sem pagamento ou recebimento", () => {
  assert.deepEqual(
    filtrarVendasAuditoria(vendas).map((venda) => venda.id),
    [1, 2, 3, 4],
  );
});

test("filtro considera o histórico sem caixa e pagamentos feitos em outro caixa", () => {
  assert.deepEqual(
    filtrarVendasAuditoria(vendas, "pix").map((venda) => venda.id),
    [1, 4],
  );
  assert.deepEqual(
    filtrarVendasAuditoria(vendas, "cartao de credito").map((venda) => venda.id),
    [1],
  );
});

test("plano crediário aparece mesmo sem recebimento vinculado", () => {
  assert.deepEqual(
    filtrarVendasAuditoria(vendas, "crediario").map((venda) => venda.id),
    [3],
  );
});

test("filtro sem pagamentos usa os registros e não infere saldo pelos recebimentos", () => {
  const semRegistro = {
    id: 5,
    pagamentos: [],
    recebimentos: [{ forma_pagamento: "Dinheiro", valor: 15 }],
  };
  assert.deepEqual(
    filtrarVendasAuditoria([...vendas, semRegistro], FILTRO_SEM_PAGAMENTOS).map(
      (venda) => venda.id,
    ),
    [2, 5],
  );
  assert.deepEqual(filtrarVendasAuditoria([semRegistro], "dinheiro"), [semRegistro]);
});

test("histórico conserva status inválidos para auditoria, sem modificar registros", () => {
  const pagamento = { id: 7, forma_pagamento: "Boleto", valor: 50, status: "estornado" };
  const venda = { id: 7, pagamentos: [pagamento], recebimentos: [] };
  assert.equal(pagamentosVendaAuditoria(venda)[0], pagamento);
  assert.deepEqual(filtrarVendasAuditoria([venda], "boleto"), [venda]);
  assert.equal(pagamento.status, "estornado");
});

test("formas disponíveis unem histórico, recebimentos e lançamentos sem repetir aliases", () => {
  const formas = formasAuditoria({
    resumo: {
      pagamentos_vendas_por_forma_pagamento: { PIX: { total: 140 }, cartao_credito: { total: 90 } },
      recebimentos_por_forma_pagamento: { Dinheiro: { total: 10 } },
    },
    vendas,
    pagamentos: [{ forma_pagamento: "Boleto" }],
    movimentacoes: [{ forma_pagamento: null, tipo: "sangria" }],
  });
  assert.deepEqual(formas.map((forma) => forma.chave).sort(), [
    "boleto",
    "cartao de credito",
    "cartao de debito",
    "crediario",
    "dinheiro",
    "pix",
  ]);
  assert.equal(
    formas.find((forma) => forma.chave === "cartao de credito").rotulo,
    "Cartão de crédito",
  );
});

test("normalização une caixa, acentos e modalidade de cartão", () => {
  assert.equal(
    chaveFormaAuditoria({ forma_pagamento: "PIX" }),
    chaveFormaAuditoria({ forma_pagamento: "pix" }),
  );
  assert.equal(
    chaveFormaAuditoria({ forma_pagamento: "Cartão de crédito" }),
    chaveFormaAuditoria({ forma_pagamento: "cartao_credito" }),
  );
  assert.equal(
    chaveFormaAuditoria({ forma_pagamento: "Cartão", modalidade_cartao: "débito" }),
    chaveFormaAuditoria({ forma_pagamento: "cartao_debito" }),
  );
});

test("filtro de lançamentos preserva dinheiro manual e não inclui formas só presentes nas vendas", () => {
  const lancamentos = [
    { id: 1, forma_pagamento: null },
    { id: 2, forma_pagamento: "PIX" },
  ];
  assert.deepEqual(filtrarLancamentosAuditoria(lancamentos, "dinheiro"), [lancamentos[0]]);
  assert.deepEqual(filtrarLancamentosAuditoria(lancamentos, "pix"), [lancamentos[1]]);
  assert.deepEqual(filtrarLancamentosAuditoria(lancamentos, "cartao de credito"), []);
  assert.deepEqual(filtrarLancamentosAuditoria(lancamentos, FILTRO_SEM_PAGAMENTOS), []);
});

test("resposta antiga sem histórico usa recebimentos como compatibilidade sem substituir lista vazia explícita", () => {
  const recebimentos = [{ forma_pagamento: "Pix", valor: 10 }];
  assert.equal(pagamentosVendaAuditoria({ recebimentos }), recebimentos);
  assert.deepEqual(pagamentosVendaAuditoria({ pagamentos: [], recebimentos }), []);
});
