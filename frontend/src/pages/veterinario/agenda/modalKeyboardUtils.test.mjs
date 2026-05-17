import assert from "node:assert/strict";
import test from "node:test";

import { shouldCloseModalWithKeyboardEvent } from "./modalKeyboardUtils.js";

test("shouldCloseModalWithKeyboardEvent fecha somente com Escape sem modificadores", () => {
  assert.equal(shouldCloseModalWithKeyboardEvent({ key: "Escape" }), true);
  assert.equal(shouldCloseModalWithKeyboardEvent({ key: "Esc" }), true);
  assert.equal(shouldCloseModalWithKeyboardEvent({ key: "Enter" }), false);
  assert.equal(shouldCloseModalWithKeyboardEvent({ key: "Escape", ctrlKey: true }), false);
  assert.equal(shouldCloseModalWithKeyboardEvent(null), false);
});
