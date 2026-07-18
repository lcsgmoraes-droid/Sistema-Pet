import assert from "node:assert/strict";
import { publicPlans, serviceInvoiceAddon } from "../src/data/publicPlans.js";

const pricesBySegment = Object.fromEntries(
  Object.entries(publicPlans).map(([segment, plans]) => [segment, plans.map((plan) => plan.price)]),
);

assert.deepEqual(pricesBySegment.pet, ["49,90", "197,00", "397,00", "697,00"]);
assert.deepEqual(pricesBySegment.vet, ["79,90", "247,00", "497,00"]);
assert.deepEqual(pricesBySegment.grooming, ["59,90", "117,00", "157,00"]);
assert.equal(serviceInvoiceAddon.price, "59,90");

for (const [segment, plans] of Object.entries(publicPlans)) {
  assert.ok(plans.length >= 3, `${segment} precisa apresentar sua escada de planos`);
  assert.equal(new Set(plans.map((plan) => plan.id)).size, plans.length);
  assert.ok(plans.every((plan) => plan.name && plan.description && plan.features.length >= 4));
}

console.log("Public plans contract OK");
