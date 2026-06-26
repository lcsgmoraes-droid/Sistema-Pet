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
  "src/pages/comissoes/RelatoriosComissoes.jsx",
  "src/components/ModuloBloqueado.jsx",
  "src/components/caixa/ModalFecharCaixaContent.jsx",
  "src/components/SugestoesInteligentesRacoes.jsx",
];

const extractedFiles = [
  "src/pages/comissoes/relatorios/RelatoriosComissoesSections.jsx",
  "src/components/moduloBloqueado/ModuloBloqueadoPreviews.jsx",
  "src/components/caixa/ModalFecharCaixaPanels.jsx",
  "src/components/racoes/SugestoesInteligentesRacoesPanels.jsx",
];

for (const relativePath of extractedFiles) {
  assert(exists(relativePath), `Missing extracted 700-batch-3 refactor module: ${relativePath}`);
}

for (const relativePath of targetFiles) {
  const lines = lineCount(relativePath);
  assert(lines <= 700, `${relativePath} has ${lines} lines; expected <= 700`);
}

for (const relativePath of extractedFiles) {
  const lines = lineCount(relativePath);
  assert(lines <= 700, `${relativePath} has ${lines} lines; expected <= 700`);
}

const relatorios = read("src/pages/comissoes/RelatoriosComissoes.jsx");
assert(
  relatorios.includes("./relatorios/RelatoriosComissoesSections"),
  "RelatoriosComissoes.jsx should delegate report sections",
);

const moduloBloqueado = read("src/components/ModuloBloqueado.jsx");
assert(
  moduloBloqueado.includes("./moduloBloqueado/ModuloBloqueadoPreviews"),
  "ModuloBloqueado.jsx should delegate premium preview panels",
);

const modalFecharCaixa = read("src/components/caixa/ModalFecharCaixaContent.jsx");
assert(
  modalFecharCaixa.includes("./ModalFecharCaixaPanels"),
  "ModalFecharCaixaContent.jsx should delegate count and sales panels",
);

const sugestoes = read("src/components/SugestoesInteligentesRacoes.jsx");
assert(
  sugestoes.includes("./racoes/SugestoesInteligentesRacoesPanels"),
  "SugestoesInteligentesRacoes.jsx should delegate suggestion tabs",
);

console.log("Large files 700 batch 3 refactor contract OK");
