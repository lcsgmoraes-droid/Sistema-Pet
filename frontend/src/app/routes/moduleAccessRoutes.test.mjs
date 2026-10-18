import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const read = (file) => readFileSync(new URL(file, import.meta.url), "utf8");

test("rotas clinicas exigem a permissao explicita do modulo", () => {
  const veterinaryRoutes = read("./VeterinaryRoutes.jsx");
  const bathGroomingRoutes = read("./BathGroomingRoutes.jsx");

  assert.match(veterinaryRoutes, /ProtectedRoute permission="veterinario\.acessar"/);
  assert.match(bathGroomingRoutes, /ProtectedRoute permission="banho_tosa\.acessar"/);
});
