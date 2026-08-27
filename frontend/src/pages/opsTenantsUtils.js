export const OPS_TENANT_TABS = [
  { id: "tenants", label: "Tenants" },
  { id: "catalog", label: "Importacao" },
  { id: "billing", label: "Planos" },
  { id: "pilot", label: "Pilotos" },
  { id: "usage", label: "Uso" },
];

export function isBillingAttention(status) {
  return [
    "past_due",
    "overdue",
    "late",
    "inadimplente",
    "suspended",
    "blocked",
    "bloqueado",
  ].includes(
    String(status || "")
      .trim()
      .toLowerCase(),
  );
}

export function formatStorageMb(bytes) {
  const value = Number(bytes || 0) / 1024 / 1024;
  return `${value.toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })} MB`;
}

export function buildOpsTenantTabSummaries(items = [], summary = {}) {
  const total = Number(summary?.total ?? items.length);
  const active = Number(
    summary?.active ??
      items.filter((item) => ["active", "ativo"].includes(String(item?.status || "").toLowerCase()))
        .length,
  );
  const installed = Number(
    summary?.with_base_catalog ?? items.filter((item) => item?.base_catalog?.installed).length,
  );
  const suspended = items.filter((item) =>
    ["suspended", "blocked", "bloqueado"].includes(String(item?.status || "").toLowerCase()),
  ).length;
  const attention = Number(
    summary?.billing_attention ??
      items.filter((item) => isBillingAttention(item?.billing_status)).length,
  );
  const recordsTotal = Number(
    summary?.records_total ??
      items.reduce(
        (totalRecords, item) => totalRecords + Number(item?.usage?.records_total || 0),
        0,
      ),
  );
  const imageBytes = Number(
    summary?.image_bytes ??
      items.reduce((totalBytes, item) => totalBytes + Number(item?.usage?.image_bytes || 0), 0),
  );
  const pilotActive = Number(
    summary?.pilots_active ??
      items.filter((item) => String(item?.pilot?.status || "") === "active").length,
  );
  const pilotBlocked = Number(
    summary?.pilots_blocked ??
      items.filter((item) => String(item?.pilot?.status || "") === "blocked").length,
  );
  const pilotNeedFollowUp = Number(
    summary?.pilots_need_follow_up ??
      items.filter((item) => {
        const pilot = item?.pilot || {};
        if (typeof pilot.needs_follow_up === "boolean") return pilot.needs_follow_up;
        return String(pilot.status || "") !== "active";
      }).length,
  );
  const pilotPending = items.filter((item) =>
    ["pending", "ready"].includes(String(item?.pilot?.status || "")),
  ).length;

  return {
    tenants: {
      total,
      active,
      suspended,
    },
    catalog: {
      installed,
      pending: Math.max(total - installed, 0),
    },
    billing: {
      attention,
    },
    pilot: {
      active: pilotActive,
      blocked: pilotBlocked,
      pending: pilotPending,
      needFollowUp: pilotNeedFollowUp,
    },
    usage: {
      recordsTotal,
      imageBytes,
      imageStorage: formatStorageMb(imageBytes),
    },
  };
}

export function buildOpsTenantCommercialForm(tenant = {}) {
  return {
    status: String(tenant?.status || "active")
      .trim()
      .toLowerCase(),
    plan: String(tenant?.plan || "basico")
      .trim()
      .toLowerCase(),
    billing_status: String(tenant?.billing_status || "active")
      .trim()
      .toLowerCase(),
    subscription_source: String(tenant?.subscription_source || "manual")
      .trim()
      .toLowerCase(),
  };
}

export function buildOpsTenantCommercialPayload(current = {}, next = {}) {
  return ["status", "plan", "billing_status", "subscription_source"].reduce((payload, field) => {
    const currentValue = String(current?.[field] || "")
      .trim()
      .toLowerCase();
    const nextValue = String(next?.[field] || "")
      .trim()
      .toLowerCase();
    if (nextValue && nextValue !== currentValue) {
      payload[field] = nextValue;
    }
    return payload;
  }, {});
}

export function buildOpsTenantOnboardingForm(tenant = {}) {
  const followUp = tenant?.onboarding_follow_up || {};
  return {
    owner_name: String(followUp.owner_name || "").trim(),
    unblocked_on: String(followUp.unblocked_on || "").trim(),
    next_contact_on: String(followUp.next_contact_on || "").trim(),
    satisfaction: String(followUp.satisfaction || "not_collected")
      .trim()
      .toLowerCase(),
  };
}

export function buildOpsTenantOnboardingPayload(current = {}, next = {}) {
  return ["owner_name", "unblocked_on", "next_contact_on", "satisfaction"].reduce(
    (payload, field) => {
      const currentValue = String(current?.[field] || "").trim();
      const nextValue = String(next?.[field] || "").trim();
      if (nextValue !== currentValue) {
        payload[field] =
          field === "satisfaction" ? nextValue || "not_collected" : nextValue || null;
      }
      return payload;
    },
    {},
  );
}
