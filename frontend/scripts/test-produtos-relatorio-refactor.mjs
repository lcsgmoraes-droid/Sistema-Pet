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
  "src/pages/ProdutosRelatorio.jsx",
  "src/pages/produtos-relatorio/ProdutosRelatorioPage.jsx",
  "src/pages/produtos-relatorio/useProdutosRelatorioController.js",
  "src/pages/produtos-relatorio/produtosRelatorioConstants.js",
  "src/pages/produtos-relatorio/produtosRelatorioData.js",
  "src/pages/produtos-relatorio/produtosRelatorioFormatters.js",
  "src/pages/produtos-relatorio/ProdutosRelatorioResumoCard.jsx",
  "src/pages/produtos-relatorio/ProdutosRelatorioJanelaVendaCard.jsx",
  "src/pages/produtos-relatorio/ProdutosRelatorioCurvaVendas30Dias.jsx",
  "src/pages/produtos-relatorio/ProdutosRelatorioHeader.jsx",
  "src/pages/produtos-relatorio/ProdutosRelatorioFiltros.jsx",
  "src/pages/produtos-relatorio/ProdutosRelatorioProdutoPanel.jsx",
  "src/pages/produtos-relatorio/ProdutosRelatorioHistoricoVendas.jsx",
  "src/pages/produtos-relatorio/ProdutosRelatorioMovimentacoesTable.jsx",
];

for (const relativePath of expectedFiles) {
  assert(
    fs.existsSync(path.join(root, relativePath)),
    `Missing produtos relatorio file: ${relativePath}`,
  );
}

for (const relativePath of expectedFiles) {
  const lines = lineCount(relativePath);
  assert(lines <= 420, `${relativePath} has ${lines} lines; expected <= 420`);
}

const facadeSource = read("src/pages/ProdutosRelatorio.jsx");
assert(
  facadeSource.includes("ProdutosRelatorioPage"),
  "ProdutosRelatorio.jsx should delegate to ProdutosRelatorioPage",
);
assert(!facadeSource.includes("useState"), "ProdutosRelatorio.jsx should not own React state");
assert(
  !facadeSource.includes("getRelatorioMovimentacoes"),
  "ProdutosRelatorio.jsx should not own report API calls",
);

const featureSource = expectedFiles
  .filter((relativePath) => relativePath.startsWith("src/pages/produtos-relatorio/"))
  .map(read)
  .join("\n");

for (const literal of [
  "getRelatorioMovimentacoes",
  "getRelatorioProdutoVendas",
  "getProdutos",
  "movimentacoes_produtos_${hojeIso()}.csv",
  "Giro de Produto e Movimentacoes",
  "Ritmo de vendas nos ultimos 30 dias",
  "Historico recente de vendas do produto",
  "Movimentacoes filtradas",
  "Exportar CSV",
  "/produtos/${produtoSelecionado.id}/editar",
  "/produtos",
]) {
  assert(
    featureSource.includes(literal),
    `Missing produtos relatorio behavior literal: ${literal}`,
  );
}

const routeSource = read("src/app/routes/ProductInventoryRoutes.jsx");
const lazySource = read("src/app/lazyPages.jsx");
assert(
  routeSource.includes('path="produtos/relatorio"'),
  "Produtos relatorio route should remain registered",
);
assert(
  lazySource.includes("pages/ProdutosRelatorio"),
  "Lazy import should keep public ProdutosRelatorio path",
);

console.log("Produtos relatorio refactor contract OK");
