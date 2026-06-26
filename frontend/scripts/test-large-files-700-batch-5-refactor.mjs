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
  "src/pages/PetForm.jsx",
  "src/pages/ecommerce/EcommerceConfig.jsx",
  "src/pages/OpsIncidentes.jsx",
  "src/components/ContasPagar.jsx",
  "src/components/compras/PedidosCompraSugestaoModal.jsx",
  "src/pages/configuracoes/ConfiguracaoFiscalEmpresa.jsx",
];

const extractedFiles = [
  "src/pages/petForm/PetFormView.jsx",
  "src/pages/ecommerce/EcommerceConfigView.jsx",
  "src/pages/opsIncidentes/OpsIncidentesCards.jsx",
  "src/pages/opsIncidentes/OpsIncidentesView.jsx",
  "src/components/contas-pagar/ContasPagarView.jsx",
  "src/components/compras/PedidosCompraSugestaoHeader.jsx",
  "src/components/compras/PedidosCompraSugestaoTable.jsx",
  "src/pages/configuracoes/ConfiguracaoFiscalEmpresaView.jsx",
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
    "src/pages/PetForm.jsx",
    "./petForm/PetFormView",
    "PetForm.jsx should delegate form markup to PetFormView",
  ],
  [
    "src/pages/ecommerce/EcommerceConfig.jsx",
    "./EcommerceConfigView",
    "EcommerceConfig.jsx should delegate store/payment markup to EcommerceConfigView",
  ],
  [
    "src/pages/OpsIncidentes.jsx",
    "./opsIncidentes/OpsIncidentesView",
    "OpsIncidentes.jsx should delegate page layout to OpsIncidentesView",
  ],
  [
    "src/pages/OpsIncidentes.jsx",
    "./opsIncidentes/OpsIncidentesCards",
    "OpsIncidentes.jsx should delegate card/detail components to OpsIncidentesCards",
  ],
  [
    "src/components/ContasPagar.jsx",
    "./contas-pagar/ContasPagarView",
    "ContasPagar.jsx should delegate page layout to ContasPagarView",
  ],
  [
    "src/components/compras/PedidosCompraSugestaoModal.jsx",
    "./PedidosCompraSugestaoHeader",
    "PedidosCompraSugestaoModal.jsx should delegate header/filter markup",
  ],
  [
    "src/components/compras/PedidosCompraSugestaoModal.jsx",
    "./PedidosCompraSugestaoTable",
    "PedidosCompraSugestaoModal.jsx should delegate suggestion table markup",
  ],
  [
    "src/pages/configuracoes/ConfiguracaoFiscalEmpresa.jsx",
    "./ConfiguracaoFiscalEmpresaView",
    "ConfiguracaoFiscalEmpresa.jsx should delegate fiscal form markup to ConfiguracaoFiscalEmpresaView",
  ],
];

for (const [sourcePath, importPath, message] of imports) {
  assert(read(sourcePath).includes(importPath), message);
}

console.log("Large files 700 batch 5 refactor contract OK");
