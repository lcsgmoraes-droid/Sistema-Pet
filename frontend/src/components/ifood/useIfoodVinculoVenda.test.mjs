import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createControllerHarness } from "../../../scripts/helpers/reactControllerHarness.mjs";

function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}
function setup(canEdit = true) {
  const requests = { search: [], link: [] };
  const saved = [];
  const request = (type, id, payload, config) => {
    const value = deferred();
    requests[type].push({ id, payload, config, ...value });
    return value.promise;
  };
  const harness = createControllerHarness(
    fileURLToPath(new URL("./useIfoodVinculoVenda.js", import.meta.url)),
    {
      props: {
        enabled: true,
        orderId: "order-a",
        canEdit,
        onVinculado: (order) => saved.push(order),
      },
      mocks: new Map([
        [
          "../../api/ifood",
          {
            getIfoodVendasCandidatas: (id, params, config) => request("search", id, params, config),
            vincularIfoodVenda: (id, payload, config) => request("link", id, payload, config),
          },
        ],
        ["./ifoodPresentation", { mensagemErroIfood: (_, fallback) => fallback }],
      ]),
      globals: { AbortController },
    },
  );
  async function search(linkable = true) {
    await harness.act(() => harness.tree.alterar("busca", "42"));
    let promise;
    await harness.act(() => {
      promise = harness.tree.buscar();
    });
    requests.search.at(-1).resolve({
      data: {
        sales: [
          {
            venda_id: 42,
            numero: 100,
            linkable,
            missing: linkable ? [] : ["Sem prova histórica"],
          },
        ],
      },
    });
    await promise;
    await harness.settle();
  }
  async function ready(linkable = true) {
    await search(linkable);
    await harness.act(() => harness.tree.alterar("vendaId", 42));
    await harness.act(() =>
      harness.tree.alterar("sourceNote", "Conferência fictícia dos itens desta venda"),
    );
    await harness.act(() => harness.tree.alterar("confirmado", true));
  }
  return { harness, requests, saved, search, ready };
}

test("vínculo exige permissão e confirmação explícita; busca não escolhe venda automaticamente", async () => {
  const denied = setup(false);
  await denied.harness.act(() => denied.harness.tree.alterar("busca", "42"));
  await denied.harness.act(() => denied.harness.tree.buscar());
  assert.equal(denied.requests.search.length, 0);
  const env = setup();
  await env.search();
  assert.deepEqual(env.requests.search[0].payload, { busca: "42" });
  assert.equal(env.harness.tree.vendaId, "");
  await env.harness.act(() => env.harness.tree.confirmar());
  assert.equal(env.requests.link.length, 0);
  await env.ready(false);
  await env.harness.act(() => env.harness.tree.confirmar());
  assert.equal(env.requests.link.length, 0);
});

test("falha de vínculo mantém seleção, confirmação e justificativa; clique duplicado envia uma vez", async () => {
  const env = setup();
  await env.ready();
  let saving;
  await env.harness.act(() => {
    saving = env.harness.tree.confirmar();
  });
  await env.harness.act(() => env.harness.tree.confirmar());
  assert.equal(env.requests.link.length, 1);
  assert.deepEqual(env.requests.link[0].payload, {
    venda_id: 42,
    source_note: "Conferência fictícia dos itens desta venda",
  });
  env.requests.link[0].reject(new Error("502"));
  await saving;
  await env.harness.settle();
  assert.equal(env.harness.tree.vendaId, 42);
  assert.equal(env.harness.tree.confirmado, true);
  assert.match(env.harness.tree.erro, /rascunho foi mantido/);
});

test("rascunhos são separados por pedido e preservados ao fechar ou inativar a aba", async () => {
  const env = setup();
  await env.ready();
  await env.harness.update({ orderId: "order-b" });
  assert.equal(env.harness.tree.sourceNote, "");
  assert.equal(env.harness.tree.vendaId, "");
  await env.harness.update({ orderId: null, enabled: false });
  await env.harness.update({ orderId: "order-a", enabled: true });
  assert.equal(env.harness.tree.vendaId, 42);
  assert.equal(env.harness.tree.confirmado, true);
  assert.match(env.harness.tree.sourceNote, /Conferência fictícia/);
});

test("resposta de busca de outro pedido é descartada; confirmação retorna ordem sem copiar custo no rascunho", async () => {
  const env = setup();
  await env.harness.act(() => env.harness.tree.alterar("busca", "42"));
  let old;
  await env.harness.act(() => {
    old = env.harness.tree.buscar();
  });
  await env.harness.update({ orderId: "order-b" });
  assert.equal(env.requests.search[0].config.signal.aborted, true);
  env.requests.search[0].resolve({ data: { sales: [{ venda_id: 999 }] } });
  await old;
  await env.harness.settle();
  assert.deepEqual(env.harness.tree.sales, []);
  assert.equal(env.harness.tree.ocupado, false);
  await env.ready();
  let saving;
  await env.harness.act(() => {
    saving = env.harness.tree.confirmar();
  });
  const order = {
    order_id: "order-b",
    effective_cmv: "60.00",
    effective_cmv_source: "erp_original_stock_out",
    manual_costs: null,
  };
  env.requests.link[0].resolve({ data: order });
  await saving;
  await env.harness.settle();
  assert.equal(env.saved[0], order);
  assert.equal(env.harness.tree.confirmado, false);
  assert.equal(Object.hasOwn(env.harness.tree, "cmv"), false);
});
