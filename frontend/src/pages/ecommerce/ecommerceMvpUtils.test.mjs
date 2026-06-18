import assert from "node:assert/strict";
import { test } from "node:test";

import {
  DEFAULT_CATALOG_LIMIT,
  buildActiveBanners,
  buildCatalogCategories,
  buildCatalogCategoryOptions,
  buildCatalogQueryParams,
  buildCustomerAddressFields,
  buildCustomerProfileForm,
  buildPaginationWindow,
  buildProductMap,
  calculateCatalogMetrics,
  filterCatalogProducts,
  isCustomerProfileComplete,
  normalizeCatalogPayload,
  resolveStoreDisplayName,
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
    [3],
  );
});

test("filterCatalogProducts ordena por prontidao e por preco", () => {
  assert.deepEqual(
    filterCatalogProducts(products).map((product) => product.id),
    [1, 3, 2],
  );
  assert.deepEqual(
    filterCatalogProducts(products, { ordenacaoCatalogo: "menor_preco" }).map(
      (product) => product.id,
    ),
    [2, 3, 1],
  );
  assert.deepEqual(
    filterCatalogProducts(products, { ordenacaoCatalogo: "maior_preco" }).map(
      (product) => product.id,
    ),
    [1, 3, 2],
  );
});

test("buildActiveBanners prioriza banners do tenant e cai nos padroes", () => {
  assert.deepEqual(buildActiveBanners({ banner_1_url: "/b1.jpg", banner_3_url: "/b3.jpg" }), [
    { type: "image", url: "/b1.jpg" },
    { type: "image", url: "/b3.jpg" },
  ]);
  assert.equal(buildActiveBanners({}).length, 3);
  assert.ok(buildActiveBanners({}).every((banner) => banner.bg && banner.title));
});

test("buildCatalogCategoryOptions usa categorias da API com nomes limpos", () => {
  assert.deepEqual(
    buildCatalogCategoryOptions({
      categories: [
        { id: 10, nome: "Gatos>>Higiene>>Areia Higi\u00eanicas", total: 3 },
        { id: 11, nome: "Ra\u00e7\u00f5es", total: 5 },
      ],
      products,
    }),
    [
      { id: "todas", value: "todas", label: "Todas as categorias", total: 8 },
      {
        id: "10",
        value: "10",
        label: "Areia Higi\u00eanicas",
        rawLabel: "Gatos>>Higiene>>Areia Higi\u00eanicas",
        total: 3,
      },
      { id: "11", value: "11", label: "Ra\u00e7\u00f5es", rawLabel: "Ra\u00e7\u00f5es", total: 5 },
    ],
  );
});

test("buildCatalogQueryParams combina busca categoria ordenacao e paginacao", () => {
  assert.deepEqual(
    buildCatalogQueryParams({
      tenant: "atacadao",
      search: "gran plus",
      category: "12",
      order: "menor_preco",
      page: 3,
      limit: 24,
      channel: "ecommerce",
    }),
    {
      tenant: "atacadao",
      busca: "gran plus",
      categoria_id: 12,
      ordenacao: "menor_preco",
      offset: 48,
      limit: 24,
      canal: "ecommerce",
    },
  );
  assert.equal(
    buildCatalogQueryParams({ tenant: "atacadao", order: "relevancia" }).ordenacao,
    "prontos",
  );
});

test("normalizeCatalogPayload padroniza itens, total e limite", () => {
  assert.deepEqual(normalizeCatalogPayload({ items: products, total: 73, offset: 24 }), {
    items: products,
    total: 73,
    offset: 24,
    limit: DEFAULT_CATALOG_LIMIT,
    categories: [],
  });
});

test("buildPaginationWindow calcula intervalo e paginas proximas", () => {
  assert.deepEqual(buildPaginationWindow({ total: 73, limit: 24, page: 2 }), {
    total: 73,
    limit: 24,
    page: 2,
    totalPages: 4,
    startItem: 25,
    endItem: 48,
    pages: [1, 2, 3, 4],
    hasPrevious: true,
    hasNext: true,
  });
  assert.deepEqual(buildPaginationWindow({ total: 0, limit: 24, page: 1 }).pages, []);
});

test("isCustomerProfileComplete exige nome completo, telefone, cpf e endereco", () => {
  assert.equal(
    isCustomerProfileComplete({
      nome: "Maria Silva",
      telefone: "18999999999",
      cpf: "123.456.789-00",
      endereco: "Rua A",
    }),
    true,
  );
  assert.equal(
    isCustomerProfileComplete({ nome: "Maria", telefone: "18", cpf: "1", endereco: "" }),
    false,
  );
});

test("buildProductMap indexa produtos por id", () => {
  const map = buildProductMap(products);
  assert.equal(map[1].nome, "Racao Premium");
  assert.equal(map[3].codigo, "DEF-003");
});

test("resolveStoreDisplayName usa nome valido, slug ou fallback", () => {
  assert.equal(
    resolveStoreDisplayName({ tenantContext: { name: "Pet Feliz" }, storefrontRef: "loja-teste" }),
    "Pet Feliz",
  );
  assert.equal(
    resolveStoreDisplayName({ tenantContext: { name: "Nome ??" }, storefrontRef: "pet-feliz" }),
    "Pet Feliz",
  );
  assert.equal(resolveStoreDisplayName({ tenantContext: {}, storefrontRef: "" }), "Loja online");
});

test("buildCustomerProfileForm e buildCustomerAddressFields mapeiam endereco alternativo", () => {
  const customer = {
    nome: "Maria Silva",
    telefone: "18999999999",
    cpf: "12345678900",
    cep: "19000-000",
    endereco: "Rua principal",
    numero: "10",
    bairro: "Centro",
    cidade: "Presidente Prudente",
    estado: "SP",
    usar_endereco_entrega_diferente: true,
    endereco_entrega_detalhado: {
      entrega_nome: "Portaria",
      entrega_cep: "19100-000",
      entrega_endereco: "Rua entrega",
      entrega_numero: "20",
      entrega_bairro: "Bairro entrega",
      entrega_cidade: "Alvares Machado",
      entrega_estado: "SP",
    },
  };

  assert.equal(buildCustomerProfileForm(customer).entrega_endereco, "Rua entrega");
  assert.deepEqual(buildCustomerAddressFields(customer), {
    cep: "19100-000",
    endereco: "Rua entrega",
    numero: "20",
    complemento: "",
    bairro: "Bairro entrega",
    cidade: "Alvares Machado",
    estado: "SP",
  });
});
