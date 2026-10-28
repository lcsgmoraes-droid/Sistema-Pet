import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createControllerHarness } from "../../../../scripts/helpers/reactControllerHarness.mjs";

test("catálogo restrito prioriza código público e mantém IDs apenas na seleção", async () => {
  const selecoes = [];
  const itens = [
    { id: 9001, codigo: "200", nome: "Ração para cães" },
    { id: 200, codigo: "777", nome: "Ração para gatos" },
  ];
  const harness = createControllerHarness(
    fileURLToPath(new URL("./useBuscaEntidadeLocal.js", import.meta.url)),
    {
      props: { itens, valueId: "", onChangeId: (id) => selecoes.push(id), tipo: "produto" },
      mocks: new Map(),
      invoke: (hook, props) => hook(props),
    },
  );
  await harness.act(() => harness.tree.onChange("200"));
  assert.deepEqual(
    harness.tree.suggestions.map((item) => item.id),
    [9001],
  );
  await harness.act(() => harness.tree.onSelect(itens[0]));
  assert.equal(selecoes.at(-1), "9001");
  await harness.update({ valueId: "9001" });
  await harness.act(() => harness.tree.onChange("racao gatos"));
  await harness.update({ valueId: "" });
  assert.equal(harness.tree.value, "racao gatos");
  assert.deepEqual(
    harness.tree.suggestions.map((item) => item.id),
    [200],
  );
});
