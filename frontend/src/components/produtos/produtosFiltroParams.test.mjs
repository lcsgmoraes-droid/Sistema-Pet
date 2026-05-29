import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { montarFiltrosProdutosParams } from "./produtosFiltroParams.js";

describe("montarFiltrosProdutosParams", () => {
  it("envia status explicito quando o usuario quer ativos e inativos", () => {
    const params = montarFiltrosProdutosParams(
      { ativo: "todos", busca: "", mostrarPaisVariacoes: true },
      { page: 2, pageSize: 50 },
    );

    assert.equal(params.ativo, undefined);
    assert.equal(params.ativo_status, "todos");
    assert.equal(params.page, 2);
    assert.equal(params.page_size, 50);
    assert.equal(params.include_variations, true);
  });

  it("mantem booleano para filtros somente ativos ou somente inativos", () => {
    assert.equal(
      montarFiltrosProdutosParams({ ativo: "ativos" }, { page: 1, pageSize: 20 }).ativo,
      true,
    );
    assert.equal(
      montarFiltrosProdutosParams({ ativo: "inativos" }, { page: 1, pageSize: 20 }).ativo,
      false,
    );
  });
});
