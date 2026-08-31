import assert from "node:assert/strict";
import test from "node:test";

import {
  getKitComponentAvailableStock,
  getKitCompositionFromResponse,
  isExpandIdSelected,
  normalizeExpandId,
  obterFontesImagemProduto,
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

test("prioriza miniatura e preserva a imagem original como fallback", () => {
  assert.deepEqual(
    obterFontesImagemProduto(
      {
        imagem_principal: "/produtos/1/originais/foto.webp",
        imagem_principal_thumbnail: "/produtos/1/thumbs/foto.webp",
      },
      "https://img.corepet.com.br",
    ),
    {
      src: "https://img.corepet.com.br/produtos/1/thumbs/foto.webp",
      fallbackSrc: "https://img.corepet.com.br/produtos/1/originais/foto.webp",
    },
  );
});

test("deriva a miniatura de imagens antigas sem campo dedicado", () => {
  assert.deepEqual(
    obterFontesImagemProduto(
      { imagem_principal: "https://img.corepet.com.br/produtos/1/originais/foto.webp" },
      "https://corepet.com.br",
    ),
    {
      src: "https://img.corepet.com.br/produtos/1/thumbs/foto.webp",
      fallbackSrc: "https://img.corepet.com.br/produtos/1/originais/foto.webp",
    },
  );
});
