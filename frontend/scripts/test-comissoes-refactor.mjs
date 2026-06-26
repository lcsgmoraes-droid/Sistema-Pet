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
  "src/pages/Comissoes.jsx",
  "src/pages/comissoes/ComissoesPage.jsx",
  "src/pages/comissoes/useComissoesPageController.js",
  "src/pages/comissoes/useComissaoModalController.js",
  "src/pages/comissoes/comissoesConstants.js",
  "src/pages/comissoes/comissoesUtils.js",
  "src/pages/comissoes/ComissoesPageHeader.jsx",
  "src/pages/comissoes/ComissoesList.jsx",
  "src/pages/comissoes/ComissaoConfiguracaoModal.jsx",
  "src/pages/comissoes/ComissaoParceiroFields.jsx",
  "src/pages/comissoes/ComissaoRulesPanel.jsx",
  "src/pages/comissoes/ComissaoProductTree.jsx",
  "src/pages/comissoes/ComissaoConfiguredItems.jsx",
  "src/pages/comissoes/ComissaoSelectedItemPanel.jsx",
  "src/pages/comissoes/ComissaoPendingConfigurations.jsx",
  "src/pages/comissoes/ComissaoModalFooter.jsx",
];

for (const relativePath of expectedFiles) {
  assert(
    fs.existsSync(path.join(root, relativePath)),
    `Missing comissoes refactor file: ${relativePath}`,
  );
}

for (const relativePath of expectedFiles) {
  const lines = lineCount(relativePath);
  assert(lines <= 420, `${relativePath} has ${lines} lines; expected <= 420`);
}

const facadeSource = read("src/pages/Comissoes.jsx");
assert(facadeSource.includes("ComissoesPage"), "Comissoes.jsx should delegate to ComissoesPage");
assert(!facadeSource.includes("useState"), "Comissoes.jsx should not own React state");
assert(!facadeSource.includes("api."), "Comissoes.jsx should not own API calls");

const featureSource = expectedFiles
  .filter((relativePath) => relativePath.startsWith("src/pages/comissoes/"))
  .map(read)
  .join("\n");

for (const literal of [
  "/comissoes/configuracoes/funcionarios",
  "/comissoes/arvore-produtos",
  "/comissoes/configuracoes/funcionario/",
  "/comissoes/configuracoes/duplicar",
  "/comissoes/funcionarios",
  "/comissoes/configuracoes/batch",
  "/comissoes/configuracoes",
  "Cadastro de Comissões",
  "Configuração de Comissão",
  "Regras de Cálculo",
  "Seleção de Produtos",
  "Configurações a Salvar",
]) {
  assert(
    featureSource.includes(literal),
    `Missing comissoes behavior literal after extraction: ${literal}`,
  );
}

const commissionRouteSource = read("src/app/routes/CommissionRoutes.jsx");
const lazySource = read("src/app/lazyPages.jsx");
assert(
  commissionRouteSource.includes('path="comissoes"'),
  "Comissoes route should remain registered",
);
assert(
  lazySource.includes("pages/Comissoes"),
  "Lazy import should keep public Comissoes page path",
);

console.log("Comissoes refactor contract OK");
