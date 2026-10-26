import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createControllerHarness } from "../../scripts/helpers/reactControllerHarness.mjs";

test("adaptador de tutor preserva digitação ao limpar seleção e busca na célula comum", async () => {
  const timers = new Map();
  const chamadas = [];
  const selecoes = [];
  const propTypes = {
    string: {},
    number: {},
    bool: {},
    func: { isRequired: {} },
    shape: () => ({}),
    oneOfType: () => ({}),
  };
  const harness = createControllerHarness(
    fileURLToPath(new URL("./TutorAutocomplete.jsx", import.meta.url)),
    {
      props: {
        selectedTutor: { id: 5, codigo: "2061", nome: "Pessoa anterior" },
        onSelect: (item) => selecoes.push(item),
      },
      mocks: new Map([
        ["prop-types", { __esModule: true, default: propTypes }],
        [
          "../api/clientes",
          {
            buscarClientes: async (params) => {
              chamadas.push(params);
              return [{ id: 8, codigo: "123", nome: "João" }];
            },
          },
        ],
        ["./v2/BuscaPessoa/BuscaPessoa", { __esModule: true, default: "BuscaPessoa" }],
      ]),
      globals: {
        setTimeout: (callback) => {
          const id = timers.size + 1;
          timers.set(id, callback);
          return id;
        },
        clearTimeout: (id) => timers.delete(id),
      },
    },
  );
  await harness.settle();
  await harness.act(() => harness.tree.props.onChange("joao"));
  assert.equal(selecoes.at(-1), null);
  await harness.update({ selectedTutor: null });
  assert.equal(harness.tree.props.value, "joao");
  for (const callback of [...timers.values()]) await callback();
  await harness.settle();
  assert.equal(chamadas.at(-1).search, "joao");
  assert.equal(harness.tree.type, "BuscaPessoa");
  assert.equal(harness.tree.props.suggestions[0].codigo, "123");
});
