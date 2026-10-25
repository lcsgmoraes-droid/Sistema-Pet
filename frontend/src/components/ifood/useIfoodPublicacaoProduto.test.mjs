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
  confirmation_context_token: "c".repeat(64),
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
  const env = {
    data,
    failRead: false,
    failSend: null,
    failConfirm: null,
    pendingPrepare: null,
    pendingSend: null,
    pendingConfirm: null,
  };
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
          if (env.failConfirm) throw env.failConfirm;
          if (env.pendingConfirm) return env.pendingConfirm.promise;
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
    portal_active: null,
    confirmation_context_token: "c".repeat(64),
    price: null,
    stock: 0,
  });
  assert.equal(calls.sends.length, 0);
  assert.equal(harness.tree.publication.last_confirmation.actor_id, 1);
});

test("disponibilidade só usa declaração explícita, inclusive inativo com estoque zero", async () => {
  for (const active of [true, false, null]) {
    const { harness, calls } = await setup({
      data: publication({ last_confirmation: { present: true, portal_active: true, stock: 21 } }),
    });
    assert.equal(harness.tree.observedActive, null);
    await harness.act(() => harness.tree.alterar("observedActive", active));
    await harness.act(() => harness.tree.alterar("observedStock", 0));
    await harness.act(() => harness.tree.alterar("confirmPortal", true));
    await harness.act(() => harness.tree.confirmar());
    assert.equal(calls.confirmations[0].body.portal_active, active);
    assert.equal(calls.confirmations[0].body.stock, 0);
    assert.equal(calls.sends.length, 0);
  }
});

test("alterar qualquer observação exige novo aceite e não apaga os valores em edição", async () => {
  const { harness, calls } = await setup();
  for (const [field, value] of [
    ["observedPrice", "154,90"],
    ["observedStock", "20"],
    ["observedActive", true],
    ["present", true],
  ]) {
    await harness.act(() => harness.tree.alterar("confirmPortal", true));
    await harness.act(() => harness.tree.alterar(field, value));
    assert.equal(harness.tree.confirmPortal, false);
    await harness.act(() => harness.tree.confirmar());
  }
  assert.equal(harness.tree.observedPrice, "154,90");
  assert.equal(harness.tree.observedStock, "20");
  assert.equal(harness.tree.observedActive, true);
  assert.equal(calls.confirmations.length, 0);
});

test("produto não localizado limpa disponibilidade, preço e estoque observados", async () => {
  const { harness, calls } = await setup();
  await harness.act(() => harness.tree.alterar("observedActive", false));
  await harness.act(() => harness.tree.alterar("observedPrice", "154,90"));
  await harness.act(() => harness.tree.alterar("observedStock", "20"));
  await harness.act(() => harness.tree.alterar("present", false));
  assert.equal(harness.tree.observedActive, null);
  assert.equal(harness.tree.observedPrice, null);
  assert.equal(harness.tree.observedStock, null);
  await harness.act(() => harness.tree.alterar("confirmPortal", true));
  await harness.act(() => harness.tree.confirmar());
  assert.equal(calls.confirmations[0].body.present, false);
  assert.equal(calls.confirmations[0].body.portal_active, null);
  assert.equal(calls.confirmations[0].body.price, null);
  assert.equal(calls.confirmations[0].body.stock, null);
});

test("troca de produto descarta a observação anterior sem predefinir disponibilidade", async () => {
  const { harness, env } = await setup();
  await harness.act(() => harness.tree.alterar("present", false));
  await harness.act(() => harness.tree.alterar("observedActive", true));
  await harness.act(() => harness.tree.alterar("observedStock", "20"));
  env.data = publication({ product_id: 8, barcode: "outro-ean" });
  await harness.update({ productId: 8 });
  await harness.settle();
  assert.equal(harness.tree.present, true);
  assert.equal(harness.tree.observedActive, null);
  assert.equal(harness.tree.observedStock, null);
  assert.equal(harness.tree.confirmPortal, false);
});

test("automação ativa aceita observação com contexto sem liberar envio ou vínculo manual", async () => {
  const sync = { enabled: true, status: "accepted", desired_stock: 21, last_accepted_stock: 21 };
  const last = { id: 8, status: "accepted", source: "auto_stock" };
  const { harness, calls } = await setup({
    data: publication({
      stock_sync: sync,
      last_submission: last,
      capabilities: { can_link: false, can_send: false, can_prepare: false, can_confirm: true },
    }),
  });
  await harness.act(() => harness.tree.alterar("observedActive", true));
  await harness.act(() => harness.tree.alterar("observedStock", 21));
  await harness.act(() => harness.tree.alterar("confirmPortal", true));
  assert.equal(harness.tree.canConfirm, true);
  assert.equal(harness.tree.canLink, false);
  assert.equal(harness.tree.canSend, false);
  await harness.act(() => harness.tree.confirmar());
  assert.equal(calls.confirmations[0].body.confirmation_context_token, "c".repeat(64));
  assert.deepEqual(harness.tree.publication.stock_sync, sync);
  assert.deepEqual(harness.tree.publication.last_submission, last);
  assert.equal(calls.links.length + calls.prepares.length + calls.sends.length, 0);
});

