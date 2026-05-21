import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(new URL("./Lembretes.jsx", import.meta.url), "utf8");

test("Lembretes consulta configuracao de validade antes de listar pendencias", () => {
  assert.match(source, /api\.get\(["']\/empresa\/config-estoque["']\)/);
});

test("Lembretes permite processar validade manualmente quando a protecao esta ativa", () => {
  assert.match(source, /api\.post\(["']\/estoque\/validade\/processar["']\)/);
  assert.match(source, /Verificar validade agora/);
});

test("Lembretes mostra estado claro quando a protecao por validade esta desativada", () => {
  assert.match(source, /Protecao por validade desativada/);
  assert.match(source, /\/configuracoes\/estoque/);
});
