import assert from "node:assert/strict";
import { test } from "node:test";

import { normalizeBenefitChannel } from "./campaignChannelScope.js";

test("normalizeBenefitChannel trata web e site como ecommerce", () => {
  assert.equal(normalizeBenefitChannel("web"), "ecommerce");
  assert.equal(normalizeBenefitChannel("site"), "ecommerce");
  assert.equal(normalizeBenefitChannel("e-commerce"), "ecommerce");
});

test("normalizeBenefitChannel preserva canais app e pdv", () => {
  assert.equal(normalizeBenefitChannel("app"), "app");
  assert.equal(normalizeBenefitChannel("aplicativo"), "app");
  assert.equal(normalizeBenefitChannel("pdv"), "loja_fisica");
});