test("contexto novo descarta só o aceite e mantém a observação durante envio e retorno", async () => {
  const { harness, env, calls } = await setup();
  await harness.act(() => harness.tree.alterar("observedPrice", "154,90"));
  await harness.act(() => harness.tree.alterar("observedStock", "20"));
  await harness.act(() => harness.tree.alterar("observedActive", true));
  await harness.act(() => harness.tree.alterar("confirmPortal", true));
  env.data = publication({
    confirmation_context_token: "d".repeat(64),
    last_submission: { status: "sending" },
    capabilities: { can_confirm: false },
  });
  await harness.act(() => harness.tree.atualizar());
  assert.equal(harness.tree.confirmPortal, false);
  assert.equal(harness.tree.confirmationContextChanged, true);
  assert.equal(harness.tree.canConfirm, false);
  assert.equal(harness.tree.observedPrice, "154,90");
  assert.equal(harness.tree.observedStock, "20");
  assert.equal(harness.tree.observedActive, true);
  await harness.act(() => harness.tree.confirmar());
  assert.equal(calls.confirmations.length, 0);
  env.data = publication({ confirmation_context_token: "e".repeat(64) });
  await harness.act(() => harness.tree.atualizar());
  assert.equal(harness.tree.canConfirm, false);
  await harness.act(() => harness.tree.alterar("confirmPortal", true));
  await harness.act(() => harness.tree.confirmar());
  assert.equal(calls.confirmations[0].body.confirmation_context_token, "e".repeat(64));
});

test("atualizar o mesmo contexto preserva observação e aceite sem registrar automaticamente", async () => {
  const { harness, calls } = await setup();
  await harness.act(() => harness.tree.alterar("observedActive", false));
  await harness.act(() => harness.tree.alterar("observedStock", "0"));
  await harness.act(() => harness.tree.alterar("confirmPortal", true));
  await harness.act(() => harness.tree.atualizar());
  assert.equal(harness.tree.observedActive, false);
  assert.equal(harness.tree.observedStock, "0");
  assert.equal(harness.tree.confirmPortal, true);
  assert.equal(harness.tree.canConfirm, true);
  assert.equal(calls.confirmations.length, 0);
});

test("409 preserva rascunhos e exige atualização e novo aceite, sem GET ou POST automático", async () => {
  const { harness, env, calls } = await setup();
  await harness.act(() => harness.tree.alterar("observedActive", true));
  await harness.act(() => harness.tree.alterar("observedStock", "21"));
  await harness.act(() => harness.tree.alterar("confirmPortal", true));
  env.failConfirm = { response: { status: 409, data: { detail: "O acompanhamento mudou." } } };
  const readCount = calls.reads.length;
  await harness.act(() => harness.tree.confirmar());
  assert.equal(calls.reads.length, readCount);
  assert.equal(calls.confirmations.length, 1);
  assert.equal(harness.tree.observedStock, "21");
  assert.equal(harness.tree.observedActive, true);
  assert.equal(harness.tree.confirmPortal, false);
  assert.equal(harness.tree.stale, true);
  assert.equal(harness.tree.confirmationContextChanged, true);
  await harness.act(() => harness.tree.alterar("confirmPortal", true));
  await harness.act(() => harness.tree.confirmar());
  assert.equal(calls.confirmations.length, 1);
  env.failConfirm = null;
  env.data = publication({ confirmation_context_token: "d".repeat(64) });
  await harness.act(() => harness.tree.atualizar());
  assert.equal(harness.tree.confirmPortal, false);
  assert.equal(harness.tree.canConfirm, false);
  await harness.act(() => harness.tree.alterar("confirmPortal", true));
  await harness.act(() => harness.tree.confirmar());
  assert.equal(calls.confirmations.length, 2);
  assert.equal(calls.confirmations[1].body.confirmation_context_token, "d".repeat(64));
});

test("contexto ausente bloqueia confirmação mesmo quando uma capacidade antiga permite", async () => {
  const { harness, calls } = await setup({
    data: publication({ confirmation_context_token: null }),
  });
  await harness.act(() => harness.tree.alterar("confirmPortal", true));
  assert.equal(harness.tree.canConfirm, false);
  await harness.act(() => harness.tree.confirmar());
  assert.equal(calls.confirmations.length, 0);
});

test("resposta de confirmação do produto anterior não preenche o produto recém-aberto", async () => {
  const { harness, calls, env } = await setup();
  await harness.act(() => harness.tree.alterar("observedActive", true));
  await harness.act(() => harness.tree.alterar("confirmPortal", true));
  env.pendingConfirm = deferred();
  const pending = harness.tree.confirmar();
  await harness.settle();
  env.data = publication({ product_id: 8, confirmation_context_token: "d".repeat(64) });
  await harness.update({ productId: 8 });
  env.pendingConfirm.resolve({ data: publication() });
  await pending;
  await harness.settle();
  assert.equal(calls.confirmations.length, 1);
  assert.equal(calls.confirmations[0].id, 7);
  assert.equal(harness.tree.publication.product_id, 8);
  assert.equal(harness.tree.observedActive, null);
  assert.equal(harness.tree.confirmPortal, false);
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
