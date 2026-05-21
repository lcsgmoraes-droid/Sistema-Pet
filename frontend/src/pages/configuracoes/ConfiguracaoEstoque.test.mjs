import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(new URL("./ConfiguracaoEstoque.jsx", import.meta.url), "utf8");

test("ConfiguracaoEstoque explica os bloqueios da protecao por validade", () => {
  assert.match(source, /Quando houver produto ou lote em risco de validade/);
  assert.match(source, /Impede que produtos com lote vencido ou em risco/);
  assert.match(source, /Bloqueia vendas enviadas por canais integrados/);
});
