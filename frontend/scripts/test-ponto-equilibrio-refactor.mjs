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
  "src/pages/PontoEquilibrio.jsx",
  "src/pages/ponto-equilibrio/PontoEquilibrioPage.jsx",
  "src/pages/ponto-equilibrio/usePontoEquilibrioController.js",
  "src/pages/ponto-equilibrio/pontoEquilibrioConstants.js",
  "src/pages/ponto-equilibrio/pontoEquilibrioUtils.js",
  "src/pages/ponto-equilibrio/PontoEquilibrioMetricCard.jsx",
  "src/pages/ponto-equilibrio/PontoEquilibrioHeaderFilters.jsx",
  "src/pages/ponto-equilibrio/PontoEquilibrioStatusSummary.jsx",
  "src/pages/ponto-equilibrio/PontoEquilibrioResumoTab.jsx",
  "src/pages/ponto-equilibrio/DetalhamentoMargemPanel.jsx",
  "src/pages/ponto-equilibrio/DetalhesPontoEquilibrioDrawer.jsx",
  "src/pages/ponto-equilibrio/SimuladorImpactoPanel.jsx",
  "src/pages/ponto-equilibrio/AnaliseCustosPanel.jsx",
  "src/pages/ponto-equilibrio/PontoEquilibrioTooltips.jsx",
];

for (const relativePath of expectedFiles) {
  assert(
    fs.existsSync(path.join(root, relativePath)),
    `Missing ponto equilibrio refactor file: ${relativePath}`,
  );
}

for (const relativePath of expectedFiles) {
  const lines = lineCount(relativePath);
  assert(lines <= 420, `${relativePath} has ${lines} lines; expected <= 420`);
}

const facadeSource = read("src/pages/PontoEquilibrio.jsx");
assert(
  facadeSource.includes("PontoEquilibrioPage"),
  "PontoEquilibrio.jsx should delegate to PontoEquilibrioPage",
);
assert(!facadeSource.includes("useState"), "PontoEquilibrio.jsx should not own React state");
assert(!facadeSource.includes("api."), "PontoEquilibrio.jsx should not own API calls");

const featureSource = expectedFiles
  .filter((relativePath) => relativePath.startsWith("src/pages/ponto-equilibrio/"))
  .map(read)
  .join("\n");

for (const literal of [
  "/financeiro/ponto-equilibrio",
  "/financeiro/ponto-equilibrio/detalhes",
  "Ponto de Equilibrio",
  "Formula usada",
  "Detalhamento da margem",
  "Calculadora de impacto",
  "Analise dos custos",
  "Abas do ponto de equilibrio",
]) {
  assert(
    featureSource.includes(literal),
    `Missing ponto equilibrio behavior literal after extraction: ${literal}`,
  );
}

const appRouteSource = read("src/app/routes/FinanceRoutes.jsx");
const lazySource = read("src/app/lazyPages.jsx");
assert(
  appRouteSource.includes('path="financeiro/ponto-equilibrio"'),
  "Ponto equilibrio route should remain registered",
);
assert(
  lazySource.includes("pages/PontoEquilibrio"),
  "Lazy import should keep public PontoEquilibrio page path",
);

console.log("Ponto equilibrio refactor contract OK");
