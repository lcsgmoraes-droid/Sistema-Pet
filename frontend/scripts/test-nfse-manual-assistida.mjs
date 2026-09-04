import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const currentDir = dirname(fileURLToPath(import.meta.url));
const read = (path) => readFileSync(resolve(currentDir, path), "utf8");

const api = read("../src/services/nfseManualApi.js");
const panel = read("../src/pages/veterinario/consultaForm/NfseManualPanel.jsx");
const central = read("../src/pages/NfseManual.jsx");
const routes = read("../src/app/routes/SalesMarketingRoutes.jsx");
const menu = read("../src/components/layout/menuConfig.js");

assert.match(api, /\/nfse-manual/);
assert.match(api, /prepararConsulta/);
assert.match(api, /registrarEmitida/);
assert.match(api, /responseType: "blob"/);

assert.match(panel, /Copiar dados/);
assert.match(panel, /Abrir portal de NFS-e/);
assert.match(panel, /Anexar XML/);
assert.match(panel, /Registrar como emitida/);
assert.doesNotMatch(panel, /type="password"|name="[^"]*senha/i);

assert.match(central, /Pendentes/);
assert.match(central, /Emitidas/);
assert.match(central, /Canceladas/);
assert.match(routes, /notas-fiscais\/servicos/);
assert.match(menu, /NFS-e de serviços/);

console.log("NFS-e manual assistida contract checks passed.");
