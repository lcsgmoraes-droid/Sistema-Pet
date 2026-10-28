import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createControllerHarness } from "../../../scripts/helpers/reactControllerHarness.mjs";

const componente = fileURLToPath(new URL("./useConferenciaFechamento.js", import.meta.url));
const assinatura = "a".repeat(64);
const snapshot = (saldo = 50, marca = "pendente", hash = assinatura) => ({
  resumo: { totais: { saldo_atual: saldo } },
  vendas: [{ id: 12, assinatura: hash, estado_conferencia: marca }],
  pagamentos: [],
  movimentacoes: [],
});
const adiar = () => {
  let resolve, reject;
  const promise = new Promise((sim, nao) => {
    resolve = sim;
    reject = nao;
  });
  return { promise, resolve, reject };
};

function preparar() {
  const leituras = [],
    gravacoes = [],
    gravacoesPix = [],
    resumos = [],
    abas = [],
    validacoes = [];
  const windowTarget = new EventTarget();
  windowTarget.open = (...args) => abas.push(args);
  const documento = new EventTarget();
  documento.visibilityState = "visible";
  const api = {
    validarCaixaAtual(id) {
      validacoes.push(id);
      return Promise.resolve({ id });
    },
    obterAuditoriaCaixa(id, opcoes) {
      const pendente = adiar();
      leituras.push({ ...pendente, id, opcoes });
      return pendente.promise;
    },
    conferirItemCaixa(id, dados) {
      const pendente = adiar();
      gravacoes.push({ ...pendente, id, dados });
      return pendente.promise;
    },
    identificarPixCaixa(id, dados) {
      const pendente = adiar();
      gravacoesPix.push({ ...pendente, id, dados });
      return pendente.promise;
    },
  };
  const h = createControllerHarness(componente, {
    props: { caixaId: 1, bloqueado: false },
    globals: { AbortController, window: windowTarget, document: documento },
    mocks: new Map([["../../api/caixa", api]]),
    invoke: (hook, props) =>
      hook(props.caixaId, {
        onResumo: (resumo) => resumos.push(resumo),
        bloqueado: props.bloqueado,
      }),
  });
  return {
    h,
    leituras,
    gravacoes,
    gravacoesPix,
    resumos,
    abas,
    validacoes,
    windowTarget,
    documento,
  };
}
async function iniciar(c) {
  await c.h.settle();
  c.leituras[0].resolve(snapshot());
  await c.h.settle();
}

test("resumo e assinatura chegam juntos; voltar à aba atualiza sem gravações", async () => {
  const c = preparar();
  await iniciar(c);
  assert.equal(c.h.tree.auditoria.vendas[0].assinatura, assinatura);
  assert.equal(c.resumos[0].totais.saldo_atual, 50);
  c.windowTarget.dispatchEvent(new Event("focus"));
  await c.h.settle();
  assert.equal(c.h.tree.bloqueado, true);
  c.leituras[1].resolve(snapshot(70, "pendente", "b".repeat(64)));
  await c.h.settle();
  assert.equal(c.resumos.at(-1).totais.saldo_atual, 70);
  assert.equal(c.h.tree.bloqueado, false);
  assert.equal(c.gravacoes.length, 0);
});

test("consulta abre somente URL em outra aba e não grava nem reabre a venda", async () => {
  const c = preparar();
  await iniciar(c);
  c.h.tree.abrirVenda(12);
  c.h.tree.abrirVenda("12&reabrir=true");
  assert.deepEqual(c.abas, [["/pdv?venda=12", "_blank", "noopener,noreferrer"]]);
  assert.equal(c.gravacoes.length, 0);
  assert.equal(c.leituras.length, 1);
});

test("OK só é exibido após POST e nova leitura; envio duplicado é recusado", async () => {
  const c = preparar();
  await iniciar(c);
  const item = c.h.tree.auditoria.vendas[0];
  const resultado = c.h.tree.salvar("venda", item, "ok", " Conferido ");
  await c.h.settle();
  assert.equal(await c.h.tree.salvar("venda", item, "ok"), false);
  assert.equal(c.h.tree.auditoria.vendas[0].estado_conferencia, "pendente");
  assert.deepEqual(c.gravacoes[0].dados, {
    tipo_item: "venda",
    item_id: 12,
    assinatura,
    estado: "ok",
    conferido: true,
    observacao: "Conferido",
  });
  c.gravacoes[0].resolve({ sucesso: true });
  await c.h.settle();
  assert.equal(c.h.tree.auditoria.vendas[0].estado_conferencia, "pendente");
  c.leituras[1].resolve(snapshot(50, "ok"));
  assert.equal(await resultado, true);
  await c.h.settle();
  assert.equal(c.h.tree.auditoria.vendas[0].estado_conferencia, "ok");
});

