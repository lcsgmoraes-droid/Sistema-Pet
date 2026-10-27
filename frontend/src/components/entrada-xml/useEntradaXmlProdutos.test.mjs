import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createControllerHarness } from "../../../scripts/helpers/reactControllerHarness.mjs";

test("XML preserva simples/variações e descarta respostas canceladas", async () => {
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
  assert.equal(chamadas.length, 2);
  assert.equal(chamadas[0].config.params.busca, "ração adulto");
  assert.deepEqual(
    chamadas.map((chamada) => chamada.config.params.tipo_produto),
    ["SIMPLES", "VARIACAO"],
  );
  await harness.act(() => harness.tree.atualizarFiltroProduto(7, "ração filhote"));
  assert.equal(chamadas[0].config.signal.aborted, true);
  assert.equal(chamadas[1].config.signal.aborted, true);
  await executarTimer();
  chamadas[2].resolve({
    data: {
      items: [
        { id: 2, codigo: "FILHOTE", tipo_produto: "SIMPLES" },
        { id: 3, tipo_produto: "PAI" },
      ],
    },
  });
  chamadas[3].resolve({
    data: {
      items: [
        { id: 4, codigo: "FILHOTE-V", tipo_produto: "VARIACAO" },
        { id: 5, tipo_produto: "KIT" },
      ],
    },
  });
  await harness.settle();
  chamadas[0].resolve({ data: { items: [{ id: 1, codigo: "ADULTO" }] } });
  chamadas[1].resolve({ data: { items: [{ id: 6, codigo: "ADULTO-V" }] } });
  await harness.settle();
  assert.deepEqual(
    harness.tree.resultadosBuscaProduto[7].map((produto) => produto.id),
    [2, 4],
  );
  await harness.act(() => harness.tree.atualizarFiltroProduto(7, "outra busca"));
  assert.deepEqual(harness.tree.resultadosBuscaProduto[7], []);
  harness.unmount();
});
