import assert from "node:assert/strict";
import test from "node:test";

import {
  calcularMargemPercentual,
  deveMostrarTipoProdutoNoFormulario,
  formatarPorcentagemProduto,
  formatarValorMonetarioProduto,
  montarAbasProdutoFormulario,
  montarEstadoFornecedorProduto,
  montarEstadoMovimentoEstoque,
  montarEstadoProdutoClonado,
  montarEstadoProdutoFormulario,
  montarProdutoComAlteracao,
  montarPayloadFornecedorProduto,
  montarPayloadMovimentoEstoque,
  montarPayloadProdutoParaSalvar,
  normalizarCodigosBarrasAlternativosCampo,
  normalizarCodigosBarrasAlternativosPayload,
  organizarCategoriasHierarquicas,
  validarArquivoImagemProduto,
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

test("atualiza campo do produto e recalcula margem quando preco muda", () => {
  assert.deepEqual(
    montarProdutoComAlteracao(
      {
        nome: "Racao",
        preco_custo: "50",
        preco_venda: "75",
        margem_lucro: "20",
        anunciar_app: false,
      },
      {
        name: "preco_venda",
        value: "100",
        type: "text",
        checked: false,
      },
    ),
    {
      nome: "Racao",
      preco_custo: "50",
      preco_venda: "100",
      margem_lucro: "100.00",
      anunciar_app: false,
    },
  );

  assert.deepEqual(
    montarProdutoComAlteracao(
      {
        preco_custo: "50",
        preco_venda: "100",
        margem_lucro: "100.00",
        anunciar_app: false,
      },
      {
        name: "anunciar_app",
        value: "on",
        type: "checkbox",
        checked: true,
      },
    ),
    {
      preco_custo: "50",
      preco_venda: "100",
      margem_lucro: "100.00",
      anunciar_app: true,
    },
  );
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

test("normaliza codigos de barras alternativos para campo e payload", () => {
  assert.equal(
    normalizarCodigosBarrasAlternativosCampo('["7890000000001","17890000000002"]'),
    "7890000000001, 17890000000002",
  );

  assert.equal(
    normalizarCodigosBarrasAlternativosPayload("7890000000001, 17890000000002\n7890000000001"),
    '["7890000000001","17890000000002"]',
  );

  assert.equal(normalizarCodigosBarrasAlternativosPayload("   "), null);
});

test("monta estado de produto clonado sem copiar identidade ou estoque", () => {
  const clone = montarEstadoProdutoClonado({
    id: 99,
    codigo: "ABC-123",
    sku: "ABC-123",
    nome: "Racao Premium",
    descricao_curta: "Texto comercial",
    codigo_barras: "789123",
    bling_id: "BL-1",
    categoria_id: 5,
    marca_id: 6,
    departamento_id: 7,
    tipo_produto: "KIT",
    tipo_kit: "VIRTUAL",
    e_kit_fisico: false,
    preco_custo: 12.5,
    preco_venda: 29.9,
    estoque_atual: 18,
    estoque: 18,
    saldo_atual: 18,
    lotes: [{ id: 1, numero_lote: "L-1" }],
    composicao_kit: [
      {
        id: 10,
        produto_id: 20,
        produto_componente_id: 20,
        produto_nome: "Componente",
        quantidade: 2,
        ordem: 1,
      },
    ],
  });

  assert.equal(clone.nome, "Racao Premium (Copia)");
  assert.equal(clone.codigo, "");
  assert.equal(clone.sku, "");
  assert.equal(clone.codigo_barras, "");
  assert.equal(clone.ativo, true);
  assert.equal(clone.situacao, true);
  assert.equal(clone.categoria_id, 5);
  assert.equal(clone.marca_id, 6);
  assert.equal(clone.departamento_id, 7);
  assert.equal(clone.tipo_produto, "KIT");
  assert.equal(clone.tipo_kit, "VIRTUAL");
  assert.equal(clone.preco_custo, 12.5);
  assert.equal(clone.preco_venda, 29.9);
  assert.equal(clone.descricao, "Texto comercial");
  assert.deepEqual(clone.composicao_kit, [
    {
      produto_id: 20,
      produto_componente_id: 20,
      produto_nome: "Componente",
      quantidade: 2,
      ordem: 1,
      opcional: false,
    },
  ]);
  assert.equal(Object.hasOwn(clone, "id"), false);
  assert.equal(Object.hasOwn(clone, "bling_id"), false);
  assert.equal(Object.hasOwn(clone, "estoque_atual"), false);
  assert.equal(Object.hasOwn(clone, "lotes"), false);
});

test("mantem seletor de tipo disponivel para produto existente que nao seja variacao", () => {
  assert.equal(
    deveMostrarTipoProdutoNoFormulario({ isEdicao: false, tipoProduto: "SIMPLES" }),
    true,
  );
  assert.equal(
    deveMostrarTipoProdutoNoFormulario({ isEdicao: true, tipoProduto: "SIMPLES" }),
    true,
  );
  assert.equal(deveMostrarTipoProdutoNoFormulario({ isEdicao: true, tipoProduto: "KIT" }), true);
  assert.equal(deveMostrarTipoProdutoNoFormulario({ isEdicao: true, tipoProduto: "PAI" }), true);
  assert.equal(
    deveMostrarTipoProdutoNoFormulario({ isEdicao: true, tipoProduto: "VARIACAO" }),
    false,
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
  assert.equal(validarProdutoParaSalvar({ nome: "Racao", preco_venda: "10" }), null);
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

test("valida arquivo de imagem permitido para upload do produto", () => {
  assert.equal(validarArquivoImagemProduto({ type: "image/webp", size: 1024 }), null);
  assert.equal(
    validarArquivoImagemProduto({ type: "application/pdf", size: 1024 }),
    "Apenas JPG, PNG e WebP são permitidos",
  );
  assert.equal(
    validarArquivoImagemProduto({ type: "image/png", size: 11 * 1024 * 1024 }),
    "Imagem deve ter no maximo 10MB",
  );
});

test("normaliza estado inicial do modal de fornecedor do produto", () => {
  assert.deepEqual(montarEstadoFornecedorProduto(), {
    fornecedor_id: "",
    codigo_fornecedor: "",
    preco_custo: "",
    prazo_entrega: "",
    estoque_fornecedor: "",
    e_principal: false,
  });

  assert.deepEqual(
    montarEstadoFornecedorProduto({
      fornecedor_id: 12,
      codigo_fornecedor: "FOR-1",
      preco_custo: 8.5,
      prazo_entrega: 3,
      estoque_fornecedor: 20,
      e_principal: true,
    }),
    {
      fornecedor_id: 12,
      codigo_fornecedor: "FOR-1",
      preco_custo: 8.5,
      prazo_entrega: 3,
      estoque_fornecedor: 20,
      e_principal: true,
    },
  );
});

test("cria estado inicial do modal de movimento de estoque", () => {
  assert.deepEqual(montarEstadoMovimentoEstoque(), {
    quantidade: "",
    numero_lote: "",
    preco_custo: "",
    data_validade: "",
    observacao: "",
  });
});

test("monta abas do formulario conforme produto e modo de edicao", () => {
  assert.deepEqual(
    montarAbasProdutoFormulario({
      isEdit: false,
      imagens: [{ id: 1 }],
      fornecedores: [{ id: 10 }],
      lotes: [{ id: 20 }],
      variacoes: [{ id: 30 }],
      produto: { controle_lote: true, tipo_produto: "PAI" },
    }).map(({ id, count }) => ({ id, count })),
    [{ id: "dados", count: null }],
  );

  assert.deepEqual(
    montarAbasProdutoFormulario({
      isEdit: true,
      imagens: [{ id: 1 }, { id: 2 }],
      fornecedores: [{ id: 10 }],
      lotes: [{ id: 20 }, { id: 21 }, { id: 22 }],
      variacoes: [{ id: 30 }],
      produto: { controle_lote: true, tipo_produto: "PAI" },
    }).map(({ id, count }) => ({ id, count })),
    [
      { id: "dados", count: null },
      { id: "imagens", count: 2 },
      { id: "fornecedores", count: 1 },
      { id: "lotes", count: 3 },
      { id: "variacoes", count: 1 },
    ],
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
