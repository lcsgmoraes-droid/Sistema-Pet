import assert from "node:assert/strict";

import {
  deveAdicionarProdutoAutomaticamente,
  encontrarProdutoPorCodigo,
  produtoCorrespondeBusca,
} from "../src/utils/pdvProdutoBuscaUtils.js";

const produto = {
  id: 6083,
  codigo: "6083",
  sku: "SKU-6083",
  codigo_barras: "7898242030076",
  gtin_ean: "17898242030073",
  gtin_ean_tributario: "7898242030076",
  codigos_barras_alternativos: '["0186361","7891000100103"]',
};

assert.equal(encontrarProdutoPorCodigo([produto], "6083")?.id, 6083);
assert.equal(encontrarProdutoPorCodigo([produto], "sku-6083")?.id, 6083);
assert.equal(encontrarProdutoPorCodigo([produto], "7898242030076")?.id, 6083);
assert.equal(encontrarProdutoPorCodigo([produto], "17 898242030073")?.id, 6083);
assert.equal(encontrarProdutoPorCodigo([produto], "018636.1")?.id, 6083);
assert.equal(encontrarProdutoPorCodigo([produto], "7891000100103")?.id, 6083);
assert.equal(produtoCorrespondeBusca(produto, "018636.1"), true);
assert.equal(produtoCorrespondeBusca(produto, "sku-6083 7891000100103"), true);
assert.equal(produtoCorrespondeBusca(produto, "9999999999999"), false);

assert.equal(
  deveAdicionarProdutoAutomaticamente({
    matchExato: produto,
    termo: "7898242030076",
    leituraScannerDetectada: false,
    modoVisualizacao: false,
    ultimoAutoAddProduto: "",
  }),
  true,
);

assert.equal(
  deveAdicionarProdutoAutomaticamente({
    matchExato: produto,
    termo: "7898242030076",
    leituraScannerDetectada: true,
    modoVisualizacao: false,
    ultimoAutoAddProduto: "7898242030076",
  }),
  false,
);

assert.equal(
  deveAdicionarProdutoAutomaticamente({
    matchExato: produto,
    termo: "abc",
    leituraScannerDetectada: false,
    modoVisualizacao: false,
    ultimoAutoAddProduto: "",
  }),
  false,
);

console.log("PDV produto busca: OK");
