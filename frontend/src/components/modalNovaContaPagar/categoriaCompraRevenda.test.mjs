import assert from "node:assert/strict";
import { test } from "node:test";

import {
  dadosAoSelecionarCategoria,
  ehCategoriaCompraRevendaPadrao,
} from "./categoriaCompraRevenda.js";

test("compra para revenda padrao sai da DRE sem apagar a categoria", () => {
  const categoria = { id: 42, nome: "Produto para Revenda", dre_subcategoria_id: null };
  const dados = {
    categoria_id: 1,
    afeta_dre: true,
    dre_subcategoria_id: 10,
    tipo_despesa_id: 20,
  };

  assert.equal(ehCategoriaCompraRevendaPadrao(categoria), true);
  assert.deepEqual(dadosAoSelecionarCategoria(dados, categoria, 42), {
    categoria_id: 42,
    afeta_dre: false,
    dre_subcategoria_id: null,
    tipo_despesa_id: null,
  });
  assert.equal(dados.afeta_dre, true);
});

test("outras categorias e a escolha manual posterior preservam a DRE", () => {
  const ligadaDre = { id: 43, nome: "Aluguel", dre_subcategoria_id: 30 };
  const compraComVinculoManual = {
    id: 44,
    nome: "Produto para Revenda",
    dre_subcategoria_id: 40,
  };
  assert.equal(ehCategoriaCompraRevendaPadrao(compraComVinculoManual), false);

  const dadosDepoisDaEscolhaManual = {
    categoria_id: 42,
    afeta_dre: true,
    dre_subcategoria_id: null,
    tipo_despesa_id: null,
  };
  assert.equal(dadosDepoisDaEscolhaManual.afeta_dre, true);
  assert.deepEqual(dadosAoSelecionarCategoria(dadosDepoisDaEscolhaManual, ligadaDre, 43), {
    categoria_id: 43,
    afeta_dre: true,
    dre_subcategoria_id: 30,
    tipo_despesa_id: null,
  });
  assert.deepEqual(
    dadosAoSelecionarCategoria(dadosDepoisDaEscolhaManual, compraComVinculoManual, 44),
    {
      categoria_id: 44,
      afeta_dre: true,
      dre_subcategoria_id: 40,
      tipo_despesa_id: null,
    },
  );
});
