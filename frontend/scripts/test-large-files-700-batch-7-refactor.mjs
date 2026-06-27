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
  "src/components/modalPagamento/useModalPagamentoController.js",
  "src/components/produtos/produtosColumns.jsx",
  "src/pages/ClienteFinanceiro.jsx",
  "src/pages/ecommerce/EcommerceMVP.jsx",
];

const extractedFiles = [
  "src/components/modalPagamento/useModalPagamentoActions.js",
  "src/components/produtos/produtosPricingColumns.jsx",
  "src/pages/clienteFinanceiro/ClienteFinanceiroView.jsx",
  "src/pages/ecommerce/useEcommercePaymentReturn.js",
  "src/pages/ecommerce/useEcommerceStorefrontRuntime.js",
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
    "src/components/modalPagamento/useModalPagamentoController.js",
    "./useModalPagamentoActions",
    "useModalPagamentoController.js should delegate payment actions",
  ],
  [
    "src/components/produtos/produtosColumns.jsx",
    "./produtosPricingColumns",
    "produtosColumns.jsx should delegate pricing/margin columns",
  ],
  [
    "src/pages/ClienteFinanceiro.jsx",
    "./clienteFinanceiro/ClienteFinanceiroView",
    "ClienteFinanceiro.jsx should delegate page markup to ClienteFinanceiroView",
  ],
  [
    "src/pages/ecommerce/EcommerceMVP.jsx",
    "./useEcommercePaymentReturn",
    "EcommerceMVP.jsx should delegate payment return flow",
  ],
  [
    "src/pages/ecommerce/EcommerceMVP.jsx",
    "./useEcommerceStorefrontRuntime",
    "EcommerceMVP.jsx should delegate storefront runtime setup",
  ],
];

for (const [sourcePath, importPath, message] of imports) {
  assert(read(sourcePath).includes(importPath), message);
}

console.log("Large files 700 batch 7 refactor contract OK");
