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
  "src/pages/ProdutosValidadeProxima.jsx",
  "src/pages/produtos-validade-proxima/ProdutosValidadeProximaPage.jsx",
  "src/pages/produtos-validade-proxima/useProdutosValidadeProximaController.js",
  "src/pages/produtos-validade-proxima/produtosValidadeProximaConstants.js",
  "src/pages/produtos-validade-proxima/produtosValidadeProximaFormatters.js",
  "src/pages/produtos-validade-proxima/produtosValidadeProximaCsv.js",
  "src/pages/produtos-validade-proxima/ProdutosValidadeHeader.jsx",
  "src/pages/produtos-validade-proxima/ProdutosValidadeRuleBanner.jsx",
  "src/pages/produtos-validade-proxima/ProdutosValidadeFiltros.jsx",
  "src/pages/produtos-validade-proxima/ProdutosValidadeResumoGrid.jsx",
  "src/pages/produtos-validade-proxima/ProdutosValidadeLotesPanel.jsx",
  "src/pages/produtos-validade-proxima/ProdutosValidadeMobileList.jsx",
  "src/pages/produtos-validade-proxima/ProdutosValidadeTable.jsx",
  "src/pages/produtos-validade-proxima/ProdutosValidadePagination.jsx",
];

for (const relativePath of expectedFiles) {
  assert(
    fs.existsSync(path.join(root, relativePath)),
    `Missing produtos validade proxima file: ${relativePath}`,
  );
}

for (const relativePath of expectedFiles) {
  const lines = lineCount(relativePath);
  assert(lines <= 420, `${relativePath} has ${lines} lines; expected <= 420`);
}

const facadeSource = read("src/pages/ProdutosValidadeProxima.jsx");
assert(
  facadeSource.includes("ProdutosValidadeProximaPage"),
  "ProdutosValidadeProxima.jsx should delegate to ProdutosValidadeProximaPage",
);
assert(
  !facadeSource.includes("useState"),
  "ProdutosValidadeProxima.jsx should not own React state",
);
assert(
  !facadeSource.includes("getRelatorioValidadeProxima"),
  "ProdutosValidadeProxima.jsx should not own report API calls",
);

const featureSource = expectedFiles
  .filter((relativePath) => relativePath.startsWith("src/pages/produtos-validade-proxima/"))
  .map(read)
  .join("\n");

for (const literal of [
  "getRelatorioValidadeProxima",
  "criarExclusaoCampanhaValidade",
  "removerExclusaoCampanhaValidade",
  "FornecedorSelector",
  "CategoriaProdutoSelector",
  "MarcaProdutoSelector",
  "validade_proxima_${dataArquivo}.csv",
  "Produtos com validade proxima",
  "Regra automatica por validade",
  "Lotes ordenados por vencimento",
  "Exportar CSV",
  "Tirar da campanha",
  "Reincluir",
  "/campanhas?aba=validade",
  "/produtos/${item.produto_id}/editar",
  "status_validade",
  "apenas_com_estoque",
  "formatarQuantidade",
]) {
  assert(
    featureSource.includes(literal),
    `Missing produtos validade proxima behavior literal: ${literal}`,
  );
}

const routeSource = read("src/app/routes/ProductInventoryRoutes.jsx");
const alertasSource = read("src/pages/AlertasEstoque.jsx");
const campanhasSource = read("src/components/campanhas/CampanhasValidadeTab.jsx");

assert(
  routeSource.includes('path="produtos/validade-proxima"'),
  "Produtos validade route redirect should remain registered",
);
assert(
  alertasSource.includes('from "./ProdutosValidadeProxima"'),
  "Alertas estoque should keep importing public ProdutosValidadeProxima path",
);
assert(
  campanhasSource.includes('from "../../pages/ProdutosValidadeProxima"'),
  "Campanhas validade should keep importing public ProdutosValidadeProxima path",
);

console.log("Produtos validade proxima refactor contract OK");
