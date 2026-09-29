import assert from "node:assert/strict";
import test from "node:test";

import { buscarTransacoesParaPdf } from "./clienteFinanceiroPdf.js";

test("o PDF busca todas as páginas com os filtros, sem depender da página exibida", async () => {
  const requisicoes = [];
  const api = {
    async get(url) {
      const parsed = new URL(url, "https://corepet.test");
      requisicoes.push(parsed);
      const pagina = Number(parsed.searchParams.get("page"));
      return {
        data: {
          historico: [{ id: pagina }],
          paginacao: { total_paginas: 3 },
        },
      };
    },
  };

  const transacoes = await buscarTransacoesParaPdf(api, 9681, {
    page: 2,
    per_page: 20,
    data_inicio: "2026-01-01",
    data_fim: "2026-09-29",
    tipo: "venda",
    status: "aberta",
  });

  assert.deepEqual(transacoes, [{ id: 1 }, { id: 2 }, { id: 3 }]);
  assert.deepEqual(
    requisicoes.map((url) => url.searchParams.get("page")),
    ["1", "2", "3"],
  );
  for (const url of requisicoes) {
    assert.equal(url.pathname, "/financeiro/cliente/9681");
    assert.equal(url.searchParams.get("per_page"), "100");
    assert.equal(url.searchParams.get("data_inicio"), "2026-01-01");
    assert.equal(url.searchParams.get("data_fim"), "2026-09-29");
    assert.equal(url.searchParams.get("tipo"), "venda");
    assert.equal(url.searchParams.get("status"), "aberta");
  }
});
