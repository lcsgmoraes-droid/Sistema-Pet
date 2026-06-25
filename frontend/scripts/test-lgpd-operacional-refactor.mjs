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
  "src/pages/LGPDOperacional.jsx",
  "src/pages/lgpd/LGPDOperacionalPage.jsx",
  "src/pages/lgpd/useLGPDOperacionalController.js",
  "src/pages/lgpd/lgpdConstants.js",
  "src/pages/lgpd/lgpdUtils.js",
  "src/pages/lgpd/LGPDRequestCard.jsx",
  "src/pages/lgpd/LGPDTitularPanel.jsx",
  "src/pages/lgpd/LGPDSolicitacoesPanel.jsx",
  "src/pages/lgpd/LGPDRequestModal.jsx",
  "src/pages/lgpd/LGPDNewRequestModal.jsx",
  "src/pages/lgpd/LGPDPrivacyModal.jsx",
  "src/pages/lgpd/LGPDAnonymizeDialog.jsx",
];

for (const relativePath of expectedFiles) {
  assert(
    fs.existsSync(path.join(root, relativePath)),
    `Missing LGPD refactor file: ${relativePath}`,
  );
}

for (const relativePath of expectedFiles) {
  const lines = lineCount(relativePath);
  assert(lines <= 420, `${relativePath} has ${lines} lines; expected <= 420`);
}

const facadeSource = read("src/pages/LGPDOperacional.jsx");
assert(
  facadeSource.includes("LGPDOperacionalPage"),
  "LGPDOperacional.jsx should delegate to LGPDOperacionalPage",
);
assert(!facadeSource.includes("useState"), "LGPDOperacional.jsx should not own React state");
assert(!facadeSource.includes("api."), "LGPDOperacional.jsx should not own API calls");

const featureSource = expectedFiles
  .filter((relativePath) => relativePath.startsWith("src/pages/lgpd/"))
  .map(read)
  .join("\n");

for (const literal of [
  "/lgpd/status",
  "/lgpd/solicitacoes",
  "/dossie",
  "/consentimentos",
  "/preferencias",
  "/anonimizar",
  "Abrir exclusao LGPD",
  "Registrar pedido LGPD",
  "Dossie e preferencias",
  "ANONIMIZAR",
  "Exportar JSON",
]) {
  assert(
    featureSource.includes(literal),
    `Missing LGPD behavior literal after extraction: ${literal}`,
  );
}

const appRouteSource = read("src/app/routes/SettingsAdminRoutes.jsx");
const lazySource = read("src/app/lazyPages.jsx");
assert(appRouteSource.includes('path="admin/lgpd"'), "Admin LGPD route should remain registered");
assert(
  lazySource.includes("pages/LGPDOperacional.jsx"),
  "Lazy import should keep public page path",
);

console.log("LGPD operacional refactor contract OK");
