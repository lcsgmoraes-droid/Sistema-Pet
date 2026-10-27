import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createControllerHarness } from "../../../../scripts/helpers/reactControllerHarness.mjs";
import * as utils from "./amazonFiscalUtils.js";

function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}
const ready = () => ({
  id: 7,
  status: "ready",
  source_revision: 1,
  payload_hash: "snapshot-1",
  blockers: [],
  external_order_id: "701-0000000-0000000",
});
function setup(loadLists = false) {
  const calls = [];
  const api = Object.fromEntries(
    ["get", "post", "put"].map((method) => [
      method,
      (path, body) => {
        const pending = deferred();
        calls.push({ method, path, body, ...pending });
        return pending.promise;
      },
    ]),
  );
  const harness = createControllerHarness(
    fileURLToPath(new URL("./useAmazonFiscal.js", import.meta.url)),
    {
      invoke: (hook) => hook({ loadLists }),
      mocks: new Map([
        ["../../../services/api", { api }],
        ["../../../services/corepetDialog", { confirmarCorePet: async () => true }],
        ["./amazonFiscalUtils", utils],
      ]),
    },
  );
  async function open(order = ready()) {
    let pending;
    await harness.act(() => {
      pending = harness.tree.openOrder({ id: order.id });
    });
    calls.at(-1).resolve({ data: order });
    await pending;
    await harness.settle();
  }
  return { calls, harness, open };
}

test("carga inicial espera contas e pedidos; resposta descartada não atualiza tela desmontada", async () => {
  const { calls, harness } = setup(true);
  assert.equal(harness.tree.loading, true);
  assert.equal(calls.length, 2);
  calls[0].resolve({ data: { items: [{ id: 1 }] } });
  await harness.settle();
  assert.equal(harness.tree.loading, true);
  calls[1].resolve({ data: { items: [ready()], total: 1 } });
  await harness.settle();
  assert.equal(harness.tree.loading, false);
  assert.equal(harness.tree.orders.length, 1);
  harness.unmount();
});

test("política padrão e automação desativada; política por pagamento exige aceite explícito", async () => {
  const { calls, harness } = setup();
  const form = {
    seller_id: "QA-SELLER",
    emitter_cnpj: "11.222.333/0001-81",
    discount_policy: "buyer_payment_total",
  };
  await harness.act(() => harness.tree.saveAccount(form));
  assert.equal(calls.length, 0);
  assert.match(harness.tree.error, /Confirme/);
  let saving;
  await harness.act(() => {
    saving = harness.tree.saveAccount({
      ...form,
      discount_policy: "source_discounts",
      activated_at: "2000-01-01",
    });
  });
  await harness.act(() => harness.tree.saveAccount(form));
  assert.equal(calls.length, 1);
  assert.equal(calls[0].body.auto_issue_enabled, false);
  assert.equal(calls[0].body.emitter_cnpj, "11222333000181");
  assert.equal("activated_at" in calls[0].body, false);
  calls[0].resolve({ data: {} });
  await saving;
  await harness.settle();
});

test("emissão usa revisão e hash conferidos e impede envio duplicado", async () => {
  const env = setup();
  await env.open();
  let issuing;
  await env.harness.act(() => {
    issuing = env.harness.tree.issue(env.harness.tree.detail);
  });
  await env.harness.act(() => env.harness.tree.issue(env.harness.tree.detail));
  assert.equal(env.calls.length, 2);
  env.calls[1].resolve({ data: ready() });
  await env.harness.settle();
  const request = env.calls[2];
  assert.equal(request.path, `${utils.FISCAL_BASE}/orders/7/emitir`);
  assert.deepEqual(request.body, { expected_revision: 1, expected_payload_hash: "snapshot-1" });
  request.resolve({ data: { ...ready(), status: "authorized", numero: 9001 } });
  await issuing;
  await env.harness.settle();
  assert.equal(env.harness.tree.detail.status, "authorized");
  assert.equal(env.calls.filter((call) => call.path.endsWith("/emitir")).length, 1);
});

test("snapshot alterado durante revisão não emite e exige nova conferência", async () => {
  const env = setup();
  await env.open();
  let issuing;
  await env.harness.act(() => {
    issuing = env.harness.tree.issue(env.harness.tree.detail);
  });
  env.calls.at(-1).resolve({ data: { ...ready(), source_revision: 2, payload_hash: "new" } });
  await issuing;
  await env.harness.settle();
  assert.equal(
    env.calls.some((call) => call.path.endsWith("/emitir")),
    false,
  );
  assert.match(env.harness.tree.error, /atualizado/);
  assert.equal(env.harness.tree.detail.source_revision, 2);
});

test("resposta incerta e consulta indisponível desabilitam nova emissão", async () => {
  const env = setup();
  await env.open();
  let issuing;
  await env.harness.act(() => {
    issuing = env.harness.tree.issue(env.harness.tree.detail);
  });
  env.calls.at(-1).resolve({ data: ready() });
  await env.harness.settle();
  env.calls.at(-1).reject(new Error("Sem confirmação"));
  await env.harness.settle();
  assert.equal(env.calls.at(-1).method, "get");
  env.calls.at(-1).reject(new Error("Consulta indisponível"));
  await issuing;
  await env.harness.settle();
  assert.equal(env.harness.tree.detail.status, "unknown");
  await env.harness.act(() => env.harness.tree.issue(env.harness.tree.detail));
  assert.equal(env.calls.filter((call) => call.path.endsWith("/emitir")).length, 1);
});

test("abrir outro pedido ignora detalhes atrasados; modo Central não busca listas de configuração", async () => {
  const env = setup();
  assert.equal(env.calls.length, 0);
  let oldRequest;
  await env.harness.act(() => {
    oldRequest = env.harness.tree.openOrder({ id: 7 });
  });
  const old = env.calls.at(-1);
  await env.open({ ...ready(), id: 8 });
  old.resolve({ data: ready() });
  await oldRequest;
  await env.harness.settle();
  assert.equal(env.harness.tree.detail.id, 8);
  assert.equal(
    env.calls.every((call) => call.path.includes("/orders/")),
    true,
  );
});

test("revisão histórica não emite nem modifica versão ou consentimento no cliente", async () => {
  const env = setup();
  await env.open({ ...ready(), status: "blocked" });
  let review;
  await env.harness.act(() => {
    review = env.harness.tree.reviewHistorical(env.harness.tree.detail);
  });
  assert.deepEqual(env.calls.at(-1).body, { acknowledge_historical: true });
  assert.equal(env.calls.at(-1).path.endsWith("/review"), true);
  env.calls.at(-1).resolve({ data: ready() });
  await review;
  await env.harness.settle();
  assert.equal(
    env.calls.some((call) => call.path.endsWith("/emitir")),
    false,
  );
});
