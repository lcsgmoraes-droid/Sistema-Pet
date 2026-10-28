import assert from "node:assert/strict";
import test from "node:test";
import {
  criarPdfProdutosPorFornecedor,
  prepararDadosProdutosPorFornecedorPdf,
} from "./analiseProdutosPdf.js";

const filtros = {
  data_inicio: "2026-01-01",
  data_fim: "2026-10-26",
  fornecedor_id: "7",
  marca_id: "3",
  categoria_id: "9",
  departamento_id: "2",
  canal: "loja_fisica",
  busca: "  desinfetante  ",
};
const geradoEm = new Date("2026-10-26T15:30:00Z");
const produtos = [
  {
    produto_id: 1,
    produto_nome: "Desinfetante Citronela 1 litro",
    codigo: "QUIMI-001",
    fornecedor_id: 7,
    fornecedor_nome: "Quimiagri Ambiental",
    quantidade: 2.125,
    faturamento: 1234.5,
    preco_venda: 9999,
  },
  {
    produto_id: 2,
    produto_nome: "Desinfetante Lavanda 2 litros",
    codigo: "QUIMI-002",
    fornecedor_id: 7,
    fornecedor_nome: "Quimiagri Ambiental",
    quantidade: 3,
    faturamento: 100,
    preco_venda: 9999,
  },
];

test("PDF usa produtos e valores do resultado aplicado sem recalcular pelo preço atual", () => {
  const originais = structuredClone(produtos);
  const dados = prepararDadosProdutosPorFornecedorPdf({
    produtos,
    filtros,
    empresa: { nome_fantasia: "Tecno Agropet" },
    catalogos: {
      fornecedores: [{ id: 7, nome: "Quimiagri Ambiental" }],
      marcas: [{ id: 3, nome: "Domis" }],
      categorias: [{ id: 9, nome: "Limpeza" }],
      departamentos: [{ id: 2, nome: "Pet shop" }],
    },
    geradoEm,
  });

  assert.equal(dados.empresa, "Tecno Agropet");
  assert.equal(dados.periodo, "01/01/2026 a 26/10/2026");
  assert.equal(dados.geradoEm, "26/10/2026, 12:30:00");
  assert.equal(dados.fornecedor, "Quimiagri Ambiental");
  assert.equal(
    dados.filtros,
    "Categoria: Limpeza | Marca: Domis | Departamento: Pet shop | Canal: Loja física | Busca: desinfetante",
  );
  assert.equal(dados.grupos.length, 1);
  assert.deepEqual(dados.grupos[0].linhas, [
    ["Desinfetante Citronela 1 litro", "QUIMI-001", "2,125", "R$ 1.234,50"],
    ["Desinfetante Lavanda 2 litros", "QUIMI-002", "3", "R$ 100,00"],
  ]);
  assert.equal(dados.grupos[0].quantidade, 5.125);
  assert.equal(dados.grupos[0].faturamento, 1334.5);
  assert.equal(dados.totalizadores, "2 produto(s) | Quantidade: 5,125 | Faturamento: R$ 1.334,50");
  assert.match(dados.nota, /alternativo ativo/);
  assert.deepEqual(produtos, originais);
});

test("identifica empresa pelo campo name retornado na sessão autenticada", () => {
  const dados = prepararDadosProdutosPorFornecedorPdf({
    produtos,
    filtros,
    empresa: { id: "tenant-atual", name: "Tecno Agropet" },
    geradoEm,
  });
  assert.equal(dados.empresa, "Tecno Agropet");
});

test("todos os fornecedores agrupam pelo vínculo retornado sem duplicar produtos ou perder sem fornecedor", () => {
  const dados = prepararDadosProdutosPorFornecedorPdf({
    produtos: [
      ...produtos,
      {
        produto_id: 3,
        produto_nome: "Amostra vendida sem valor",
        fornecedor_id: null,
        quantidade: 1,
        faturamento: 0,
      },
      {
        produto_id: 4,
        produto_nome: "Produto independente",
        fornecedor_id: 8,
        fornecedor_nome: "Outro fornecedor",
        quantidade: 10,
        faturamento: 2000,
      },
    ],
    filtros: { data_inicio: filtros.data_inicio, data_fim: filtros.data_fim },
    geradoEm,
  });

  assert.equal(dados.fornecedor, "Todos os fornecedores");
  assert.equal(dados.filtros, "Canal: Todos os canais");
  assert.deepEqual(
    dados.grupos.map((grupo) => grupo.nome),
    ["Outro fornecedor", "Quimiagri Ambiental", "Sem fornecedor"],
  );
  assert.equal(
    dados.grupos.reduce((soma, grupo) => soma + grupo.linhas.length, 0),
    4,
  );
  assert.equal(dados.grupos[2].linhas[0][3], "R$ 0,00");
  assert.match(
    dados.totalizadores,
    /4 produto\(s\) \| Quantidade: 16,125 \| Faturamento: R\$ 3\.334,50/,
  );
  assert.match(dados.nota, /fornecedor principal atual/);
});

test("identifica fornecedor pelo payload quando o catálogo ainda não foi carregado", () => {
  const dados = prepararDadosProdutosPorFornecedorPdf({ produtos, filtros, geradoEm });
  assert.equal(dados.fornecedor, "Quimiagri Ambiental");
  assert.match(dados.filtros, /Marca: Código 3/);
});

