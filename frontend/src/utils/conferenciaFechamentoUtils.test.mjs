import assert from "node:assert/strict";
import { test } from "node:test";
import {
  classeConferenciaCaixa,
  estadoConferenciaCaixa,
  localizarLancamentoConferencia,
  localizarVendaConferencia,
  urlConsultaVendaPdv,
} from "./conferenciaFechamentoUtils.js";

test("venda da composição conserva o registro e a assinatura originais da auditoria", () => {
  const item = Object.freeze({ id: 42, venda_id: 42, assinatura: "assinatura-original" });
  const resultado = localizarVendaConferencia({ vendas: [item] }, { venda_id: "42" });
  assert.equal(resultado.tipo, "venda");
  assert.equal(resultado.item, item);
  assert.equal(localizarVendaConferencia({ vendas: [item] }, item).item, item);
  assert.equal(localizarVendaConferencia({ vendas: [item] }, { venda_id: 41 }), null);
  assert.equal(localizarVendaConferencia({ vendas: [item] }, { venda_id: 42, id: 41 }), null);
  assert.equal(
    localizarVendaConferencia({ vendas: [{ id: 42, venda_id: 41 }] }, { venda_id: 42 }),
    null,
  );
});

test("lançamentos distinguem pagamento, crédito e movimento mesmo com IDs iguais", () => {
  const pagamento = Object.freeze({ id: 9, venda_id: 42, assinatura: "pagamento" });
  const movimento = Object.freeze({ id: 9, venda_id: 42, assinatura: "movimento" });
  const auditoria = { pagamentos: [pagamento], movimentacoes: [movimento] };
  for (const tipo of ["pagamento", "beneficio", "estorno"]) {
    const resultado = localizarLancamentoConferencia(auditoria, {
      id: "pagamento-9",
      origem: "pagamento",
      venda_id: "42",
      tipo,
    });
    assert.equal(resultado.tipo, "pagamento");
    assert.equal(resultado.item, pagamento);
  }
  const resultado = localizarLancamentoConferencia(auditoria, {
    id: "movimento-9",
    origem: "movimento",
    venda_id: 42,
  });
  assert.equal(resultado.tipo, "movimentacao");
  assert.equal(resultado.item, movimento);
});

test("devolução negativa da composição localiza o movimento positivo sem reconstruí-lo", () => {
  const item = { id: 31, venda_id: 42, tipo: "devolucao", valor: 20, assinatura: "original" };
  const resultado = localizarLancamentoConferencia(
    { movimentacoes: [item] },
    { id: "movimento-31", origem: "movimento", venda_id: 42, valor: -20 },
  );
  assert.equal(resultado.item, item);
  assert.equal(resultado.item.valor, 20);
});

test("espelho de baixa em lote não duplica a conferência nem substitui o pagamento ausente", () => {
  const pagamento = { id: 9, venda_id: 42, baixa_lote_id: 2, assinatura: "pagamento" };
  const espelho = { id: 31, pagamento_id: 9, venda_id: 42 };
  const auditoria = { pagamentos: [pagamento], espelhos_pagamentos: [espelho], movimentacoes: [] };
  assert.equal(
    localizarLancamentoConferencia(auditoria, { id: "pagamento-9", origem: "pagamento" }).item,
    pagamento,
  );
  assert.equal(
    localizarLancamentoConferencia(auditoria, { id: "movimento-31", origem: "movimento" }),
    null,
  );
  assert.equal(
    localizarLancamentoConferencia(
      { espelhos_pagamentos: [espelho] },
      { id: "pagamento-9", origem: "pagamento" },
    ),
    null,
  );
});

test("recusa prefixos inexatos, origem trocada e vínculo com outra venda", () => {
  const auditoria = {
    pagamentos: [{ id: 9, venda_id: 42 }],
    movimentacoes: [{ id: 9, venda_id: 42 }],
  };
  for (const lancamento of [
    { id: "pagamento-9", origem: "movimento" },
    { id: "movimento-9", origem: "pagamento" },
    { id: 9, origem: "pagamento" },
    { id: "pagamento-09", origem: "pagamento" },
    { id: "pagamento-9-extra", origem: "pagamento" },
    { id: " pagamento-9", origem: "pagamento" },
    { id: "pagamento-9", origem: "pagamento", venda_id: 41 },
    { id: "pagamento-9", origem: "pagamento", venda_id: 0 },
    { id: "pagamento-9007199254740992", origem: "pagamento" },
  ]) {
    assert.equal(localizarLancamentoConferencia(auditoria, lancamento), null);
  }
});

