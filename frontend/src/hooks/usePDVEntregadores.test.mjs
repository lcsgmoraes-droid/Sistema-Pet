import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createControllerHarness } from "../../scripts/helpers/reactControllerHarness.mjs";

const courier = {
  id: 77,
  entregador_padrao: true,
  modelo_custo_entrega: "taxa_fixa",
  taxa_fixa_entrega: 8,
};

function pending() {
  let resolve;
  const promise = new Promise((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

function setup(initialSale, response) {
  let sale = initialSale;
  const writes = [];
  const requests = [];
  const harness = createControllerHarness(
    fileURLToPath(new URL("./usePDVEntregadores.js", import.meta.url)),
    {
      exportName: "usePDVEntregadores",
      invoke: (Hook, props) => Hook(props.vendaAtual, props.setVendaAtual),
      mocks: new Map([
        ["react-hot-toast", { __esModule: true, default: { error() {} } }],
        ["../utils/debug", { debugLog() {}, debugWarn() {} }],
        [
          "../api",
          {
            __esModule: true,
            default: {
              get: async (url) => {
                requests.push(url);
                if (url === "/clientes/") return response || { data: { items: [courier] } };
                throw new Error("Consulta de custo nao esperada");
              },
            },
          },
        ],
      ]),
      props: {
        vendaAtual: sale,
        setVendaAtual: (update) => {
          const next = typeof update === "function" ? update(sale) : update;
          if (next !== sale) writes.push(next);
          sale = next;
        },
      },
    },
  );
  return {
    harness,
    writes,
    requests,
    sale: () => sale,
    setSale: (value) => {
      sale = value;
    },
  };
}

test("resposta tardia do entregador padrao nao altera venda DELIVERY do iFood", async () => {
  const request = pending();
  const env = setup(
    { canal: "loja_fisica", tem_entrega: false, entregador_id: null },
    request.promise,
  );
  const ifood = { id: 42, canal: "ifood", tem_entrega: true, entregador_id: null };
  env.setSale(ifood);
  await env.harness.update({ vendaAtual: ifood });
  request.resolve({ data: { items: [courier] } });
  await env.harness.settle();
  await env.harness.act(() => env.harness.tree.selecionarEntregador(courier));
  assert.equal(env.harness.tree.entregadorSelecionado, null);
  assert.equal(env.harness.tree.custoOperacionalEntrega, 0);
  assert.equal(env.sale(), ifood);
  assert.equal(ifood.tem_entrega, true);
  assert.deepEqual(env.writes, []);
  assert.deepEqual(env.requests, ["/clientes/"]);
});

test("app e ecommerce preservam selecao do entregador padrao e custo local", async () => {
  for (const canal of ["app", "ecommerce"]) {
    const env = setup({ canal, tem_entrega: true, entregador_id: null });
    await env.harness.settle();
    assert.equal(env.harness.tree.entregadorSelecionado.id, 77);
    assert.equal(env.sale().entregador_id, 77);
    assert.equal(env.harness.tree.custoOperacionalEntrega, 8);
  }
});
