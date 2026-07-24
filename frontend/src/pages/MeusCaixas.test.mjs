import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(new URL("./MeusCaixas.jsx", import.meta.url), "utf8");

test("meus caixas exibe os textos em português sem caracteres corrompidos", () => {
  assert.match(source, /Histórico e gestão dos seus caixas/);
  assert.match(source, /Data Início/);
  assert.doesNotMatch(source, /Ã|Â|ð|�/);
});