test("divergência exige nota; marca antiga, estado inválido e contexto bloqueado não gravam", async () => {
  const c = preparar();
  await iniciar(c);
  const item = c.h.tree.auditoria.vendas[0];
  for (const args of [
    ["venda", item, "divergencia", " "],
    ["venda", { ...item, assinatura: "velha" }, "ok"],
    ["venda", item, "outro"],
  ]) {
    assert.equal(await c.h.tree.salvar(...args), false);
  }
  await c.h.update({ bloqueado: true });
  assert.equal(await c.h.tree.salvar("venda", item, "ok"), false);
  c.windowTarget.dispatchEvent(new Event("focus"));
  await c.h.settle();
  assert.equal(c.gravacoes.length, 0);
  assert.equal(c.leituras.length, 1);
});

test("conflito atualiza o item e exige escolha nova, sem repetir aprovação", async () => {
  const c = preparar();
  await iniciar(c);
  const resultado = c.h.tree.salvar("venda", c.h.tree.auditoria.vendas[0], "ok");
  c.gravacoes[0].reject({ response: { status: 409 } });
  await c.h.settle();
  const novo = snapshot(80, "pendente", "c".repeat(64));
  novo.vendas[0].conferencia_alterada = true;
  c.leituras[1].resolve(novo);
  assert.equal(await resultado, false);
  await c.h.settle();
  assert.equal(c.gravacoes.length, 1);
  assert.equal(c.h.tree.auditoria.vendas[0].conferencia_alterada, true);
  assert.match(c.h.tree.erro, /Confira novamente/);
});

test("POST confirmado mas leitura falha mantém estado anterior e bloqueia até atualizar", async () => {
  const c = preparar();
  await iniciar(c);
  const resultado = c.h.tree.salvar(
    "venda",
    c.h.tree.auditoria.vendas[0],
    "divergencia",
    "Era crédito",
  );
  c.gravacoes[0].resolve({ sucesso: true });
  await c.h.settle();
  c.leituras[1].reject(new Error("offline"));
  assert.equal(await resultado, false);
  await c.h.settle();
  assert.equal(c.h.tree.bloqueado, true);
  assert.equal(c.h.tree.auditoria.vendas[0].estado_conferencia, "pendente");
  assert.match(c.h.tree.erro, /Conferência salva/);
  const atualizacao = c.h.tree.atualizar();
  await c.h.settle();
  c.leituras[2].resolve(snapshot(50, "divergencia"));
  await atualizacao;
  await c.h.settle();
  assert.equal(c.h.tree.bloqueado, false);
  assert.equal(c.h.tree.auditoria.vendas[0].estado_conferencia, "divergencia");
});

test("resposta de caixa anterior é cancelada e não sobrescreve a nova conferência", async () => {
  const c = preparar();
  await c.h.settle();
  await c.h.update({ caixaId: 2 });
  assert.equal(c.leituras[0].opcoes.signal.aborted, true);
  c.leituras[1].resolve(snapshot(90));
  await c.h.settle();
  c.leituras[0].resolve(snapshot(999));
  await c.h.settle();
  assert.deepEqual(
    c.resumos.map((r) => r.totais.saldo_atual),
    [90],
  );
  assert.equal(c.h.tree.auditoria.resumo.totais.saldo_atual, 90);
});

const snapshotPix = (estado = "nao_conferido", registroId = null, hash = assinatura) => ({
  ...snapshot(),
  pagamentos: [
    {
      id: 42,
      assinatura: hash,
      forma_pagamento: "Pix",
      valor: 50,
      identificacao_pix: {
        estado,
        registro_id: registroId,
        justificativa: registroId ? "Motivo salvo" : "",
        historico: [],
      },
    },
  ],
});
async function iniciarPix(c, dados = snapshotPix()) {
  await c.h.settle();
  c.leituras[0].resolve(dados);
  await c.h.settle();
  return c.h.tree.auditoria.pagamentos[0];
}

