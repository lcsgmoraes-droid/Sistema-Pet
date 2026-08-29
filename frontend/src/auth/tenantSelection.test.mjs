import assert from "node:assert/strict";

import { findTenantOption, normalizeTenantOptions } from "./tenantSelection.js";

const tenants = normalizeTenantOptions([
  { id: "gabi", name: "GS Multi Marcas", role_id: 36 },
  { id: "atacadao", name: "Atacadão das Rações Pet", role_id: 1 },
  { id: "gabi", name: "Duplicado ignorado" },
  { id: "", name: "Sem identificador" },
]);

assert.deepEqual(
  tenants.map((tenant) => tenant.id),
  ["atacadao", "gabi"],
  "as empresas devem ser validas, unicas e ordenadas para a escolha",
);

assert.equal(findTenantOption(tenants, "gabi")?.name, "GS Multi Marcas");
assert.equal(findTenantOption(tenants, "desconhecido"), null);
assert.deepEqual(normalizeTenantOptions(null), []);
