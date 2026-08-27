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
  "src/components/modalNovaContaPagar/VincularCategoriaDREModal.jsx",
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
  "Classificar categoria no DRE",
  "handleCategoriaChange",
  "handleSubmitVinculoDRE",
  "Categoria vinculada ao DRE!",
  "aplicar_recorrencia_futura",
]) {
  assert(featureSource.includes(literal), `Missing modal conta pagar behavior literal: ${literal}`);
}

const basicFieldsSource = read("src/components/modalNovaContaPagar/ContaPagarBasicFields.jsx");
assert(
  basicFieldsSource.includes('className="flex min-w-0 gap-2"'),
  "Category row should allow the select to shrink inside the modal",
);
assert(
  basicFieldsSource.includes('className="shrink-0 px-3 py-2'),
  "Add category button should remain fully visible inside the modal",
);

const helpSource = read("src/pages/centralAjuda/centralAjudaKnowledge.js");
for (const literal of [
  'slug: "vincular-categoria-dre-conta-pagar"',
  "Como vincular uma categoria ao DRE ao criar uma conta a pagar",
  "Esta categoria ainda não está vinculada ao DRE",
  "Classificar agora",
  "Salvar vínculo",
  "Teste seguro",
  "Checklist final",
]) {
  assert(helpSource.includes(literal), `Missing DRE help article literal: ${literal}`);
}

const contasPagarViewSource = read("src/components/contas-pagar/ContasPagarView.jsx");
assert(
  contasPagarViewSource.includes('from "../ModalNovaContaPagar"'),
  "ContasPagarView should keep importing the public modal path",
);

console.log("Modal nova conta pagar refactor contract OK");
