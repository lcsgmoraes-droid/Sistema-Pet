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
  "src/components/ModalNovaContaPagar.jsx",
  "src/components/modalNovaContaPagar/ModalNovaContaPagar.jsx",
  "src/components/modalNovaContaPagar/useModalNovaContaPagarController.js",
  "src/components/modalNovaContaPagar/contaPagarFormState.js",
  "src/components/modalNovaContaPagar/ModalNovaContaPagarDialog.jsx",
  "src/components/modalNovaContaPagar/ContaPagarBasicFields.jsx",
  "src/components/modalNovaContaPagar/ContaPagarRecorrenciaSection.jsx",
  "src/components/modalNovaContaPagar/ContaPagarParcelamentoSection.jsx",
  "src/components/modalNovaContaPagar/CategoriaFinanceiraModal.jsx",
  "src/components/modalNovaContaPagar/CategoriaSubcategoriasFields.jsx",
];

for (const relativePath of expectedFiles) {
  assert(
    fs.existsSync(path.join(root, relativePath)),
    `Missing modal nova conta pagar file: ${relativePath}`,
  );
}

for (const relativePath of expectedFiles) {
  const lines = lineCount(relativePath);
  assert(lines <= 420, `${relativePath} has ${lines} lines; expected <= 420`);
}

const facadeSource = read("src/components/ModalNovaContaPagar.jsx");
assert(
  facadeSource.includes("modalNovaContaPagar/ModalNovaContaPagar"),
  "ModalNovaContaPagar.jsx should delegate to the extracted modal module",
);
assert(!facadeSource.includes("useState"), "ModalNovaContaPagar.jsx should not own React state");
assert(!facadeSource.includes("api."), "ModalNovaContaPagar.jsx should not own API calls");

const featureSource = expectedFiles
  .filter((relativePath) => relativePath.startsWith("src/components/modalNovaContaPagar/"))
  .map(read)
  .join("\n");

for (const literal of [
  "/clientes/?tipo_cadastro=fornecedor",
  "/categorias-financeiras",
  "/dre/subcategorias",
  "/cadastros/tipo-despesa/",
  "/contas-pagar/${contaEdicao.id}",
  "/contas-pagar/",
  "criarDadosPadraoContaPagar",
  "montarDadosEdicaoContaPagar",
  "normalizarDataOpcionalRecorrencia",
  "gerarPreviewParcelas",
  "FornecedorSelector",
  "Nova Conta a Pagar",
  "Editar Conta a Pagar",
  "Despesa Recorrente",
  "Parcelar esta conta",
  "Nova Categoria Financeira",
  "aplicar_recorrencia_futura",
]) {
  assert(featureSource.includes(literal), `Missing modal conta pagar behavior literal: ${literal}`);
}

const contasPagarSource = read("src/components/ContasPagar.jsx");
assert(
  contasPagarSource.includes('from "./ModalNovaContaPagar"'),
  "ContasPagar should keep importing the public modal path",
);

console.log("Modal nova conta pagar refactor contract OK");
