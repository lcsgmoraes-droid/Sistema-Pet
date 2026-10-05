import assert from "node:assert/strict";
import test from "node:test";

import {
  getSubcategoriasDREDaCategoria,
  resolverCategoriaDREId,
} from "./categoriasFinanceirasUtils.js";
import { garantirCategoriaDRE } from "../../utils/dreCategoriaFinanceira.js";

test("mostra apenas subcategorias pertencentes à categoria financeira", () => {
  const categoria = { id: 10, dre_subcategoria_id: 1 };
  const subs = [
    { id: 1, categoria_id: 7, categoria_financeira_id: null, nome: "Compartilhada" },
    { id: 2, categoria_id: 7, categoria_financeira_id: 10, nome: "Própria" },
    { id: 3, categoria_id: 7, categoria_financeira_id: 11, nome: "De outra" },
  ];
  assert.deepEqual(
    getSubcategoriasDREDaCategoria(categoria, subs).map((sub) => sub.id),
    [2, 1],
  );
});

test("não usa categoria DRE genérica para categoria financeira sem vínculo", () => {
  const base = {
    categoriaFinanceiraId: 10,
    categorias: [{ id: 10, nome: "Aluguel", tipo: "despesa" }],
    subcategoriasDRE: [],
    dreCategorias: [{ id: 7, nome: "Despesas Operacionais", natureza: "despesa" }],
  };
  assert.equal(resolverCategoriaDREId(base), null);
  assert.equal(
    resolverCategoriaDREId({
      ...base,
      dreCategorias: [...base.dreCategorias, { id: 8, nome: "Aluguel", natureza: "despesa" }],
    }),
    8,
  );
});

test("cria categoria DRE antes de permitir cadastrar subcategorias", async () => {
  const chamadas = [];
  const api = {
    get: async (url) => {
      chamadas.push(["get", url]);
      return { data: [] };
    },
    post: async (url, data) => {
      chamadas.push(["post", url, data]);
      return { data: { id: 42 } };
    },
  };
  assert.equal(await garantirCategoriaDRE(api, { nome: "Nova Categoria", tipo: "despesa" }), 42);
  assert.deepEqual(chamadas, [
    ["get", "/dre/categorias"],
    ["post", "/dre/categorias", { nome: "Nova Categoria", natureza: "despesa" }],
  ]);
});

test("classifica CMV novo como custo no plano DRE", async () => {
  let payload;
  const api = {
    get: async () => ({ data: [] }),
    post: async (_url, data) => {
      payload = data;
      return { data: { id: 9 } };
    },
  };
  await garantirCategoriaDRE(api, { nome: "CMV", tipo: "despesa" });
  assert.deepEqual(payload, { nome: "CMV", natureza: "custo" });
});

test("reutiliza categoria DRE de custo existente para CMV", () => {
  assert.equal(
    resolverCategoriaDREId({
      categoriaFinanceiraId: 10,
      categorias: [{ id: 10, nome: "CMV", tipo: "despesa" }],
      subcategoriasDRE: [],
      dreCategorias: [{ id: 7, nome: "CMV", natureza: "custo" }],
    }),
    7,
  );
});
