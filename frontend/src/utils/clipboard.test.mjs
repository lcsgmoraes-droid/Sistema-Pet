import assert from "node:assert/strict";

import { copyTextToClipboard } from "./clipboard.js";

let modernValue = "";
await copyTextToClipboard("Maria Oliveira", {
  navigatorObject: {
    clipboard: {
      writeText: async (value) => {
        modernValue = value;
      },
    },
  },
  documentObject: null,
});
assert.equal(modernValue, "Maria Oliveira");

let legacyValue = "";
let removed = false;
const textarea = {
  style: {},
  setAttribute() {},
  focus() {},
  select() {
    legacyValue = this.value;
  },
  setSelectionRange() {},
  remove() {
    removed = true;
  },
};
await copyTextToClipboard("DEMO-CLI-003", {
  navigatorObject: {
    clipboard: {
      writeText: async () => {
        throw new Error("bloqueado");
      },
    },
  },
  documentObject: {
    body: { appendChild() {} },
    createElement: () => textarea,
    execCommand: (command) => command === "copy",
  },
});
assert.equal(legacyValue, "DEMO-CLI-003");
assert.equal(removed, true);

console.log("clipboard: ok");
