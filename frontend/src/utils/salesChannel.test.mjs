import assert from "node:assert/strict";
import { test } from "node:test";

import {
  benefitChannelFromSalesChannel,
  getSalesChannelInfo,
  isOnlineSalesChannel,
  isCorepetOnlineSalesChannel,
  normalizeSalesChannel,
} from "./salesChannel.js";
import { campaignAllowsSaleChannel } from "./campaignChannelScope.js";

test("WhatsApp é preservado como origem própria da venda", () => {
  assert.equal(normalizeSalesChannel("WhatsApp"), "whatsapp");
  assert.equal(getSalesChannelInfo("whatsapp").label, "WhatsApp");
  assert.equal(isOnlineSalesChannel("whatsapp"), true);
});

test("WhatsApp usa o escopo de benefícios do ecommerce", () => {
  assert.equal(benefitChannelFromSalesChannel("whatsapp"), "ecommerce");
});

test("iFood conserva origem propria e nao habilita acoes locais de entrega", () => {
  assert.equal(normalizeSalesChannel(" iFood "), "ifood");
  assert.equal(normalizeSalesChannel("i-food"), "ifood");
  assert.equal(getSalesChannelInfo("IFOOD").value, "ifood");
  assert.equal(getSalesChannelInfo("ifood").label, "iFood");
  assert.equal(isOnlineSalesChannel("ifood"), true);
  assert.equal(isCorepetOnlineSalesChannel("ifood"), false);
  for (const channel of ["app", "ecommerce", "whatsapp"]) {
    assert.equal(isCorepetOnlineSalesChannel(channel), true);
  }
});

test("iFood nao herda beneficios da loja fisica, app ou ecommerce", () => {
  assert.equal(benefitChannelFromSalesChannel("ifood"), "ifood");
  assert.equal(campaignAllowsSaleChannel({}, "ifood"), false);
  assert.equal(campaignAllowsSaleChannel({ benefit_channels: ["loja_fisica"] }, "ifood"), false);
  assert.equal(campaignAllowsSaleChannel({ benefit_channels: "all" }, "ifood"), false);
  assert.equal(campaignAllowsSaleChannel({}, "app"), true);
});
