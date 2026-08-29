import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function source(relativePath) {
  return readFileSync(path.resolve(__dirname, "..", relativePath), "utf8");
}

test("tutor agenda banho e tosa diretamente pelo app", () => {
  const service = source("src/services/banhoTosa.service.ts");
  const screen = source("src/screens/services/BanhoTosaScreen.tsx");

  assert.match(service, /api\.post\("\/app\/banho-tosa\/agendamentos", payload\)/);
  assert.match(screen, /criarAgendamentoBanhoTosa/);
  assert.match(screen, /Confirmar agendamento/);
  assert.match(screen, /Agendamento realizado/);
  assert.match(screen, /pet_id: pet\.id/);
  assert.match(screen, /servico_id: servico\.id/);
  assert.match(screen, /horario_inicio: horario/);
});
