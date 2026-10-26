import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createControllerHarness } from "../../../scripts/helpers/reactControllerHarness.mjs";

test("XML usa termo completo numa consulta e descarta resposta da busca cancelada", async () => {
  const timers = new Map();
  const chamadas = [];
  let sequencia = 0;
  const api = {
    get: (url, config) => new Promise((resolve) => chamadas.push({ url, config, resolve })),
  };
  const harness = createControllerHarness(
    fileURLToPath(new URL("./useEntradaXmlProdutos.js", import.meta.url)),
    {
      props: { api, multiplicadoresPack: {}, toast: {}, setLoading() {} },
      invoke: (hook, props) => hook(props),
      mocks: new Map([
        ["../../services/corepetDialog", {}],
        ["./entradaXmlUtils", {}],
        ["./entradaXmlProdutosPricing", {}],
      ]),
      globals: {
        setTimeout: (callback) => {
          const id = ++sequencia;
          timers.set(id, callback);
          return id;
        },
        clearTimeout: (id) => timers.delete(id),
        AbortController,
      },
    },
  );
  const executarTimer = async () => {
    const [id, callback] = [...timers].at(-1);
    timers.delete(id);
    callback();
    await harness.settle();
  };
  await harness.act(() => harness.tree.atualizarFiltroProduto(7, "ração adulto"));
  await executarTimer();
  assert.equal(chamadas.length, 1);
  assert.equal(chamadas[0].config.params.busca, "ração adulto");
  assert.equal(chamadas[0].config.params.include_variations, true);
  await harness.act(() => harness.tree.atualizarFiltroProduto(7, "ração filhote"));
  assert.equal(chamadas[0].config.signal.aborted, true);
  await executarTimer();
  chamadas[1].resolve({ data: { items: [{ id: 2, codigo: "FILHOTE" }] } });
  await harness.settle();
  chamadas[0].resolve({ data: { items: [{ id: 1, codigo: "ADULTO" }] } });
  await harness.settle();
  assert.equal(harness.tree.resultadosBuscaProduto[7][0].codigo, "FILHOTE");
});
