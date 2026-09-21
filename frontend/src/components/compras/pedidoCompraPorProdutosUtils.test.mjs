import assert from "node:assert/strict";
import test from "node:test";
import {
  calcularQuantidadeReposicaoProduto,
  criarItemCatalogoPedido,
  montarTooltipGiroCatalogo,
} from "./pedidoCompraPorProdutosUtils.js";

test("sugere a quantidade necessaria para recompor o estoque minimo", () => {
  assert.equal(calcularQuantidadeReposicaoProduto({ estoque_atual: 2, estoque_minimo: 8 }), 6);
  assert.equal(calcularQuantidadeReposicaoProduto({ estoque_atual: 10, estoque_minimo: 8 }), 1);
  assert.equal(
    calcularQuantidadeReposicaoProduto({
      estoque_atual: 10,
      estoque_minimo: 8,
      quantidade_sugerida: 6.2,
    }),
    7,
  );
});

test("detalha o giro de 7 a 90 dias no tooltip do catalogo", () => {
  const tooltip = montarTooltipGiroCatalogo({
    vendas_janelas: { 7: 2, 15: 5, 30: 12, 60: 25, 90: 40 },
    media_diaria_30: 0.4,
    dias_ate_minimo: 6.5,
  });

  assert.match(tooltip, /7 dias: 2/);
  assert.match(tooltip, /15 dias: 5/);
  assert.match(tooltip, /30 dias: 12/);
  assert.match(tooltip, /60 dias: 25/);
  assert.match(tooltip, /90 dias: 40/);
  assert.match(tooltip, /Média diária \(30 dias\): 0,4/);
  assert.match(tooltip, /Previsão até o mínimo: 6,5 dia/);
});

test("cria item unitario diretamente a partir do catalogo", () => {
  assert.deepEqual(
    criarItemCatalogoPedido({
      produto: { id: 10, nome: "Racao Golden", codigo: "GOLD-10" },
      quantidade: "6",
      custoUnitario: "12.5",
    }),
    {
      produto_id: 10,
      produto_nome: "Racao Golden",
      produto_codigo: "GOLD-10",
      quantidade_pedida: 6,
      unidade_compra: "UN",
      quantidade_por_embalagem: 1,
      quantidade_total_unidades: 6,
      preco_unitario: 12.5,
      desconto_item: 0,
      total: 75,
    },
  );
});

test("preserva a unidade de compra ao atualizar um item existente", () => {
  const item = criarItemCatalogoPedido({
    produto: { id: 20, nome: "Caixa de Petiscos" },
    quantidade: 3,
    custoUnitario: 40,
    itemAtual: {
      produto_id: 20,
      unidade_compra: "CX",
      quantidade_por_embalagem: 4,
      desconto_item: 0,
    },
  });

  assert.equal(item.unidade_compra, "CX");
  assert.equal(item.quantidade_total_unidades, 12);
  assert.equal(item.total, 480);
});
