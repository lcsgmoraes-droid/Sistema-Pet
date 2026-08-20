import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(
  new URL("./MovimentacoesLancamentosTable.jsx", import.meta.url),
  "utf8",
);
const pageSource = readFileSync(new URL("../MovimentacoesProduto.jsx", import.meta.url), "utf8");

test("tabela preserva largura minima para observacoes", () => {
  assert.match(pageSource, /max-w-\[1440px\]/);
  assert.match(source, /min-w-\[1320px\]/);
  assert.match(source, /min-w-\[320px\]/);
  assert.match(source, /break-words/);
});

test("observacao longa pode ser expandida por movimentacao", () => {
  assert.match(source, /observacoesExpandidas/);
  assert.match(source, /alternarObservacao/);
  assert.match(source, /line-clamp-2/);
  assert.match(source, /Ver mais/);
  assert.match(source, /Ver menos/);
  assert.match(source, /event\.stopPropagation\(\)/);
});
