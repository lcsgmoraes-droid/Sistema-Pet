import assert from "node:assert/strict";
import test from "node:test";

import {
  buildOpsTenantCommercialForm,
  buildOpsTenantCommercialPayload,
  buildOpsTenantTabSummaries,
  formatStorageMb,
  isBillingAttention,
} from "./opsTenantsUtils.js";

test("isBillingAttention marca status de cobranca que precisam acompanhamento", () => {
  assert.equal(isBillingAttention("past_due"), true);
  assert.equal(isBillingAttention("overdue"), true);
  assert.equal(isBillingAttention("inadimplente"), true);
  assert.equal(isBillingAttention("active"), false);
  assert.equal(isBillingAttention("trial"), false);
});

test("formatStorageMb formata bytes de imagem em MB brasileiro", () => {
  assert.equal(formatStorageMb(1572864), "1,50 MB");
  assert.equal(formatStorageMb(0), "0,00 MB");
});

test("buildOpsTenantTabSummaries resume tenants por aba do MVP Ops", () => {
  const items = [
    {
      status: "active",
      billing_status: "active",
      base_catalog: { installed: true },
      counts: { produtos: 3 },
      usage: { records_total: 18, image_bytes: 1572864 },
    },
    {
      status: "suspended",
      billing_status: "past_due",
      base_catalog: { installed: false },
      counts: { produtos: 0 },
      usage: { records_total: 2, image_bytes: 0 },
    },
  ];

  const summaries = buildOpsTenantTabSummaries(items, { total: 2, active: 1, with_base_catalog: 1 });

  assert.deepEqual(summaries.tenants, {
    total: 2,
    active: 1,
    suspended: 1,
  });
  assert.deepEqual(summaries.catalog, {
    installed: 1,
    pending: 1,
  });
  assert.deepEqual(summaries.billing, {
    attention: 1,
  });
  assert.deepEqual(summaries.usage, {
    recordsTotal: 20,
    imageBytes: 1572864,
    imageStorage: "1,50 MB",
  });
});

test("buildOpsTenantCommercialForm monta formulario editavel com valores atuais", () => {
  const form = buildOpsTenantCommercialForm({
    status: "active",
    plan: "basico",
    billing_status: "trial",
    subscription_source: "manual",
  });

  assert.deepEqual(form, {
    status: "active",
    plan: "basico",
    billing_status: "trial",
    subscription_source: "manual",
  });
});

test("buildOpsTenantCommercialPayload envia somente campos alterados", () => {
  const payload = buildOpsTenantCommercialPayload(
    {
      status: "active",
      plan: "basico",
      billing_status: "trial",
      subscription_source: "manual",
    },
    {
      status: "active",
      plan: "premium",
      billing_status: " active ",
      subscription_source: "manual",
    },
  );

  assert.deepEqual(payload, {
    plan: "premium",
    billing_status: "active",
  });
});