test("identificacao Pix exige motivo e metadados atuais, sem alterar conferencia financeira", async () => {
  const c = preparar();
  const item = await iniciarPix(c);
  for (const args of [
    [item, "identificado", " "],
    [item, "pendente", "motivo"],
    [{ ...item, assinatura: "velha" }, "identificado", "motivo"],
    [
      { ...item, identificacao_pix: { estado: "nao_conferido", registro_id: 99 } },
      "identificado",
      "motivo",
    ],
    [{ id: 123, assinatura }, "identificado", "motivo"],
  ])
    assert.equal(await c.h.tree.salvarPix(...args), false);
  assert.equal(c.gravacoesPix.length, 0);
  assert.equal(c.gravacoes.length, 0);
});

test("Pix nao identificado salva com motivo, rele servidor e continua permitindo fechar o caixa", async () => {
  const c = preparar();
  const item = await iniciarPix(c);
  const resultado = c.h.tree.salvarPix(
    item,
    "nao_identificado",
    "  Crédito não encontrado no extrato.  ",
  );
  assert.equal(await c.h.tree.salvarPix(item, "nao_identificado", "duplicado"), false);
  assert.equal(await c.h.tree.salvar("venda", c.h.tree.auditoria.vendas[0], "ok"), false);
  await c.h.settle();
  assert.equal(c.h.tree.auditoria.pagamentos[0].identificacao_pix.estado, "nao_conferido");
  assert.deepEqual(c.gravacoesPix[0].dados, {
    pagamento_id: 42,
    assinatura,
    registro_id: null,
    estado: "nao_identificado",
    justificativa: "Crédito não encontrado no extrato.",
  });
  c.gravacoesPix[0].resolve({ success: true });
  await c.h.settle();
  c.leituras[1].resolve(snapshotPix("nao_identificado", 17));
  assert.equal(await resultado, true);
  await c.h.settle();
  assert.equal(c.h.tree.auditoria.pagamentos[0].identificacao_pix.estado, "nao_identificado");
  assert.equal(c.h.tree.bloqueado, false);
  assert.equal(c.h.tree.ocupado, false);
  assert.equal(c.resumos.at(-1).totais.saldo_atual, 50);
  assert.equal(
    await c.h.tree.salvarPix(c.h.tree.auditoria.pagamentos[0], "nao_identificado", "mesmo estado"),
    false,
  );
  assert.equal(c.gravacoesPix.length, 1);
  assert.equal(c.gravacoes.length, 0);
});

test("conflito Pix atualiza registro e assinatura sem repetir a alteracao nem perder resumo", async () => {
  const c = preparar();
  const item = await iniciarPix(c, snapshotPix("nao_identificado", 17));
  const resultado = c.h.tree.salvarPix(item, "identificado", "Comprovante encontrado.");
  c.gravacoesPix[0].reject({ response: { status: 409 } });
  await c.h.settle();
  c.leituras[1].resolve(snapshotPix("nao_conferido", 18, "b".repeat(64)));
  assert.equal(await resultado, false);
  await c.h.settle();
  assert.equal(c.gravacoesPix.length, 1);
  assert.equal(c.h.tree.auditoria.pagamentos[0].identificacao_pix.registro_id, 18);
  assert.match(c.h.tree.erro, /Pix foi atualizado/);
  assert.equal(await c.h.tree.salvarPix(item, "identificado", "Repeticao antiga"), false);
  assert.equal(c.gravacoesPix.length, 1);
});

test("POST Pix salvo e leitura falha mantem estado anterior bloqueado ate recuperar uma leitura valida", async () => {
  const c = preparar();
  const item = await iniciarPix(c);
  const resultado = c.h.tree.salvarPix(item, "identificado", "Crédito confirmado.");
  c.gravacoesPix[0].resolve({ success: true });
  await c.h.settle();
  c.leituras[1].reject(new Error("offline"));
  assert.equal(await resultado, false);
  await c.h.settle();
  assert.equal(c.h.tree.bloqueado, true);
  assert.equal(c.h.tree.auditoria.pagamentos[0].identificacao_pix.estado, "nao_conferido");
  assert.match(c.h.tree.erro, /Identificação salva/);
  const leitura = c.h.tree.atualizar();
  await c.h.settle();
  c.leituras[2].resolve(snapshotPix("identificado", 18));
  await leitura;
  await c.h.settle();
  assert.equal(c.h.tree.bloqueado, false);
  assert.equal(c.h.tree.auditoria.pagamentos[0].identificacao_pix.estado, "identificado");
});
