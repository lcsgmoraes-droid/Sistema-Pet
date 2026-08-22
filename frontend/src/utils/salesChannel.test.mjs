import assert from "node:assert/strict";
import { test } from "node:test";

import {
  benefitChannelFromSalesChannel,
  getSalesChannelInfo,
  isOnlineSalesChannel,
  normalizeSalesChannel,
} from "./salesChannel.js";

test("WhatsApp é preservado como origem própria da venda", () => {
  assert.equal(normalizeSalesChannel("WhatsApp"), "whatsapp");
  assert.equal(getSalesChannelInfo("whatsapp").label, "WhatsApp");
  assert.equal(isOnlineSalesChannel("whatsapp"), true);
});

test("WhatsApp usa o escopo de benefícios do ecommerce", () => {
  assert.equal(benefitChannelFromSalesChannel("whatsapp"), "ecommerce");
});
