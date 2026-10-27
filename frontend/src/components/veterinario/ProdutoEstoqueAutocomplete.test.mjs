import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elements,
} from "../../../scripts/helpers/reactControllerHarness.mjs";

test("insumo conserva fonte especializada e limpa loading ao apagar busca pendente", async () => {
  const timers = new Map();
  const chamadas = [];
  let sequencia = 0;
  const harness = createControllerHarness(
    fileURLToPath(new URL("./ProdutoEstoqueAutocomplete.jsx", import.meta.url)),
    {
      props: {
        onSelect() {},
        searchProducts: (termo) => new Promise((resolve) => chamadas.push({ termo, resolve })),
      },
      mocks: new Map([
        ["../v2/BuscaProduto/BuscaProduto", { __esModule: true, default: "BuscaProduto" }],
        ["../v2/BotaoInteracao/BotaoInteracao", { __esModule: true, default: "BotaoInteracao" }],
        [
          "../../pages/veterinario/vetApi",
          {
            vetApi: {
              listarProdutosEstoque() {
                throw new Error("Não trocar fonte especializada");
              },
            },
          },
        ],
      ]),
      globals: {
        setTimeout: (fn) => {
          timers.set(++sequencia, fn);
          return sequencia;
        },
        clearTimeout: (id) => timers.delete(id),
      },
    },
  );
  const campo = () => elements(harness.tree).find((node) => node.type === "BuscaProduto").props;
  const dispararTimer = async () => {
    const [id, fn] = [...timers].at(-1);
    timers.delete(id);
    fn();
    await harness.settle();
  };
  await harness.act(() => campo().onChange("primeira"));
  await dispararTimer();
  assert.equal(campo().loading, true);
  await harness.act(() => campo().onChange(""));
  assert.equal(campo().loading, false);
  chamadas[0].resolve({ data: [{ id: 1, nome: "Resposta antiga" }] });
  await harness.settle();
  assert.deepEqual(campo().suggestions, []);
  assert.equal(campo().loading, false);
  await harness.act(() => campo().onChange("nova"));
  await dispararTimer();
  chamadas[1].resolve({ data: [{ id: 2, codigo: "PUBLICO", nome: "Nova elegível" }] });
  await harness.settle();
  assert.equal(chamadas[1].termo, "nova");
  assert.equal(campo().suggestions[0].codigo, "PUBLICO");
  await harness.act(() => campo().onChange("outra"));
  assert.deepEqual(campo().suggestions, []);
  harness.unmount();
});
