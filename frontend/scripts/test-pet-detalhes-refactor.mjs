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
  "src/pages/PetDetalhes.jsx",
  "src/pages/pet-detalhes/PetDetalhesPage.jsx",
  "src/pages/pet-detalhes/usePetDetalhesController.js",
  "src/pages/pet-detalhes/petDetalhesConstants.js",
  "src/pages/pet-detalhes/petDetalhesUtils.js",
  "src/pages/pet-detalhes/PetDetalhesLoadingState.jsx",
  "src/pages/pet-detalhes/PetDetalhesErrorState.jsx",
  "src/pages/pet-detalhes/PetDetalhesHeader.jsx",
  "src/pages/pet-detalhes/PetDetalhesTabs.jsx",
  "src/pages/pet-detalhes/PetDetalhesInfoField.jsx",
  "src/pages/pet-detalhes/PetDetalhesGeralTab.jsx",
  "src/pages/pet-detalhes/PetDetalhesSaudeTab.jsx",
  "src/pages/pet-detalhes/PetDetalhesExamesPanel.jsx",
  "src/pages/pet-detalhes/PetDetalhesNovoExameForm.jsx",
  "src/pages/pet-detalhes/PetDetalhesVacinasTab.jsx",
  "src/pages/pet-detalhes/PetDetalhesConsultasTab.jsx",
  "src/pages/pet-detalhes/PetDetalhesInternacoesTab.jsx",
  "src/pages/pet-detalhes/PetDetalhesServicosTab.jsx",
];

for (const relativePath of expectedFiles) {
  assert(
    fs.existsSync(path.join(root, relativePath)),
    `Missing pet detalhes refactor file: ${relativePath}`,
  );
}

for (const relativePath of expectedFiles) {
  const lines = lineCount(relativePath);
  assert(lines <= 420, `${relativePath} has ${lines} lines; expected <= 420`);
}

const facadeSource = read("src/pages/PetDetalhes.jsx");
assert(
  facadeSource.includes("PetDetalhesPage"),
  "PetDetalhes.jsx should delegate to PetDetalhesPage",
);
assert(!facadeSource.includes("useState"), "PetDetalhes.jsx should not own React state");
assert(!facadeSource.includes("api."), "PetDetalhes.jsx should not own API calls");
assert(!facadeSource.includes("vetApi."), "PetDetalhes.jsx should not own vet API calls");

const featureSource = expectedFiles
  .filter((relativePath) => relativePath.startsWith("src/pages/pet-detalhes/"))
  .map(read)
  .join("\n");

for (const literal of [
  "/pets/${petId}",
  "/pets/${pet.id}?soft_delete=true",
  "historicoInternacoesPet",
  "listarVacinasPet",
  "listarConsultas",
  "listarExamesPet",
  "obterCarteirinhaPet",
  "criarExame",
  "uploadArquivoExame",
  "interpretarExameIA",
  "Dados Gerais",
  "InformaÃ§Ãµes Gerais",
  "InformaÃ§Ãµes de SaÃºde",
  "Carteira de VacinaÃ§Ã£o",
  "HistÃ³rico de Consultas",
  "HistÃ³rico de InternaÃ§Ãµes",
  "HistÃ³rico de ServiÃ§os",
  "Novo exame",
  "Salvar exame",
  "Interpretar com IA",
]) {
  assert(
    featureSource.includes(literal),
    `Missing pet detalhes behavior literal after extraction: ${literal}`,
  );
}

const routeSource = read("src/app/routes/CoreProtectedRoutes.jsx");
const lazySource = read("src/app/lazyPages.jsx");
assert(routeSource.includes('path="pets/:petId"'), "Pet detalhes route should remain registered");
assert(
  lazySource.includes("pages/PetDetalhes"),
  "Lazy import should keep public PetDetalhes page path",
);

console.log("Pet detalhes refactor contract OK");
