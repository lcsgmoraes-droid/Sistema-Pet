import assert from "node:assert/strict";
import test from "node:test";
import { normalizarBusca, ordenarSugestoesEntidade } from "./buscaEntidades.js";
import { obterCodigoPessoaPublico, obterCodigoProdutoPublico } from "./codigosPublicos.js";

test("código público nunca cai no ID e não confunde código de venda com cliente", () => {
  assert.equal(obterCodigoPessoaPublico({ id: 47644 }), "");
  assert.equal(obterCodigoPessoaPublico({ id: 43087, codigo: "2292" }), "2292");
  assert.equal(obterCodigoPessoaPublico({ codigo: "VENDA-1", cliente_id: 99 }), "");
  assert.equal(
    obterCodigoPessoaPublico({
      codigo: "VENDA-1",
      cliente_id: 99,
      cliente: { id: 99, codigo: "0012" },
    }),
    "0012",
  );
  assert.equal(obterCodigoProdutoPublico({ id: 900 }), "");
  assert.equal(obterCodigoProdutoPublico({ id: 900, codigo: "0007" }), "0007");
  assert.equal(obterCodigoProdutoPublico({ produto_id: 900, produto_codigo: "SKU7" }), "SKU7");
});

test("código exato vem antes de nome alfabético, prefixo e telefone", () => {
  const pessoas = [
    { id: 1, codigo: "A1", nome: "Ana", telefone: "18992292292" },
    { id: 2, codigo: "22921", nome: "Bia" },
    { id: 3, codigo: "2292", nome: "Fernanda" },
    { id: 4, codigo: "12292", nome: "Carlos" },
  ];
  assert.deepEqual(
    ordenarSugestoesEntidade(pessoas, "2292").map((item) => item.id),
    [3, 2, 4, 1],
  );
  assert.equal(pessoas[0].id, 1, "não modifica resultados originais");
});

test("acentos, espaços e palavras fora de ordem respeitam relevância", () => {
  assert.equal(normalizarBusca("  RAÇÃO   CÃES  "), "racao caes");
  const produtos = [
    { id: 1, codigo: "1", nome: "Saco para cães" },
    { id: 2, codigo: "2", nome: "Ração para Cães Adultos" },
    { id: 3, codigo: "3", nome: "Cães Ração" },
  ];
  assert.deepEqual(
    ordenarSugestoesEntidade(produtos, "caes racao", "produto").map((item) => item.id),
    [3, 2, 1],
  );
});

test("SKU e EAN exatos têm prioridade sem usar id técnico", () => {
  const produtos = [
    { id: 789123, codigo: "99", nome: "A" },
    { id: 2, codigo: "88", codigo_barras: "789123", nome: "B" },
  ];
  assert.deepEqual(
    ordenarSugestoesEntidade(produtos, "789123", "produto").map((item) => item.id),
    [2, 789123],
  );
});
