import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function source(relativePath) {
  return readFileSync(path.resolve(__dirname, "..", relativePath), "utf8");
}

test("perfil gestor usa navegacao propria", () => {
  const appNavigator = source("src/navigation/AppNavigator.tsx");
  const gestorNavigator = source("src/navigation/GestorNavigator.tsx");

  assert.match(appNavigator, /perfil_operacional === "gestor"/);
  assert.match(appNavigator, /<GestorNavigator \/>/);
  assert.match(gestorNavigator, /GestorDashboardScreen/);
  assert.match(gestorNavigator, /HeaderProfileActions/);
});

test("dashboard gestor consulta resumo protegido e exibe filtros principais", () => {
  const service = source("src/services/gestor.service.ts");
  const screen = source("src/screens/gestor/GestorDashboardScreen.tsx");
  const utils = source("src/screens/gestor/GestorDashboardUtils.ts");

  assert.match(service, /\/app\/gestor\/resumo/);
  assert.match(utils, /Hoje/);
  assert.match(utils, /Ontem/);
  assert.match(utils, /7 dias/);
  assert.match(utils, /Este mes/);
  assert.match(utils, /Mes anterior/);
  assert.match(screen, /Faturamento/);
  assert.match(screen, /Fluxo de caixa de hoje/);
  assert.match(screen, /Contas a receber/);
  assert.match(screen, /Resultado da DRE/);
});
