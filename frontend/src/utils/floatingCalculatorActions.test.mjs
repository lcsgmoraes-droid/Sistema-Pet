import assert from "node:assert/strict";
import test from "node:test";

import { getFloatingCalculatorActions } from "./floatingCalculatorActions.js";

test("inclui comparar preco no painel expandido da calculadora flutuante", () => {
  const actions = getFloatingCalculatorActions();

  assert.deepEqual(
    actions.map((action) => action.id),
    ["calcular-racao", "comparar-preco"],
  );
  assert.equal(actions[1].label, "Comparar Preco");
});
