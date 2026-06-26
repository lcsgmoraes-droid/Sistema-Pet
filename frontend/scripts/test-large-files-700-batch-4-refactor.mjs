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
  "src/pages/ConciliacaoBancaria.jsx",
  "src/components/DRE.jsx",
  "src/components/ModalNovaContaReceber.jsx",
  "src/components/FormasPagamento.jsx",
];

const extractedFiles = [
  "src/pages/conciliacaoBancaria/ConciliacaoBancariaModals.jsx",
  "src/components/dre/DREView.jsx",
  "src/components/contasReceber/ModalNovaContaReceberContent.jsx",
  "src/components/formasPagamento/FormasPagamentoView.jsx",
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
    "src/pages/ConciliacaoBancaria.jsx",
    "./conciliacaoBancaria/ConciliacaoBancariaModals",
    "ConciliacaoBancaria.jsx should delegate modal markup to ConciliacaoBancariaModals",
  ],
  [
    "src/components/DRE.jsx",
    "./dre/DREView",
    "DRE.jsx should delegate visual composition to DREView",
  ],
  [
    "src/components/ModalNovaContaReceber.jsx",
    "./contasReceber/ModalNovaContaReceberContent",
    "ModalNovaContaReceber.jsx should delegate form markup to ModalNovaContaReceberContent",
  ],
  [
    "src/components/FormasPagamento.jsx",
    "./formasPagamento/FormasPagamentoView",
    "FormasPagamento.jsx should delegate visual composition to FormasPagamentoView",
  ],
];

for (const [sourcePath, importPath, message] of imports) {
  assert(read(sourcePath).includes(importPath), message);
}

console.log("Large files 700 batch 4 refactor contract OK");
