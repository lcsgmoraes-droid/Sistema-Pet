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
  "src/pages/conciliacaoRecebimentos/Aba2ConciliacaoRecebimentosView.jsx",
  "src/pages/Aba1ConciliacaoVendasV2.jsx",
  "src/components/ContasReceber.jsx",
  "src/components/ModalDevolucao.jsx",
];

const extractedFiles = [
  "src/pages/conciliacaoRecebimentos/Aba2RecebimentosSections.jsx",
  "src/pages/conciliacaoRecebimentos/Aba2RecebimentosResult.jsx",
  "src/pages/conciliacao/Aba1ConciliacaoCards.jsx",
  "src/components/contasReceber/ContasReceberPanels.jsx",
  "src/components/devolucao/ModalDevolucaoSections.jsx",
];

for (const relativePath of extractedFiles) {
  assert(exists(relativePath), `Missing extracted 700-batch-2 refactor module: ${relativePath}`);
}

for (const relativePath of targetFiles) {
  const lines = lineCount(relativePath);
  assert(lines <= 700, `${relativePath} has ${lines} lines; expected <= 700`);
}

for (const relativePath of extractedFiles) {
  const lines = lineCount(relativePath);
  assert(lines <= 700, `${relativePath} has ${lines} lines; expected <= 700`);
}

const aba2 = read("src/pages/conciliacaoRecebimentos/Aba2ConciliacaoRecebimentosView.jsx");
assert(
  aba2.includes("./Aba2RecebimentosSections"),
  "Aba2ConciliacaoRecebimentosView.jsx should delegate confirmation and divergence modal sections",
);
assert(
  aba2.includes("./Aba2RecebimentosResult"),
  "Aba2ConciliacaoRecebimentosView.jsx should delegate validation result rendering",
);

const aba1 = read("src/pages/Aba1ConciliacaoVendasV2.jsx");
assert(
  aba1.includes("./conciliacao/Aba1ConciliacaoCards"),
  "Aba1ConciliacaoVendasV2.jsx should delegate card and match-pair rendering",
);

const contasReceber = read("src/components/ContasReceber.jsx");
assert(
  contasReceber.includes("./contasReceber/ContasReceberPanels"),
  "ContasReceber.jsx should delegate filters and modal panels",
);

const modalDevolucao = read("src/components/ModalDevolucao.jsx");
assert(
  modalDevolucao.includes("./devolucao/ModalDevolucaoSections"),
  "ModalDevolucao.jsx should delegate sale and item selection sections",
);

console.log("Large files 700 batch 2 refactor contract OK");
