import assert from "node:assert/strict";
import { test } from "node:test";

import {
  buildCatalogCategories,
  calculateCatalogMetrics,
  filterCatalogProducts,
} from "./ecommerceMvpUtils.js";

const products = [
  {
    id: 1,
    nome: "Racao Premium",
    codigo: "RAC-001",
    categoria_nome: "Racoes",
    preco_venda: 120,
    estoque_atual: 4,
    imagem_principal: "/uploads/racao.jpg",
  },
  {
    id: 2,
    nome: "Brinquedo Bola",
    codigo: "BRI-002",
    categoria: "Brinquedos",
    preco_venda: 30,
    estoque_atual: 0,
  },
  {
    id: 3,
    nome: "Antipulgas",
    codigo: "DEF-003",
    categoria_nome: "Medicamentos",
    preco_venda: 80,
    estoque_atual: 2,
    imagens: [{ url: "/uploads/antipulgas.jpg" }],
  },
];

test("buildCatalogCategories preserva ordem e adiciona opcao todas", () => {
  assert.deepEqual(buildCatalogCategories(products), [
    "todas",
    "Racoes",
    "Brinquedos",
    "Medicamentos",
  ]);
});

test("calculateCatalogMetrics conta imagens, estoque e produtos prontos", () => {
  assert.deepEqual(calculateCatalogMetrics(products), {
    total: 3,
    comImagem: 2,
    emEstoque: 2,
    prontos: 2,
  });
});

test("filterCatalogProducts filtra por busca, categoria, estoque e imagem", () => {
  assert.deepEqual(
    filterCatalogProducts(products, {
      search: "def",
      categoria: "Medicamentos",
      somenteComEstoque: true,
      somenteComImagem: true,
    }).map((product) => product.id),
    [3]
  );
});

test("filterCatalogProducts ordena por prontidao e por preco", () => {
  assert.deepEqual(filterCatalogProducts(products).map((product) => product.id), [1, 3, 2]);
  assert.deepEqual(
    filterCatalogProducts(products, { ordenacaoCatalogo: "menor_preco" }).map((product) => product.id),
    [2, 3, 1]
  );
  assert.deepEqual(
    filterCatalogProducts(products, { ordenacaoCatalogo: "maior_preco" }).map((product) => product.id),
    [1, 3, 2]
  );
});
