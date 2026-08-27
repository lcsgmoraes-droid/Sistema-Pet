import assert from "node:assert/strict";
import test from "node:test";

import {
  buildOpsTenantCommercialForm,
  buildOpsTenantCommercialPayload,
  buildOpsTenantOnboardingForm,
  buildOpsTenantOnboardingPayload,
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
      pilot: { status: "active", needs_follow_up: false },
    },
    {
      status: "suspended",
      billing_status: "past_due",
      base_catalog: { installed: false },
      counts: { produtos: 0 },
      usage: { records_total: 2, image_bytes: 0 },
      pilot: { status: "blocked", needs_follow_up: true },
    },
  ];

  const summaries = buildOpsTenantTabSummaries(items, {
    total: 2,
    active: 1,
    with_base_catalog: 1,
  });

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
  assert.deepEqual(summaries.pilot, {
    active: 1,
    blocked: 1,
    pending: 0,
    needFollowUp: 1,
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

test("buildOpsTenantOnboardingForm monta acompanhamento salvo", () => {
  const form = buildOpsTenantOnboardingForm({
    onboarding_follow_up: {
      owner_name: "Ana Operacoes",
      unblocked_on: "2026-08-27",
      next_contact_on: "2026-08-30",
      satisfaction: "satisfied",
    },
  });

  assert.deepEqual(form, {
    owner_name: "Ana Operacoes",
    unblocked_on: "2026-08-27",
    next_contact_on: "2026-08-30",
    satisfaction: "satisfied",
  });
});

test("buildOpsTenantOnboardingPayload permite alterar e limpar campos", () => {
  const payload = buildOpsTenantOnboardingPayload(
    {
      owner_name: "Ana",
      unblocked_on: "2026-08-20",
      next_contact_on: "2026-08-28",
      satisfaction: "not_collected",
    },
    {
      owner_name: "  Lucas  ",
      unblocked_on: "",
      next_contact_on: "2026-09-01",
      satisfaction: "neutral",
    },
  );

  assert.deepEqual(payload, {
    owner_name: "Lucas",
    unblocked_on: null,
    next_contact_on: "2026-09-01",
    satisfaction: "neutral",
  });
});
