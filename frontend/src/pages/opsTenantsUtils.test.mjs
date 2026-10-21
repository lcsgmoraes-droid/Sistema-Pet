import assert from "node:assert/strict";
import test from "node:test";

import {
  buildOpsTenantCommercialForm,
  buildOpsTenantCommercialPayload,
  buildOpsTenantOnboardingForm,
  buildOpsTenantOnboardingPayload,
  buildOpsTenantTabSummaries,
  formatStorageMb,
  getOpsTenantBlockingAuthorizationError,
  groupOpsTenantsByClient,
  isBillingAttention,
  requiresOpsTenantBlockingAuthorization,
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
      counts: { produtos: 3 },
      usage: { records_total: 18, image_bytes: 1572864 },
      pilot: { status: "active", needs_follow_up: false },
    },
    {
      status: "suspended",
      billing_status: "past_due",
      counts: { produtos: 0 },
      usage: { records_total: 2, image_bytes: 0 },
      pilot: { status: "blocked", needs_follow_up: true },
    },
  ];

  const summaries = buildOpsTenantTabSummaries(items, {
    total: 2,
    active: 1,
  });

  assert.deepEqual(summaries.tenants, {
    total: 2,
    active: 1,
    suspended: 1,
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

test("groupOpsTenantsByClient agrupa por grupo comercial e marca inadimplencia", () => {
  const items = [
    {
      id: "t1",
      name: "Loja A",
      billing_status: "active",
      grupo_comercial: { id: 10, nome: "Cliente Grupo" },
    },
    {
      id: "t2",
      name: "Loja B",
      billing_status: "past_due",
      grupo_comercial: { id: 10, nome: "Cliente Grupo" },
    },
    {
      id: "t3",
      name: "Loja Solo",
      billing_status: "active",
      grupo_comercial: null,
    },
  ];

  const groups = groupOpsTenantsByClient(items);

  assert.equal(groups.length, 2);
  const grupo = groups.find((group) => group.grupoId === 10);
  assert.ok(grupo);
  assert.equal(grupo.nome, "Cliente Grupo");
  assert.equal(grupo.lojaCount, 2);
  assert.equal(grupo.adimplente, false);
  assert.deepEqual(
    grupo.inadimplentes.map((loja) => loja.id),
    ["t2"],
  );

  const solo = groups.find((group) => group.grupoId === null);
  assert.ok(solo);
  assert.equal(solo.nome, "Loja Solo");
  assert.equal(solo.lojaCount, 1);
  assert.equal(solo.adimplente, true);
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
    billing_status: "trial",
    blocking_authorized_by_lucas: false,
    blocking_authorization_reason: "",
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
    billing_status: "active",
  });
});

test("suspensão exige nova autorização e motivo antes de enviar comprovação", () => {
  const current = buildOpsTenantCommercialForm({ status: "active" });
  for (const status of ["suspended", "inactive", "trial"]) {
    const next = { ...current, status };
    assert.equal(requiresOpsTenantBlockingAuthorization(current, next), true);
    assert.match(getOpsTenantBlockingAuthorizationError(current, next), /autorização explícita/);
    assert.deepEqual(buildOpsTenantCommercialPayload(current, next), { status });
    assert.deepEqual(
      buildOpsTenantCommercialPayload(current, {
        ...next,
        blocking_authorization_reason: "Motivo informado sem marcar a autorização do Lucas.",
      }),
      { status },
    );
    assert.deepEqual(
      buildOpsTenantCommercialPayload(current, {
        ...next,
        blocking_authorized_by_lucas: true,
        blocking_authorization_reason: "curto",
      }),
      { status },
    );
    assert.match(
      getOpsTenantBlockingAuthorizationError(current, {
        ...next,
        blocking_authorized_by_lucas: true,
        blocking_authorization_reason: "curto",
      }),
      /10 caracteres/,
    );
    assert.deepEqual(
      buildOpsTenantCommercialPayload(current, {
        ...next,
        blocking_authorized_by_lucas: true,
        blocking_authorization_reason:
          " Lucas autorizou por telefone em 21/10; encerramento solicitado. ",
      }),
      {
        status,
        blocking_authorized_by_lucas: true,
        blocking_authorization_reason:
          "Lucas autorizou por telefone em 21/10; encerramento solicitado.",
      },
    );
  }
});

test("reativação e ajuste de cobrança não exigem nem enviam autorização de bloqueio", () => {
  for (const [current, next, expected] of [
    [{ status: "suspended" }, { status: "active" }, { status: "active" }],
    [
      { status: "active", billing_status: "active" },
      { status: "active", billing_status: "past_due" },
      { billing_status: "past_due" },
    ],
    [
      { status: "inactive", billing_status: "trial" },
      { status: "inactive", billing_status: "active" },
      { billing_status: "active" },
    ],
  ]) {
    const form = {
      ...next,
      blocking_authorized_by_lucas: true,
      blocking_authorization_reason: "Autorização anterior não pode ser reaproveitada.",
    };
    assert.equal(requiresOpsTenantBlockingAuthorization(current, form), false);
    assert.equal(getOpsTenantBlockingAuthorizationError(current, form), "");
    assert.deepEqual(buildOpsTenantCommercialPayload(current, form), expected);
  }
});

test("autorização salva nunca é pré-selecionada no formulário", () => {
  const form = buildOpsTenantCommercialForm({
    status: "suspended",
    blocking_authorized_by_lucas: true,
    blocking_authorization_reason: "Autorização de uma interrupção anterior.",
  });
  assert.equal(form.blocking_authorized_by_lucas, false);
  assert.equal(form.blocking_authorization_reason, "");
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
