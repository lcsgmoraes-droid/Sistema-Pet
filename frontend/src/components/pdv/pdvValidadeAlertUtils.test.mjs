import assert from "node:assert/strict";
import { test } from "node:test";

import {
  buildValidadePdvMessage,
  buildValidadePdvQuery,
  extractProdutoIdsCarrinho,
} from "./pdvValidadeAlertUtils.js";

test("extractProdutoIdsCarrinho remove duplicados e aceita formatos do carrinho", () => {
  assert.deepEqual(
    extractProdutoIdsCarrinho([
      { produto_id: 12 },
      { produto: { id: 15 } },
      { id: 12 },
      { produto_id: null },
      null,
    ]),
    [12, 15],
  );
});

test("buildValidadePdvQuery serializa ids repetidos para FastAPI", () => {
  assert.equal(buildValidadePdvQuery([12, 15]), "produto_ids=12&produto_ids=15");
});

test("buildValidadePdvMessage resume produtos em risco", () => {
  assert.equal(
    buildValidadePdvMessage([
      { produto_nome: "Defenza", quantidade_bloqueada: 2 },
      { produto_nome: "Racao Senior", quantidade_bloqueada: 1 },
    ]),
    "Conferir produtos com validade em risco: Defenza (2), Racao Senior (1).",
  );
});
