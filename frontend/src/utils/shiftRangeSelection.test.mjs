import assert from "node:assert/strict";
import test from "node:test";

import { applyShiftRangeSelection, getShiftSelectionEvent } from "./shiftRangeSelection.js";

const items = [{ id: 1 }, { id: 2 }, { id: 3 }, { id: 4 }, { id: 5 }];

test("seleciona um intervalo inclusivo na ordem visivel", () => {
  assert.deepEqual(
    applyShiftRangeSelection({
      anchorId: 2,
      checked: true,
      currentSelection: [2],
      itemId: 5,
      items,
      shiftKey: true,
    }),
    [2, 3, 4, 5],
  );
});

test("desmarca o intervalo quando o checkbox final foi desmarcado", () => {
  assert.deepEqual(
    applyShiftRangeSelection({
      anchorId: 2,
      checked: false,
      currentSelection: [1, 2, 3, 4, 5],
      itemId: 4,
      items,
      shiftKey: true,
    }),
    [1, 5],
  );
});

test("ignora itens que nao podem ser selecionados", () => {
  assert.deepEqual(
    applyShiftRangeSelection({
      anchorId: 1,
      checked: true,
      currentSelection: [1],
      isItemSelectable: (item) => item.id !== 3,
      itemId: 5,
      items,
      shiftKey: true,
    }),
    [1, 2, 4, 5],
  );
});

test("mantem Set quando a tela usa Set para guardar a selecao", () => {
  const result = applyShiftRangeSelection({
    anchorId: 2,
    checked: true,
    currentSelection: new Set([2]),
    itemId: 4,
    items,
    shiftKey: true,
  });

  assert.ok(result instanceof Set);
  assert.deepEqual(Array.from(result), [2, 3, 4]);
});

test("faz selecao simples quando a ancora nao esta mais visivel", () => {
  assert.deepEqual(
    applyShiftRangeSelection({
      anchorId: 99,
      checked: true,
      currentSelection: [1],
      itemId: 4,
      items,
      shiftKey: true,
    }),
    [1, 4],
  );
});

test("le checked e Shift tanto do evento React quanto do evento nativo", () => {
  assert.deepEqual(
    getShiftSelectionEvent({
      nativeEvent: { shiftKey: true, target: { checked: true } },
      target: { checked: true },
    }),
    { checked: true, shiftKey: true },
  );
  assert.deepEqual(getShiftSelectionEvent(false), { checked: false, shiftKey: false });
});
