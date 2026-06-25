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
  "src/app/AppRoutePreloader.jsx",
  "src/app/AppRoutes.jsx",
  "src/app/lazyPages.jsx",
  "src/app/routes/PublicRoutes.jsx",
  "src/app/routes/OpsRoutes.jsx",
  "src/app/routes/RouteGates.jsx",
  "src/app/routes/CoreProtectedRoutes.jsx",
  "src/app/routes/VeterinaryRoutes.jsx",
  "src/app/routes/BathGroomingRoutes.jsx",
  "src/app/routes/ProductInventoryRoutes.jsx",
  "src/app/routes/SalesMarketingRoutes.jsx",
  "src/app/routes/PurchasingBlingRoutes.jsx",
  "src/app/routes/FinanceRoutes.jsx",
  "src/app/routes/CommissionRoutes.jsx",
  "src/app/routes/CatalogAdminRoutes.jsx",
  "src/app/routes/SettingsAdminRoutes.jsx",
  "src/app/routes/DeliveryAiRoutes.jsx",
];

for (const relativePath of expectedFiles) {
  assert(
    fs.existsSync(path.join(root, relativePath)),
    `Missing extracted route file: ${relativePath}`,
  );
}

const cappedFiles = ["src/App.jsx", ...expectedFiles];
for (const relativePath of cappedFiles) {
  const lines = lineCount(relativePath);
  assert(lines <= 420, `${relativePath} has ${lines} lines; expected <= 420`);
}

const appSource = read("src/App.jsx");
assert(
  !appSource.includes("lazy(() => import("),
  "src/App.jsx should not declare lazy page imports",
);
assert(!appSource.includes("<Route "), "src/App.jsx should not own route declarations");
assert(
  appSource.includes("<AppRoutes />"),
  "src/App.jsx should render the extracted AppRoutes component",
);
assert(
  appSource.includes("<AppRoutePreloader />"),
  "src/App.jsx should keep the preload hook through AppRoutePreloader",
);

const lazyPagesSource = read("src/app/lazyPages.jsx");
for (const exportName of [
  "Login",
  "Pessoas",
  "Produtos",
  "DashboardFinanceiro",
  "PDV",
  "VendasCanaisPreview",
  "WhatsAppDashboard",
]) {
  assert(
    new RegExp(`export const ${exportName}\\b`).test(lazyPagesSource),
    `lazyPages.jsx should export ${exportName}`,
  );
}

const routeSources = expectedFiles
  .filter(
    (relativePath) =>
      relativePath === "src/app/AppRoutes.jsx" ||
      relativePath.includes("/routes/") ||
      relativePath.includes("\\routes\\"),
  )
  .map(read)
  .join("\n");

for (const routeLiteral of [
  'path="/login"',
  'path="/:tenantId"',
  'path="/ops"',
  'path="dashboard-gerencial"',
  'path="clientes/:clienteId/timeline"',
  'path="veterinario/agenda"',
  'path="banho-tosa/taxi-dog"',
  'path="produtos/:id/movimentacoes"',
  'path="compras/pedidos"',
  'path="financeiro/conciliacao-bancaria"',
  'path="comissoes/fechamentos/detalhe"',
  'path="configuracoes/integracoes"',
  'path="entregas/financeiro"',
  'path="ia/whatsapp"',
]) {
  assert(
    routeSources.includes(routeLiteral),
    `Missing route literal after extraction: ${routeLiteral}`,
  );
}

console.log("App route refactor contract OK");
