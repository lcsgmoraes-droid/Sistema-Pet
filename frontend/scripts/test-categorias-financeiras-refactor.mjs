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
  "src/pages/CategoriasFinanceiras.jsx",
  "src/pages/categorias-financeiras/CategoriasFinanceirasPage.jsx",
  "src/pages/categorias-financeiras/useCategoriasFinanceirasController.js",
  "src/pages/categorias-financeiras/categoriasFinanceirasPersistence.js",
  "src/pages/categorias-financeiras/categoriasFinanceirasConstants.js",
  "src/pages/categorias-financeiras/categoriasFinanceirasUtils.js",
  "src/pages/categorias-financeiras/CategoriasFinanceirasHeader.jsx",
  "src/pages/categorias-financeiras/CategoriasFinanceirasFilters.jsx",
  "src/pages/categorias-financeiras/CategoriasFinanceirasList.jsx",
  "src/pages/categorias-financeiras/CategoriasFinanceirasRow.jsx",
  "src/pages/categorias-financeiras/CategoriasFinanceirasExpandedPanel.jsx",
  "src/pages/categorias-financeiras/CategoriaFinanceiraModal.jsx",
  "src/pages/categorias-financeiras/CategoriaFinanceiraFormFields.jsx",
  "src/pages/categorias-financeiras/CategoriaFinanceiraSubcategoriasFields.jsx",
  "src/pages/categorias-financeiras/SubcategoriaDREModal.jsx",
];

for (const relativePath of expectedFiles) {
  assert(
    fs.existsSync(path.join(root, relativePath)),
    `Missing categorias financeiras refactor file: ${relativePath}`,
  );
}

for (const relativePath of expectedFiles) {
  const lines = lineCount(relativePath);
  assert(lines <= 420, `${relativePath} has ${lines} lines; expected <= 420`);
}

const facadeSource = read("src/pages/CategoriasFinanceiras.jsx");
assert(
  facadeSource.includes("CategoriasFinanceirasPage"),
  "CategoriasFinanceiras.jsx should delegate to CategoriasFinanceirasPage",
);
assert(!facadeSource.includes("useState"), "CategoriasFinanceiras.jsx should not own React state");
assert(!facadeSource.includes("api."), "CategoriasFinanceiras.jsx should not own API calls");

const featureSource = expectedFiles
  .filter((relativePath) => relativePath.startsWith("src/pages/categorias-financeiras/"))
  .map(read)
  .join("\n");

for (const literal of [
  "/dre/categorias",
  "/categorias-financeiras",
  "/dre/subcategorias",
  "Categorias Financeiras",
  "Nova Categoria",
  "Subcategorias DRE",
  "ClassificaÃ§Ã£o de Custo",
  "Nova Subcategoria DRE",
  "Categoria DRE",
]) {
  assert(
    featureSource.includes(literal),
    `Missing categorias financeiras behavior literal after extraction: ${literal}`,
  );
}

const catalogRouteSource = read("src/app/routes/CatalogAdminRoutes.jsx");
const lazySource = read("src/app/lazyPages.jsx");
assert(
  catalogRouteSource.includes('path="cadastros/categorias-financeiras"'),
  "Categorias financeiras route should remain registered",
);
assert(
  lazySource.includes("pages/CategoriasFinanceiras"),
  "Lazy import should keep public CategoriasFinanceiras page path",
);

console.log("Categorias financeiras refactor contract OK");
