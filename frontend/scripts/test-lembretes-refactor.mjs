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
  "src/pages/Lembretes.jsx",
  "src/pages/lembretes/LembretesPage.jsx",
  "src/pages/lembretes/useLembretesController.js",
  "src/pages/lembretes/lembretesFormatters.js",
  "src/pages/lembretes/LembretesHeader.jsx",
  "src/pages/lembretes/LembretesCampanhasAlertas.jsx",
  "src/pages/lembretes/LembretesBlingAutocadastros.jsx",
  "src/pages/lembretes/LembretesDrePendentes.jsx",
  "src/pages/lembretes/LembretesValidadeSection.jsx",
  "src/pages/lembretes/LembretesList.jsx",
  "src/pages/lembretes/LembreteCard.jsx",
];

for (const relativePath of expectedFiles) {
  assert(fs.existsSync(path.join(root, relativePath)), `Missing lembretes file: ${relativePath}`);
}

for (const relativePath of expectedFiles) {
  const lines = lineCount(relativePath);
  assert(lines <= 420, `${relativePath} has ${lines} lines; expected <= 420`);
}

const facadeSource = read("src/pages/Lembretes.jsx");
assert(facadeSource.includes("LembretesPage"), "Lembretes.jsx should delegate to LembretesPage");
assert(!facadeSource.includes("useState"), "Lembretes.jsx should not own React state");
assert(!facadeSource.includes("api."), "Lembretes.jsx should not own API calls");

const featureSource = expectedFiles
  .filter((relativePath) => relativePath.startsWith("src/pages/lembretes/"))
  .map(read)
  .join("\n");

for (const literal of [
  "/lembretes/pendentes",
  "/campanhas/dashboard",
  "/dre/classificar/pendentes",
  "/integracoes/bling/nf/autocadastros-recentes",
  "/empresa/config-estoque",
  "/estoque/validade/processar",
  "/estoque/validade/pendencias",
  "/lembretes/${lembrete_id}/completar",
  "/lembretes/${lembrete_id}/renovar",
  "/estoque/validade/${item.id}/${endpoints[acao]}",
  "Lembretes de Recorr",
  "Alertas de Campanhas",
  "Auto cadastro Bling",
  "DRE",
  "Protecao por validade",
  "Produtos removidos por validade",
  "Verificar validade agora",
  "LembreteCard",
  "formatarDataValidade",
  "formatarMoeda",
]) {
  assert(featureSource.includes(literal), `Missing lembretes behavior literal: ${literal}`);
}

const routeSource = read("src/app/routes/ProductInventoryRoutes.jsx");
const lazySource = read("src/app/lazyPages.jsx");
assert(routeSource.includes('path="lembretes"'), "Lembretes route should remain registered");
assert(lazySource.includes("pages/Lembretes"), "Lazy import should keep public Lembretes path");

console.log("Lembretes refactor contract OK");
