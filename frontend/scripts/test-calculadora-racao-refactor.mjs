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
  "src/pages/CalculadoraRacao.jsx",
  "src/pages/calculadora-racao/CalculadoraRacaoPage.jsx",
  "src/pages/calculadora-racao/useCalculadoraRacaoController.js",
  "src/pages/calculadora-racao/useRacaoSearchEffect.js",
  "src/pages/calculadora-racao/calculadoraRacaoApi.js",
  "src/pages/calculadora-racao/calculadoraRacaoState.js",
  "src/pages/calculadora-racao/RacaoSearchInput.jsx",
  "src/pages/calculadora-racao/CalculadoraRacaoHeader.jsx",
  "src/pages/calculadora-racao/CalculadoraRacaoForm.jsx",
  "src/pages/calculadora-racao/CalculadoraRacaoPetFields.jsx",
  "src/pages/calculadora-racao/CalculadoraRacaoProdutoFields.jsx",
  "src/pages/calculadora-racao/CalculadoraRacaoComparativoFields.jsx",
  "src/pages/calculadora-racao/CalculadoraRacaoResultadoCard.jsx",
  "src/pages/calculadora-racao/CalculadoraRacaoComparativoCard.jsx",
];

for (const relativePath of expectedFiles) {
  assert(
    fs.existsSync(path.join(root, relativePath)),
    `Missing calculadora racao file: ${relativePath}`,
  );
}

for (const relativePath of expectedFiles) {
  const lines = lineCount(relativePath);
  assert(lines <= 420, `${relativePath} has ${lines} lines; expected <= 420`);
}

const facadeSource = read("src/pages/CalculadoraRacao.jsx");
assert(
  facadeSource.includes("CalculadoraRacaoPage"),
  "CalculadoraRacao.jsx should delegate to CalculadoraRacaoPage",
);
assert(!facadeSource.includes("useState"), "CalculadoraRacao.jsx should not own React state");
assert(!facadeSource.includes("api."), "CalculadoraRacao.jsx should not own API calls");

const featureSource = expectedFiles
  .filter((relativePath) => relativePath.startsWith("src/pages/calculadora-racao/"))
  .map(read)
  .join("\n");

for (const literal of [
  "/produtos/calculadora-racao/opcoes",
  "/clientes/pets/todos",
  "/produtos/calculadora-racao",
  "/produtos/comparar-racoes",
  "Calculadora de",
  "Dados do Pet",
  "Selecionar",
  "Comparar",
  "Resultado do",
  "Comparativo de",
  "racao-produto-principal",
  "racao-produto-comparar",
  "racao-filtro-classificacao",
  "camposIncompletosTexto",
  "formatarRacaoLabel",
]) {
  assert(featureSource.includes(literal), `Missing calculadora racao behavior literal: ${literal}`);
}

const routeSource = read("src/app/routes/ProductInventoryRoutes.jsx");
const lazySource = read("src/app/lazyPages.jsx");
assert(
  routeSource.includes('path="calculadora-racao"'),
  "Calculadora racao route should remain registered",
);
assert(lazySource.includes("pages/CalculadoraRacao"), "Lazy import should keep public path");

console.log("Calculadora racao refactor contract OK");
