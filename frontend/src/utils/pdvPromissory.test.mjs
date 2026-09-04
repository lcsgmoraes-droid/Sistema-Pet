import assert from "node:assert/strict";
import test from "node:test";

import { valorPorExtenso } from "./pdvPromissory.js";

test("escreve o valor da nota promissoria por extenso", () => {
  assert.equal(valorPorExtenso(390), "trezentos e noventa reais");
  assert.equal(valorPorExtenso(100.01), "cem reais e um centavo");
});
