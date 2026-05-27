import assert from "node:assert/strict";
import test from "node:test";

import {
  calcularMargemPercentual,
  formatarPorcentagemProduto,
  formatarValorMonetarioProduto,
  montarEstadoProdutoFormulario,
  montarPayloadFornecedorProduto,
  montarPayloadMovimentoEstoque,
  montarPayloadProdutoParaSalvar,
  organizarCategoriasHierarquicas,
  validarProdutoParaSalvar,
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

test("normaliza produto carregado para o estado do formulario", () => {
  assert.deepEqual(
    montarEstadoProdutoFormulario({
      codigo: "ABC",
      nome: "Racao",
      preco_custo: 10,
      preco_venda: 20,
      margem_lucro: 100,
      controle_lote: true,
      preco_ecommerce: 19.9,
      anunciar_ecommerce: false,
    }),
    {
      codigo: "ABC",
      nome: "Racao",
      descricao: "",
      categoria_id: "",
      marca_id: "",
      departamento_id: "",
      tipo: "produto",
      preco_custo: 10,
      preco_venda: 20,
      margem_lucro: 100,
      estoque_minimo: "",
      estoque_maximo: "",
      localizacao: "",
      observacoes: "",
      controle_lote: true,
      status: "ativo",
      preco_ecommerce: 19.9,
      preco_ecommerce_promo: null,
      preco_ecommerce_promo_inicio: null,
      preco_ecommerce_promo_fim: null,
      preco_app: null,
      preco_app_promo: null,
      preco_app_promo_inicio: null,
      preco_app_promo_fim: null,
      anunciar_ecommerce: false,
      anunciar_app: true,
    },
  );
});

test("valida dados obrigatorios antes de salvar produto", () => {
  assert.equal(
    validarProdutoParaSalvar({ nome: "  ", preco_venda: "10" }),
    "Nome do produto é obrigatório",
  );
  assert.equal(
    validarProdutoParaSalvar({ nome: "Racao", preco_venda: "0" }),
    "Preço de venda é obrigatório e deve ser maior que zero",
  );
  assert.equal(
    validarProdutoParaSalvar({ nome: "Racao", preco_venda: "10" }),
    null,
  );
});

test("monta payload numerico para salvar produto respeitando canais ativos", () => {
  assert.deepEqual(
    montarPayloadProdutoParaSalvar({
      _mostrarCanais: true,
      nome: "Racao",
      preco_custo: "12.50",
      preco_venda: "20",
      margem_lucro: "60",
      estoque_minimo: "",
      estoque_maximo: "4",
      categoria_id: "",
      marca_id: "8",
      status: "inativo",
      anunciar_ecommerce: true,
      anunciar_app: true,
    }),
    {
      nome: "Racao",
      preco_custo: 12.5,
      preco_venda: 20,
      margem_lucro: 60,
      estoque_minimo: 0,
      estoque_maximo: 4,
      categoria_id: null,
      marca_id: "8",
      status: "inativo",
      anunciar_ecommerce: false,
      anunciar_app: false,
    },
  );
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