test("registros ausentes, duplicados e históricos legados não fabricam alvos", () => {
  assert.equal(localizarVendaConferencia(null, { venda_id: 42 }), null);
  assert.equal(
    localizarVendaConferencia({ vendas: [{ id: 42 }, { id: "42" }] }, { venda_id: 42 }),
    null,
  );
  assert.equal(
    localizarLancamentoConferencia(null, { id: "pagamento-9", origem: "pagamento" }),
    null,
  );
  assert.equal(localizarLancamentoConferencia({}, null), null);
  assert.equal(
    localizarLancamentoConferencia(
      { pagamentos: [{ id: 9 }, { id: "9" }] },
      { id: "pagamento-9", origem: "pagamento" },
    ),
    null,
  );
  const auditoria = { vendas: [{ id: 42, pagamentos: [{ id: 9, caixa_id: null }] }] };
  for (const [id, origem] of [
    ["recebimento-9", "recebimento"],
    ["conta-9", "conta_legada"],
    ["venda-legada-42", "venda_legada"],
    ["pagamento-9", "pagamento"],
  ]) {
    assert.equal(localizarLancamentoConferencia(auditoria, { id, origem }), null);
  }
});

test("estado canônico prevalece sobre booleano legado e mudança de conteúdo volta a pendente", () => {
  for (const estado of ["pendente", "ok", "divergencia"]) {
    assert.equal(estadoConferenciaCaixa({ estado_conferencia: estado, conferido: true }), estado);
    assert.equal(
      estadoConferenciaCaixa({
        estado_conferencia: estado,
        conferido: true,
        conferencia_alterada: true,
      }),
      "pendente",
    );
  }
  assert.equal(estadoConferenciaCaixa({ conferido: true }), "ok");
  for (const item of [
    null,
    {},
    { conferido: false },
    { conferido: "true" },
    { estado_conferencia: "inválido" },
  ]) {
    assert.equal(estadoConferenciaCaixa(item), "pendente");
  }
});

test("cada estado recebe borda e fundo próprios com suporte ao modo escuro", () => {
  for (const [estado, cor] of [
    ["ok", "emerald"],
    ["divergencia", "red"],
    ["pendente", "slate"],
  ]) {
    const classes = classeConferenciaCaixa({ estado_conferencia: estado }).split(" ");
    assert.ok(classes.includes("border"));
    assert.ok(classes.some((classe) => classe.startsWith(`border-${cor}-`)));
    assert.ok(classes.some((classe) => classe.startsWith(`dark:border-${cor}-`)));
    assert.ok(classes.some((classe) => classe.startsWith("bg-")));
    assert.ok(classes.some((classe) => classe.startsWith("dark:bg-")));
  }
  assert.equal(
    classeConferenciaCaixa(null),
    classeConferenciaCaixa({ estado_conferencia: "pendente" }),
  );
});

test("consulta de venda só gera URL interna para inteiro positivo seguro", () => {
  assert.equal(urlConsultaVendaPdv(42), "/pdv?venda=42");
  assert.equal(urlConsultaVendaPdv("42"), "/pdv?venda=42");
  assert.equal(
    urlConsultaVendaPdv(Number.MAX_SAFE_INTEGER),
    `/pdv?venda=${Number.MAX_SAFE_INTEGER}`,
  );
  for (const id of [
    null,
    undefined,
    true,
    {},
    [],
    0,
    -1,
    1.5,
    NaN,
    Infinity,
    Number.MAX_SAFE_INTEGER + 1,
    "",
    "0",
    "042",
    " 42 ",
    "42.0",
    "4e2",
    "42&editar=1",
    "42#x",
    "9007199254740992",
  ]) {
    assert.equal(urlConsultaVendaPdv(id), null);
  }
});
