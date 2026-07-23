import assert from "node:assert/strict";
import test from "node:test";

import { adicionarDias, formatData } from "./vacinaUtils.js";

test("formatData preserva a data civil sem recuar um dia", () => {
  assert.equal(formatData("2026-07-23"), "23/07/2026");
});

test("adicionarDias preserva a data civil", () => {
  assert.equal(adicionarDias("2026-07-23", 21), "2026-08-13");
});
