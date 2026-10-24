import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createControllerHarness } from "../../../scripts/helpers/reactControllerHarness.mjs";

const saved = {
  id: 7,
  codigo: "018631.1",
  codigo_barras: "0789000000011",
  nome: "Produto fictício",
  preco_venda: 100,
  preco_custo: 60,
  preco_ifood: 110,
  anunciar_ifood: true,
};
const publication = (extra = {}) => ({
  product_id: 7,
  merchant_id: "merchant-fixture",
  barcode: "0789000000011",
  snapshot_saved: saved,
  link: { mode: "existing", barcode: "0789000000011", stale: false },
  capabilities: {
    can_link: true,
    can_prepare: true,
    can_send: true,
    can_confirm: true,
    write_enabled: true,
  },
  pending: [],
  last_submission: null,
  last_confirmation: null,
  ...extra,
});
const deferred = () => {
  let resolve, reject;
  const promise = new Promise((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
};

async function setup({ draft = null, data = publication(), productId = 7 } = {}) {
  const calls = { reads: [], links: [], prepares: [], sends: [], confirmations: [] };
  const env = { data, failRead: false, failSend: null, pendingPrepare: null, pendingSend: null };
  const mocks = new Map([
    [
      "../../api/ifood",
      {
        getIfoodPublicacaoProduto: async (id) => {
          calls.reads.push(id);
          if (env.failRead) throw Error("offline");
          return { data: env.data };
        },
        vincularIfoodProduto: async (id, body) => {
          calls.links.push({ id, body });
          env.data = {
            ...env.data,
            link: { mode: body.mode, barcode: body.barcode, stale: false },
          };
          return { data: env.data };
        },
        prepararIfoodPublicacaoProduto: async (id, body) => {
          calls.prepares.push({ id, body });
          if (env.pendingPrepare) return env.pendingPrepare.promise;
          return {
            data: {
              dry_run: true,
              eligible: true,
              pending: [],
              operation: body.operation,
              fields: body.fields,
              payload: { barcode: env.data.barcode },
              review_token: "review-saved-version",
              publication: env.data,
            },
          };
        },
        enviarIfoodPublicacaoProduto: async (id, body) => {
          calls.sends.push({ id, body });
          if (env.failSend) throw env.failSend;
          if (env.pendingSend) return env.pendingSend.promise;
          env.data = { ...env.data, last_submission: { id: 9, status: "accepted" } };
          return {
            data: {
              status: "accepted",
              submission: env.data.last_submission,
              publication: env.data,
            },
          };
        },
        confirmarIfoodProdutoPortal: async (id, body) => {
          calls.confirmations.push({ id, body });
          env.data = {
            ...env.data,
            last_confirmation: { ...body, actor_id: 1, confirmed_at: "2026-10-23T12:00:00Z" },
          };
          return { data: env.data };
        },
      },
    ],
    ["../../api/produtos", { getProduto: async () => ({ data: saved }) }],
  ]);
  const harness = createControllerHarness(
    fileURLToPath(new URL("./useIfoodPublicacaoProduto.js", import.meta.url)),
    {
      props: { productId, draft },
      mocks,
      globals: {
        AbortController,
        crypto: { randomUUID: () => "00000000-0000-4000-8000-000000000001" },
      },
    },
  );
  await harness.settle();
  return { env, calls, harness };
}

async function revisar(harness) {
  await harness.act(() => harness.tree.preparar());
  await harness.act(() => harness.tree.alterar("confirmSend", true));
}

test("preparação local envia um único ID e nunca publica sem confirmação", async () => {
  const { harness, calls } = await setup();
  await harness.act(() => harness.tree.alterar("fields", ["stock"]));
  await harness.act(() => harness.tree.preparar());
  assert.deepEqual(calls.prepares, [{ id: 7, body: { operation: "update", fields: ["stock"] } }]);
  await harness.act(() => harness.tree.enviar());
  assert.equal(calls.sends.length, 0);
  await harness.act(() => harness.tree.alterar("confirmSend", true));
  await harness.act(() => harness.tree.enviar());
  assert.deepEqual(calls.sends[0], {
    id: 7,
    body: {
      operation: "update",
      fields: ["stock"],
      review_token: "review-saved-version",
      request_key: "00000000-0000-4000-8000-000000000001",
      confirm_send: true,
    },
  });
  assert.equal(harness.tree.publication.last_submission.status, "accepted");
  assert.equal(harness.tree.publication.last_confirmation, null);
  assert.match(harness.tree.success, /ainda precisa ser conferida/);
});

test("vínculo exige conferência explícita, preserva EAN com zero e não escreve produto", async () => {
  const { harness, calls } = await setup();
  await harness.act(() => harness.tree.vincular());
  assert.equal(calls.links.length, 0);
  await harness.act(() => harness.tree.alterar("mode", "new"));
  await harness.act(() => harness.tree.alterar("portalChecked", true));
  await harness.act(() => harness.tree.vincular());
  assert.deepEqual(calls.links[0], {
    id: 7,
    body: {
      merchant_id: "merchant-fixture",
      barcode: "0789000000011",
      mode: "new",
      portal_checked: true,
    },
  });
  assert.equal(harness.tree.operation, "create");
  assert.equal(calls.sends.length, 0);
  assert.equal(harness.tree.portalChecked, false);
});

test("rascunho editado antes da montagem bloqueia todas as ações sem perder campos", async () => {
  const draft = { ...saved, preco_ifood: 125, descricao: "Texto ainda em edição" };
  const { harness, calls } = await setup({ draft });
  assert.equal(harness.tree.dirty, true);
  await harness.act(() => harness.tree.alterar("portalChecked", true));
  await harness.act(() => harness.tree.vincular());
  await harness.act(() => harness.tree.preparar());
  await harness.act(() => harness.tree.alterar("confirmPortal", true));
  await harness.act(() => harness.tree.confirmar());
  assert.equal(calls.links.length + calls.prepares.length + calls.confirmations.length, 0);
  assert.equal(draft.preco_ifood, 125);
  assert.equal(draft.descricao, "Texto ainda em edição");
});

test("cadastro sem ID ou sem capacidade do servidor não libera operações", async () => {
  const missing = await setup({ productId: null });
  assert.equal(missing.calls.reads.length, 0);
  const { harness, calls } = await setup({ data: publication({ capabilities: {} }) });
  await harness.act(() => harness.tree.alterar("portalChecked", true));
  await harness.act(() => harness.tree.vincular());
  await harness.act(() => harness.tree.preparar());
  assert.equal(harness.tree.canPrepare, false);
  assert.equal(calls.links.length + calls.prepares.length, 0);
});

test("falha de leitura mantém acompanhamento e rascunhos, mas bloqueia ações", async () => {
  const { harness, calls, env } = await setup();
  await harness.act(() => harness.tree.alterar("observedPrice", 120));
  env.failRead = true;
  await harness.act(() => harness.tree.atualizar());
  assert.equal(harness.tree.publication.barcode, "0789000000011");
  assert.equal(harness.tree.observedPrice, 120);
  assert.equal(harness.tree.stale, true);
  assert.equal(harness.tree.canPrepare, false);
  await harness.act(() => harness.tree.preparar());
  assert.equal(calls.prepares.length, 0);
});

test("alterar campos invalida a prévia e a autorização, sem envio automático", async () => {
  const { harness, calls } = await setup();
  await revisar(harness);
  await harness.act(() => harness.tree.alterar("fields", ["price"]));
  assert.equal(harness.tree.review, null);
  assert.equal(harness.tree.confirmSend, false);
  assert.equal(calls.sends.length, 0);
});

test("edição durante preparação descarta revisão recebida, sem sobrescrever rascunho", async () => {
  const { harness, calls, env } = await setup({ draft: { ...saved, descricao: "" } });
  env.pendingPrepare = deferred();
  const promise = harness.tree.preparar();
  await harness.settle();
  await harness.update({ draft: { ...saved, descricao: "", preco_ifood: 122 } });
  env.pendingPrepare.resolve({
    data: { eligible: true, review_token: "old", publication: env.data },
  });
  await promise;
  await harness.settle();
  assert.equal(harness.tree.review, null);
  assert.equal(harness.tree.dirty, true);
  assert.equal(calls.sends.length, 0);
});

test("timeout de envio vira incerteza local e nunca repete POST automaticamente", async () => {
  const { harness, calls, env } = await setup();
  await revisar(harness);
  env.failSend = Error("timeout");
  await harness.act(() => harness.tree.enviar());
  assert.equal(harness.tree.uncertain, true);
  assert.equal(harness.tree.canPrepare, false);
  await harness.act(() => harness.tree.enviar());
  await harness.act(() => harness.tree.preparar());
  assert.equal(calls.sends.length, 1);
  assert.equal(harness.tree.publication.last_confirmation, null);
});

test("403 revoga ações sem apagar histórico nem declarar publicação", async () => {
  const { harness, env } = await setup();
  await revisar(harness);
  env.failSend = { response: { status: 403 } };
  await harness.act(() => harness.tree.enviar());
  assert.equal(harness.tree.stale, true);
  assert.equal(harness.tree.uncertain, false);
  assert.equal(harness.tree.review, null);
  assert.equal(harness.tree.publication.last_confirmation, null);
  assert.match(harness.tree.error, /permissão/);
});

test("conferência manual mantém desconhecido diferente de zero e não envia ao iFood", async () => {
  const { harness, calls } = await setup();
  await harness.act(() => harness.tree.alterar("observedStock", 0));
  await harness.act(() => harness.tree.alterar("confirmPortal", true));
  await harness.act(() => harness.tree.confirmar());
  assert.deepEqual(calls.confirmations[0].body, {
    merchant_id: "merchant-fixture",
    barcode: "0789000000011",
    present: true,
    price: null,
    stock: 0,
  });
  assert.equal(calls.sends.length, 0);
  assert.equal(harness.tree.publication.last_confirmation.actor_id, 1);
});

test("cliques duplos geram somente uma tentativa com a chave preparada", async () => {
  const { harness, env, calls } = await setup();
  await revisar(harness);
  env.pendingSend = deferred();
  const a = harness.tree.enviar();
  const b = harness.tree.enviar();
  assert.equal(calls.sends.length, 1);
  env.pendingSend.resolve({ data: { status: "accepted", publication: env.data } });
  await Promise.all([a, b]);
  await harness.settle();
  assert.equal(harness.tree.review, null);
});
