import fs from "node:fs";
import path from "node:path";
import process from "node:process";

const root = process.cwd();

function read(relativePath) {
  return fs.readFileSync(path.join(root, relativePath), "utf8");
}

function exists(relativePath) {
  return fs.existsSync(path.join(root, relativePath));
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function lineCount(relativePath) {
  return read(relativePath).split(/\r?\n/).length;
}

const targetFiles = [
  "src/components/EstoqueBling.jsx",
  "src/components/VendasFinanceiro.jsx",
  "src/components/MovimentacoesProduto.jsx",
];

const extractedFiles = [
  "src/components/estoqueBling/useEstoqueBlingActions.js",
  "src/components/financeiro/vendasFinanceiro/useVendasFinanceiroActions.js",
  "src/components/estoque/useMovimentacoesProdutoGranel.js",
];

for (const relativePath of targetFiles) {
  assert(exists(relativePath), `Missing target file: ${relativePath}`);
  const lines = lineCount(relativePath);
  assert(lines <= 700, `${relativePath} has ${lines} lines; expected <= 700`);
}

for (const relativePath of extractedFiles) {
  assert(exists(relativePath), `Missing extracted frontend refactor file: ${relativePath}`);
  const lines = lineCount(relativePath);
  assert(lines <= 700, `${relativePath} has ${lines} lines; expected <= 700`);
}

const imports = [
  [
    "src/components/EstoqueBling.jsx",
    "./estoqueBling/useEstoqueBlingActions",
    "EstoqueBling.jsx should delegate Bling action handlers to useEstoqueBlingActions",
  ],
  [
    "src/components/VendasFinanceiro.jsx",
    "./financeiro/vendasFinanceiro/useVendasFinanceiroActions",
    "VendasFinanceiro.jsx should delegate export and reprocessing actions",
  ],
  [
    "src/components/MovimentacoesProduto.jsx",
    "./estoque/useMovimentacoesProdutoGranel",
    "MovimentacoesProduto.jsx should delegate granel workflow state/actions",
  ],
];

for (const [sourcePath, importPath, message] of imports) {
  assert(read(sourcePath).includes(importPath), message);
}

console.log("Large files 700 batch 6 refactor contract OK");
