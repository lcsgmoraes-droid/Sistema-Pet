import assert from "node:assert/strict";
import test from "node:test";

import {
  getKitComponentAvailableStock,
  getKitCompositionFromResponse,
  isExpandIdSelected,
  normalizeExpandId,
} from "./produtosUtils.js";

test("normaliza ids de expansao vindos como numero ou texto", () => {
  assert.equal(normalizeExpandId(42), "42");
  assert.equal(normalizeExpandId("42"), "42");
  assert.equal(isExpandIdSelected(["42"], 42), true);
  assert.equal(isExpandIdSelected([42], "42"), true);
  assert.equal(isExpandIdSelected([41], 42), false);
});

test("extrai a composicao da resposta detalhada do produto", () => {
  const composicao = [{ id: 1, produto_id: 9, quantidade: 3 }];

  assert.deepEqual(
    getKitCompositionFromResponse({ data: { composicao_kit: composicao } }),
    composicao,
  );
  assert.deepEqual(getKitCompositionFromResponse({ composicao_kit: composicao }), composicao);
  assert.deepEqual(getKitCompositionFromResponse({ data: { composicao_kit: null } }), []);
});

test("usa o estoque disponivel informado para cada componente", () => {
  assert.equal(
    getKitComponentAvailableStock({
      estoque_disponivel: "7",
      estoque_componente: 9,
      produto_estoque: 11,
    }),
    7,
  );
  assert.equal(getKitComponentAvailableStock({ estoque_componente: 4 }), 4);
  assert.equal(getKitComponentAvailableStock({ produto_estoque: 2 }), 2);
  assert.equal(getKitComponentAvailableStock({ estoque_disponivel: "invalido" }), null);
  assert.equal(getKitComponentAvailableStock({}), null);
});
