export const normalizeTenantOptions = (tenants) => {
  if (!Array.isArray(tenants)) {
    return [];
  }

  const uniqueTenants = new Map();

  tenants.forEach((tenant) => {
    const id = String(tenant?.id || "").trim();
    const name = String(tenant?.name || "").trim();

    if (id && name && !uniqueTenants.has(id)) {
      uniqueTenants.set(id, { ...tenant, id, name });
    }
  });

  return [...uniqueTenants.values()].sort((first, second) =>
    first.name.localeCompare(second.name, "pt-BR", { sensitivity: "base" }),
  );
};

export const findTenantOption = (tenants, tenantId) => {
  const normalizedId = String(tenantId || "").trim();
  return normalizeTenantOptions(tenants).find((tenant) => tenant.id === normalizedId) || null;
};
