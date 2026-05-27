import assert from "node:assert/strict";
import test from "node:test";

import {
  calcularMargemPercentual,
  formatarPorcentagemProduto,
  formatarValorMonetarioProduto,
  montarPayloadFornecedorProduto,
  montarPayloadMovimentoEstoque,
  organizarCategoriasHierarquicas,
} from "./produtosFormUtils.js";

test("organiza categorias em hierarquia achatada com nivel", () => {
  const resultado = organizarCategoriasHierarquicas([
    { id: 1, nome: "Racoes", categoria_pai_id: null },
    { id: 2, nome: "Caes", categoria_pai_id: 1 },
    { id: 3, nome: "Gatos", categoria_pai_id: 1 },
    { id: 4, nome: "Medicamentos", categoria_pai_id: null },
    { id: 5, nome: "Filhotes", categoria_pai_id: 2 },
  ]);

  assert.deepEqual(
    resultado.map((categoria) => ({
      id: categoria.id,
      nome: categoria.nome,
      nivel: categoria.nivel,
    })),
    [
      { id: 1, nome: "Racoes", nivel: 0 },
      { id: 2, nome: "Caes", nivel: 1 },
      { id: 5, nome: "Filhotes", nivel: 2 },
      { id: 3, nome: "Gatos", nivel: 1 },
      { id: 4, nome: "Medicamentos", nivel: 0 },
    ],
  );
});

test("formata valores monetarios e percentuais do produto", () => {
  assert.equal(formatarValorMonetarioProduto("12.5"), "R$ 12,50");
  assert.equal(formatarValorMonetarioProduto(null), "R$ 0,00");
  assert.equal(formatarValorMonetarioProduto("abc"), "R$ 0,00");

  assert.equal(formatarPorcentagemProduto("8.2"), "8,20%");
  assert.equal(formatarPorcentagemProduto(""), "0,00%");
  assert.equal(formatarPorcentagemProduto("abc"), "0,00%");
});

test("calcula margem percentual mantendo nulo quando custo nao permite recalculo", () => {
  assert.equal(calcularMargemPercentual("50", "75"), "50.00");
  assert.equal(calcularMargemPercentual("50", "0"), "-100.00");
  assert.equal(calcularMargemPercentual("0", "75"), null);
  assert.equal(calcularMargemPercentual("", "75"), null);
});

test("monta payload normalizado de fornecedor do produto", () => {
  assert.deepEqual(
    montarPayloadFornecedorProduto({
      fornecedor_id: "10",
      codigo_fornecedor: "ABC",
      preco_custo: "12.50",
      prazo_entrega: "7",
      estoque_fornecedor: "3.5",
      e_principal: true,
    }),
    {
      fornecedor_id: "10",
      codigo_fornecedor: "ABC",
      preco_custo: 12.5,
      prazo_entrega: 7,
      estoque_fornecedor: 3.5,
      e_principal: true,
    },
  );

  assert.deepEqual(
    montarPayloadFornecedorProduto({
      fornecedor_id: "10",
      codigo_fornecedor: "",
      preco_custo: "",
      prazo_entrega: "0",
      estoque_fornecedor: "",
      e_principal: false,
    }),
    {
      fornecedor_id: "10",
      codigo_fornecedor: "",
      preco_custo: null,
      prazo_entrega: null,
      estoque_fornecedor: null,
      e_principal: false,
    },
  );
});

test("monta payload de movimentacao de estoque conforme tipo", () => {
  assert.deepEqual(
    montarPayloadMovimentoEstoque("entrada", {
      quantidade: "4",
      numero_lote: "L-1",
      preco_custo: "9.90",
      data_validade: "2026-12-31",
      observacao: "Entrada manual",
    }),
    {
      quantidade: 4,
      observacao: "Entrada manual",
      numero_lote: "L-1",
      preco_custo: 9.9,
      data_validade: "2026-12-31",
    },
  );

  assert.deepEqual(
    montarPayloadMovimentoEstoque("saida", {
      quantidade: "2",
      numero_lote: "L-1",
      preco_custo: "9.90",
      data_validade: "2026-12-31",
      observacao: "",
    }),
    {
      quantidade: 2,
      observacao: null,
    },
  );
});
