import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createControllerHarness } from "../../scripts/helpers/reactControllerHarness.mjs";

function prepare(vendaAtual) {
  const opens = [],
    alerts = [];
  const harness = createControllerHarness(
    fileURLToPath(new URL("./usePDVVendaAcoes.js", import.meta.url)),
    {
      exportName: "usePDVVendaAcoes",
      mocks: new Map(),
      props: {
        vendaAtual: { status: "aberta", itens: [{}], ...vendaAtual },
        vendedorObrigatorio: false,
        vendaComissionada: false,
        setMostrarModalPagamento: (value) => opens.push(value),
      },
      globals: { alert: (message) => alerts.push(message) },
    },
  );
  return { harness, opens, alerts };
}

test("acao de receber no PDV bloqueia iFood online ou modo nao comprovado", () => {
  for (const summary of [
    { enabled: true, payment_mode: "online" },
    { enabled: false, payment_mode: "unknown" },
    undefined,
  ]) {
    const env = prepare({ canal: "ifood", ifood_pdv_pilot: summary });
    env.harness.tree.abrirModalPagamento();
    assert.deepEqual(env.opens, []);
    assert.match(env.alerts[0], /sem cobrança manual autorizada/);
  }
});

test("recebimento de app, ecommerce e iFood offline comprovado permanece disponivel", () => {
  for (const venda of [
    { canal: "app" },
    { canal: "ecommerce" },
    { canal: "ifood", ifood_pdv_pilot: { enabled: true, payment_mode: "offline" } },
  ]) {
    const env = prepare(venda);
    env.harness.tree.abrirModalPagamento();
    assert.deepEqual(env.opens, [true]);
    assert.deepEqual(env.alerts, []);
  }
});
