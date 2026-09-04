import assert from "node:assert/strict";
import { test } from "node:test";
import { VENDAS_LISTA_TABLE_LAYOUT } from "./vendasListaLayout.js";

test("mantem o cabecalho da lista de vendas visivel durante a rolagem", () => {
  assert.match(VENDAS_LISTA_TABLE_LAYOUT.scrollContainerClassName, /\boverflow-y-auto\b/);
  assert.match(VENDAS_LISTA_TABLE_LAYOUT.scrollContainerClassName, /\bmax-h-/);
  assert.match(VENDAS_LISTA_TABLE_LAYOUT.theadClassName, /\bsticky\b/);
  assert.match(VENDAS_LISTA_TABLE_LAYOUT.theadClassName, /\btop-0\b/);
  assert.match(VENDAS_LISTA_TABLE_LAYOUT.theadClassName, /\bz-20\b/);
});