test("recorte vazio preserva período, fornecedor e totais zerados", async () => {
  const opcoes = {
    produtos: [],
    filtros,
    geradoEm,
    catalogos: { fornecedores: [{ id: 7, razao_social: "QUIMIAGRI" }] },
  };
  const dados = prepararDadosProdutosPorFornecedorPdf(opcoes);
  assert.equal(dados.fornecedor, "QUIMIAGRI");
  assert.equal(dados.periodo, "01/01/2026 a 26/10/2026");
  assert.deepEqual(dados.grupos, []);
  assert.match(dados.totalizadores, /0 produto\(s\) \| Quantidade: 0 \| Faturamento: R\$ 0,00/);
  const pdf = await criarPdfProdutosPorFornecedor(opcoes);
  assert.equal(pdf.internal.getNumberOfPages(), 1);
  assert.match(pdf.output(), /Nenhuma venda de produto encontrada/);
});

test("PDF pagina tabelas extensas, mantém SKUs e quebra nomes compridos sem omitir linhas", async () => {
  const itens = Array.from({ length: 120 }, (_, indice) => ({
    ...produtos[0],
    produto_id: indice + 1,
    produto_nome: `${"Desinfetante para ambientes e acessórios de animais ".repeat(indice === 0 ? 200 : 3)} Item ${indice + 1}`,
    codigo: `SKU-${String(indice + 1).padStart(3, "0")}`,
    fornecedor_nome: "QUIMIAGRI AMBIENTAL INDÚSTRIA E COMÉRCIO DE DESINFETANTES DOMÉSTICOS LTDA",
    quantidade: indice + 0.125,
    faturamento: 10000 - indice,
  }));
  const pdf = await criarPdfProdutosPorFornecedor({ produtos: itens, filtros, geradoEm });
  assert.ok(pdf.internal.getNumberOfPages() > 4);
  const conteudo = pdf.output();
  for (const item of itens)
    assert.ok(conteudo.includes(item.codigo), `SKU ausente: ${item.codigo}`);
  assert.match(conteudo, /Total geral/);
  assert.ok(conteudo.includes(`de ${pdf.internal.getNumberOfPages()}`));
});

test("vendedores são opcionais e não alteram totais, agrupamento ou produtos originais", async () => {
  const itens = [
    {
      ...produtos[0],
      vendedores: [
        {
          vendedor_id: null,
          vendedor_nome: "",
          quantidade: 0.125,
          faturamento: 234.5,
          participacao_faturamento_pct: 19,
        },
        {
          vendedor_id: 4,
          vendedor_nome: "Maria-SALES-004",
          quantidade: 2,
          faturamento: 1000,
          participacao_faturamento_pct: 81,
        },
      ],
    },
    {
      ...produtos[1],
      vendedores: [
        {
          vendedor_id: 4,
          vendedor_nome: "Maria-SALES-004",
          quantidade: 3,
          faturamento: 100,
          participacao_faturamento_pct: 100,
        },
      ],
    },
  ];
  const originais = structuredClone(itens);
  const resumido = prepararDadosProdutosPorFornecedorPdf({ produtos: itens, filtros, geradoEm });
  const detalhado = prepararDadosProdutosPorFornecedorPdf({
    produtos: itens,
    filtros,
    geradoEm,
    incluirVendedores: true,
  });

  assert.equal(resumido.incluirVendedores, false);
  assert.deepEqual(resumido.grupos[0].linhasVendedores, []);
  assert.equal(detalhado.incluirVendedores, true);
  assert.equal(detalhado.totalizadores, resumido.totalizadores);
  assert.equal(detalhado.grupos[0].quantidade, resumido.grupos[0].quantidade);
  assert.equal(detalhado.grupos[0].faturamento, resumido.grupos[0].faturamento);
  assert.deepEqual(detalhado.grupos[0].linhas, resumido.grupos[0].linhas);
  assert.deepEqual(detalhado.grupos[0].linhasVendedores, [
    [
      ["Vendedor: Maria-SALES-004", "", "2", "R$ 1.000,00", "81,00%"],
      ["Vendedor: Sem vendedor informado", "", "0,125", "R$ 234,50", "19,00%"],
    ],
    [["Vendedor: Maria-SALES-004", "", "3", "R$ 100,00", "100,00%"]],
  ]);
  assert.deepEqual(itens, originais);

  const semVendedores = await criarPdfProdutosPorFornecedor({ produtos: itens, filtros, geradoEm });
  const comVendedores = await criarPdfProdutosPorFornecedor({
    produtos: itens,
    filtros,
    geradoEm,
    incluirVendedores: true,
  });
  assert.doesNotMatch(semVendedores.output(), /SALES-004|Vendedor:/);
  assert.match(comVendedores.output(), /SALES-004/);
  assert.match(comVendedores.output(), /Sem vendedor informado/);
  assert.match(comVendedores.output(), /81,00%/);
  assert.match(comVendedores.output(), /Total geral/);
});

test("vendedores continuam após quebras de página sem perder nomes, quantidades ou participação", async () => {
  const vendedores = Array.from({ length: 100 }, (_, indice) => ({
    vendedor_id: indice + 1,
    vendedor_nome: `${"Nome completo com muitos sobrenomes ".repeat(indice === 0 ? 120 : 3)} SALES-${String(indice + 1).padStart(3, "0")}`,
    quantidade: 1,
    faturamento: 1,
    participacao_faturamento_pct: 1,
  }));
  const itens = [{ ...produtos[0], quantidade: 100, faturamento: 100, vendedores }];
  const pdf = await criarPdfProdutosPorFornecedor({
    produtos: itens,
    filtros,
    geradoEm,
    incluirVendedores: true,
  });
  assert.ok(pdf.internal.getNumberOfPages() > 4);
  const conteudo = pdf.output();
  for (let indice = 1; indice <= vendedores.length; indice += 1)
    assert.ok(conteudo.includes(`SALES-${String(indice).padStart(3, "0")}`));
  assert.match(conteudo, /Vendedores de/);
  assert.match(conteudo, /QUIMI-001/);
  assert.match(conteudo, /1,00%/);
  assert.match(conteudo, /Total geral/);
});
