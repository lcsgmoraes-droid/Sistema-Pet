import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import path from "node:path";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function source(relativePath) {
  return readFileSync(path.resolve(__dirname, "..", relativePath), "utf8");
}

test("funcionario acessa agenda e fila do banho e tosa", () => {
  const navigator = source("src/navigation/FuncionarioNavigator.tsx");
  const home = source("src/screens/funcionario/FuncionarioHomeScreen.tsx");
  const screen = source("src/screens/funcionario/FuncionarioBanhoTosaScreen.tsx");

  assert.match(navigator, /FuncionarioBanhoTosaScreen/);
  assert.match(home, /navigation\.navigate\("FuncionarioBanhoTosa"\)/);
  assert.match(screen, /FuncionarioBanhoTosaAgenda/);
  assert.match(screen, /FuncionarioBanhoTosaFila/);
  assert.match(screen, /realizarCheckinBanhoTosaFuncionario/);
  assert.match(screen, /moverEtapaBanhoTosaFuncionario/);
  assert.match(screen, /setInterval\(\(\) => void carregarOperacao\(false\), 30000\)/);
});

test("agenda do funcionario permite criar horario com pet servico e recurso", () => {
  const service = source("src/services/funcionarioBanhoTosa.service.ts");
  const screen = source("src/screens/funcionario/FuncionarioBanhoTosaScreen.tsx");
  const modal = source(
    "src/screens/funcionario/banho-tosa/FuncionarioBanhoTosaModals.tsx",
  );

  assert.match(service, /\/app\/funcionario\/banho-tosa/);
  assert.match(service, /`\$\{BASE\}\/agenda`/);
  assert.match(screen, /criarAgendamentoBanhoTosaFuncionario/);
  assert.match(modal, /Pet ou tutor/);
  assert.match(modal, /Servico/);
  assert.match(modal, /Box ou recurso/);
});

test("entregador recebe Taxi Dog e pode abrir rota e avancar o trajeto", () => {
  const rotas = source("src/screens/entregador/RotasDoEntregadorScreen.tsx");
  const taxi = source("src/screens/entregador/TaxiDogEntregador.tsx");
  const service = source("src/services/taxiDogEntregador.service.ts");

  assert.match(rotas, /TaxiDogEntregador/);
  assert.match(rotas, /🐾 Taxi Dog/);
  assert.match(service, /\/app\/entregador\/taxi-dog/);
  assert.match(taxi, /Abrir rota/);
  assert.match(taxi, /Entreguei na loja/);
  assert.match(taxi, /entra automaticamente na fila/);
});
