export const OPS_TENANT_TABS = [
  { id: "tenants", label: "Tenants" },
  { id: "catalog", label: "Importacao" },
  { id: "billing", label: "Planos" },
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
  ].includes(String(status || "").trim().toLowerCase());
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
      items.filter((item) => ["active", "ativo"].includes(String(item?.status || "").toLowerCase())).length,
  );
  const installed = Number(
    summary?.with_base_catalog ?? items.filter((item) => item?.base_catalog?.installed).length,
  );
  const suspended = items.filter((item) =>
    ["suspended", "blocked", "bloqueado"].includes(String(item?.status || "").toLowerCase()),
  ).length;
  const attention = Number(
    summary?.billing_attention ?? items.filter((item) => isBillingAttention(item?.billing_status)).length,
  );
  const recordsTotal = Number(
    summary?.records_total ??
      items.reduce((totalRecords, item) => totalRecords + Number(item?.usage?.records_total || 0), 0),
  );
  const imageBytes = Number(
    summary?.image_bytes ??
      items.reduce((totalBytes, item) => totalBytes + Number(item?.usage?.image_bytes || 0), 0),
  );

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
    usage: {
      recordsTotal,
      imageBytes,
      imageStorage: formatStorageMb(imageBytes),
    },
  };
}
