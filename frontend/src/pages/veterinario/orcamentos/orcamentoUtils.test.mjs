import assert from "node:assert/strict";
import test from "node:test";

import {
  calcularTotaisOrcamento,
  criarItemCatalogoOrcamento,
  criarItemDiariaOrcamento,
  criarItemProdutoOrcamento,
} from "./orcamentoUtils.js";

test("criarItemCatalogoOrcamento usa custo estimado e valor padrao do catalogo", () => {
  const item = criarItemCatalogoOrcamento(
    {
      id: 7,
      nome: "Consulta com medicacao",
      valor_padrao: 150,
      custo_estimado: 18,
    },
    2,
  );

  assert.equal(item.origem, "catalogo");
  assert.equal(item.catalogo_id, 7);
  assert.equal(item.quantidade, 2);
  assert.equal(item.custo_total_estimado, 36);
  assert.equal(item.preco_total, 300);
  assert.equal(item.margem_valor, 264);
  assert.equal(item.margem_percentual, 88);
});

test("criarItemProdutoOrcamento usa custo e preco de venda do produto", () => {
  const item = criarItemProdutoOrcamento(
    {
      id: 44,
      nome: "Defenza 2 - 4,5kg",
      unidade: "un",
      preco_custo: 62.25,
      preco_venda: 99.9,
    },
    3,
  );

  assert.equal(item.origem, "produto");
  assert.equal(item.produto_id, 44);
  assert.equal(item.unidade, "un");
  assert.equal(item.custo_total_estimado, 186.75);
  assert.equal(item.preco_total, 299.7);
});

test("criarItemDiariaOrcamento multiplica previsao de dias", () => {
  const item = criarItemDiariaOrcamento({
    nome: "Internacao",
    custo_unitario_estimado: "80,50",
    preco_unitario: "180",
    dias: 4,
  });

  assert.equal(item.origem, "diaria");
  assert.equal(item.quantidade, 4);
  assert.equal(item.custo_total_estimado, 322);
  assert.equal(item.preco_total, 720);
});

test("calcularTotaisOrcamento soma itens e margem", () => {
  const totais = calcularTotaisOrcamento([
    { custo_total_estimado: 36, preco_total: 300 },
    { custo_total_estimado: 186.75, preco_total: 299.7 },
  ]);

  assert.deepEqual(totais, {
    custo_total_estimado: 222.75,
    preco_total: 599.7,
    margem_valor: 376.95,
    margem_percentual: 62.86,
  });
});
