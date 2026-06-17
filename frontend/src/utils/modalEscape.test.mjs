import assert from "node:assert/strict";
import test from "node:test";

import { createEscapeCloseRegistry, shouldCloseModalWithKeyboardEvent } from "./modalEscape.js";

test("shouldCloseModalWithKeyboardEvent aceita apenas Escape sem modificadores", () => {
  assert.equal(shouldCloseModalWithKeyboardEvent({ key: "Escape" }), true);
  assert.equal(shouldCloseModalWithKeyboardEvent({ key: "Esc" }), true);
  assert.equal(shouldCloseModalWithKeyboardEvent({ key: "Enter" }), false);
  assert.equal(shouldCloseModalWithKeyboardEvent({ key: "Escape", ctrlKey: true }), false);
  assert.equal(shouldCloseModalWithKeyboardEvent({ key: "Escape", altKey: true }), false);
  assert.equal(shouldCloseModalWithKeyboardEvent({ key: "Escape", shiftKey: true }), false);
  assert.equal(shouldCloseModalWithKeyboardEvent({ key: "Escape", defaultPrevented: true }), false);
  assert.equal(shouldCloseModalWithKeyboardEvent(null), false);
});

test("registry fecha apenas o modal ativo mais recente", () => {
  const registry = createEscapeCloseRegistry();
  const fechados = [];

  registry.register({ onClose: () => fechados.push("primeiro") });
  registry.register({ onClose: () => fechados.push("segundo") });

  const event = fakeKeyboardEvent("Escape");
  registry.handleKeyDown(event);

  assert.deepEqual(fechados, ["segundo"]);
  assert.equal(event.prevented, true);
  assert.equal(event.stopped, true);
});

test("registry ignora entradas desativadas e eventos que nao sao Escape", () => {
  const registry = createEscapeCloseRegistry();
  const fechados = [];

  registry.register({ onClose: () => fechados.push("primeiro") });
  registry.register({ disabled: () => true, onClose: () => fechados.push("segundo") });

  registry.handleKeyDown(fakeKeyboardEvent("Enter"));
  registry.handleKeyDown(fakeKeyboardEvent("Escape"));

  assert.deepEqual(fechados, ["primeiro"]);
});

function fakeKeyboardEvent(key) {
  return {
    key,
    prevented: false,
    stopped: false,
    preventDefault() {
      this.prevented = true;
    },
    stopPropagation() {
      this.stopped = true;
    },
  };
}
