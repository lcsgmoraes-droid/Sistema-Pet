import assert from "node:assert/strict";
import test from "node:test";

import {
  buildSubcategoriasExistentes,
  getSubcategoriasDREDaCategoria,
  podeClassificarCustoPeDRE,
  resolverCategoriaDREId,
} from "./categoriasFinanceirasUtils.js";
import {
  garantirCategoriaDRE,
  prevalidarSubcategoriasDRE,
} from "../../utils/dreCategoriaFinanceira.js";

test("classificação DRE no painel exige categoria financeira editável", () => {
  const propria = { categoria_financeira_id: 10 };
  const geral = { categoria_financeira_id: null };
  const vinculoDeOutra = { categoria_financeira_id: 11 };
  const editavel = { id: 10, tipo_custo: "ambos", pode_editar: true };

  assert.equal(podeClassificarCustoPeDRE({ ...editavel, pode_editar: false }, propria), false);
  assert.equal(podeClassificarCustoPeDRE(editavel, propria), true);
  assert.equal(podeClassificarCustoPeDRE(editavel, geral), true);
  assert.equal(podeClassificarCustoPeDRE(editavel, vinculoDeOutra), false);
  assert.equal(podeClassificarCustoPeDRE({ ...editavel, tipo_custo: "fixo" }, propria), false);
});

test("rejeita subcategoria DRE duplicada antes de qualquer gravação financeira", async () => {
  const chamadas = [];
  const api = {
    get: async (url) => {
      chamadas.push(url);
      return {
        data:
          url === "/dre/categorias"
            ? [{ id: 7, nome: "Operações", natureza: "despesa", ativo: true }]
            : [{ id: 31, categoria_id: 7, nome: "Internet", ativo: true }],
      };
    },
    post: async () => {
      throw new Error("Pré-validação não deve gravar dados");
    },
    put: async () => {
      throw new Error("Pré-validação não deve gravar dados");
    },
  };

  await assert.rejects(
    prevalidarSubcategoriasDRE(api, {
      nomeCategoria: "Operações",
      tipoCategoria: "despesa",
      categoriaFinanceiraId: null,
      categoriaDREId: null,
      subcategorias: [{ nome: "  INTERNÉT  " }],
    }),
    /Subcategoria DRE.*já existe/,
  );
  assert.deepEqual(chamadas.sort(), ["/dre/categorias", "/dre/subcategorias"]);
});

test("rejeita renomeação DRE conflitante e preserva duplicatas históricas sem edição", async () => {
  const api = {
    get: async (url) => ({
      data:
        url === "/dre/categorias"
          ? []
          : [
              {
                id: 31,
                categoria_id: 7,
                categoria_financeira_id: 10,
                nome: "Internet",
                ativo: true,
              },
              {
                id: 32,
                categoria_id: 7,
                categoria_financeira_id: 11,
                nome: "Energia",
                ativo: true,
              },
              {
                id: 33,
                categoria_id: 7,
                categoria_financeira_id: 11,
                nome: "Energia",
                ativo: true,
              },
            ],
    }),
  };
  const base = {
    nomeCategoria: "Operações",
    tipoCategoria: "despesa",
    categoriaFinanceiraId: 10,
    categoriaDREId: 7,
  };

  await assert.rejects(
    prevalidarSubcategoriasDRE(api, {
      ...base,
      subcategorias: [{ id: 31, nome: " ENÉRGIA " }],
    }),
    /Subcategoria DRE.*já existe/,
  );
  await prevalidarSubcategoriasDRE(api, {
    ...base,
    subcategorias: [{ id: 31, nome: "Internet" }],
  });
});

test("rejeita nomes duplicados entre novas subcategorias antes do cadastro", async () => {
  const api = { get: async () => ({ data: [] }) };
  await assert.rejects(
    prevalidarSubcategoriasDRE(api, {
      nomeCategoria: "Nova categoria",
      tipoCategoria: "despesa",
      categoriaFinanceiraId: null,
      categoriaDREId: null,
      subcategorias: [{ nome: "Alimentação" }, { nome: " ALIMENTACAO " }],
    }),
    /Subcategoria DRE.*já existe/,
  );
});

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

test("preserva vínculo principal divergente sem permitir editar subcategoria de outra categoria", () => {
  const categoria = { id: 10, dre_subcategoria_id: 3 };
  const subs = [
    { id: 2, categoria_financeira_id: 10, nome: "Própria" },
    { id: 3, categoria_financeira_id: 11, nome: "Vínculo legado" },
  ];
  const selecionadas = getSubcategoriasDREDaCategoria(categoria, subs);
  assert.deepEqual(
    selecionadas.map((sub) => sub.id),
    [2, 3],
  );
  assert.deepEqual(
    buildSubcategoriasExistentes(selecionadas, categoria.id).map((sub) => sub.somenteVinculo),
    [false, true],
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

test("reutiliza categoria DRE com acento e espaços equivalentes", async () => {
  const api = {
    get: async () => ({
      data: [{ id: 71, nome: "Marketing Digital", natureza: "despesa", ativo: true }],
    }),
    post: async () => {
      throw new Error("Não deveria criar categoria duplicada");
    },
  };
  assert.equal(
    await garantirCategoriaDRE(api, { nome: "  Márketing   DIGITAL ", tipo: "despesa" }),
    71,
  );
});

test("continua após 409 de criação DRE concorrente e propaga conflito real", async () => {
  const conflito = Object.assign(new Error("Já existe"), { response: { status: 409 } });
  let buscas = 0;
  const api = {
    get: async () => ({
      data: ++buscas === 1 ? [] : [{ id: 72, nome: "Marketing", natureza: "despesa", ativo: true }],
    }),
    post: async () => {
      throw conflito;
    },
  };
  assert.equal(await garantirCategoriaDRE(api, { nome: "Márketing", tipo: "despesa" }), 72);

  api.get = async () => ({ data: [] });
  await assert.rejects(
    garantirCategoriaDRE(api, { nome: "Márketing", tipo: "despesa" }),
    (error) => error === conflito,
  );
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

test("classifica custo dos serviços prestados como custo no plano DRE", async () => {
  let payload;
  const api = {
    get: async () => ({ data: [] }),
    post: async (_url, data) => {
      payload = data;
      return { data: { id: 10 } };
    },
  };
  await garantirCategoriaDRE(api, { nome: "Custo dos Serviços Prestados", tipo: "despesa" });
  assert.deepEqual(payload, { nome: "Custo dos Serviços Prestados", natureza: "custo" });
});

test("classifica custo dos servicos prestados sem acento como custo", async () => {
  let payload;
  const api = {
    get: async () => ({ data: [] }),
    post: async (_url, data) => {
      payload = data;
      return { data: { id: 11 } };
    },
  };
  await garantirCategoriaDRE(api, { nome: "Custo dos Servicos Prestados", tipo: "despesa" });
  assert.deepEqual(payload, { nome: "Custo dos Servicos Prestados", natureza: "custo" });
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
