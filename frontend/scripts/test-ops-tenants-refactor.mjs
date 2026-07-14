import fs from "node:fs";
import path from "node:path";
import process from "node:process";

const root = process.cwd();

function read(relativePath) {
  return fs.readFileSync(path.join(root, relativePath), "utf8");
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function lineCount(relativePath) {
  return read(relativePath).split(/\r?\n/).length;
}

const expectedFiles = [
  "src/pages/OpsTenants.jsx",
  "src/pages/ops-tenants/OpsTenantsPage.jsx",
  "src/pages/ops-tenants/useOpsTenantsController.js",
  "src/pages/ops-tenants/opsTenantsConstants.js",
  "src/pages/ops-tenants/opsTenantsFormatters.js",
  "src/pages/ops-tenants/OpsTenantsBadge.jsx",
  "src/pages/ops-tenants/OpsTenantsMetricCard.jsx",
  "src/pages/ops-tenants/OpsTenantsHeader.jsx",
  "src/pages/ops-tenants/OpsTenantsFilters.jsx",
  "src/pages/ops-tenants/OpsTenantsTabs.jsx",
  "src/pages/ops-tenants/OpsTenantsTable.jsx",
  "src/pages/ops-tenants/OpsTenantsImportPanel.jsx",
  "src/pages/ops-tenants/OpsTenantsGuardrailsPanel.jsx",
  "src/pages/ops-tenants/OpsTenantsCommercialEditPanel.jsx",
  "src/pages/ops-tenants/OpsTenantsBillingTab.jsx",
  "src/pages/ops-tenants/OpsTenantsUsageTab.jsx",
  "src/pages/ops-tenants/OpsTenantsPilotTab.jsx",
];

for (const relativePath of expectedFiles) {
  assert(fs.existsSync(path.join(root, relativePath)), `Missing ops tenants file: ${relativePath}`);
}

for (const relativePath of expectedFiles) {
  const lines = lineCount(relativePath);
  assert(lines <= 420, `${relativePath} has ${lines} lines; expected <= 420`);
}

const facadeSource = read("src/pages/OpsTenants.jsx");
assert(facadeSource.includes("OpsTenantsPage"), "OpsTenants.jsx should delegate to OpsTenantsPage");
assert(!facadeSource.includes("useState"), "OpsTenants.jsx should not own React state");
assert(!facadeSource.includes("api."), "OpsTenants.jsx should not own API calls");

const featureSource = expectedFiles
  .filter((relativePath) => relativePath.startsWith("src/pages/ops-tenants/"))
  .map(read)
  .join("\n");

for (const literal of [
  "/admin/tenants",
  "/catalog-import/preview",
  "/catalog-import/apply",
  "/commercial",
  "Clientes e catalogo base",
  "Importacao de catalogo base",
  "Planos e pagamentos",
  "Uso e cadastros",
  "Acompanhamento dos pilotos",
  "Guardrails do MVP",
  "Rode uma simulacao valida antes de aplicar a importacao.",
  "Manutencao salva.",
]) {
  assert(featureSource.includes(literal), `Missing ops tenants behavior literal: ${literal}`);
}

const routeSource = read("src/app/routes/OpsRoutes.jsx");
const lazySource = read("src/app/lazyPages.jsx");
assert(routeSource.includes('path="tenants"'), "Ops tenants route should remain registered");
assert(lazySource.includes("pages/OpsTenants"), "Lazy import should keep public OpsTenants path");

console.log("Ops tenants refactor contract OK");
