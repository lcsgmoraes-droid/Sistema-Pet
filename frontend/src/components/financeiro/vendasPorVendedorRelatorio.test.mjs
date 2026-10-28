import assert from "node:assert/strict";
import test from "node:test";

import {
  agruparVendasPorVendedor,
  opcoesProdutosVendas,
  planilhasVendasPorVendedor,
} from "./vendasPorVendedorRelatorio.js";

test("agrupa pelo vendedor indicado, mesmo com operador diferente e nomes iguais", () => {
  const grupos = agruparVendasPorVendedor([
    { id: 1, user_id: 99, vendedor_funcionario_id: 10, vendedor_nome: "Ana", total_venda: 100 },
    { id: 2, user_id: 99, vendedor_funcionario_id: 11, vendedor_nome: "Ana", total_venda: 50 },
    { id: 3, user_id: 88, vendedor_funcionario_id: 10, vendedor_nome: "Ana", total_venda: 25 },
    { id: 4, user_id: 88, vendedor_funcionario_id: null, total_venda: 10 },
  ]);

  assert.deepEqual(
    grupos.map(({ chave, quantidade, total }) => ({ chave, quantidade, total })),
    [
      { chave: "10", quantidade: 2, total: 125 },
      { chave: "11", quantidade: 1, total: 50 },
      { chave: "sem-vendedor", quantidade: 1, total: 10 },
    ],
  );
});

test("opções distinguem produtos com nome igual e ignoram itens sem identificação", () => {
  const opcoes = opcoesProdutosVendas([
    {
      itens: [
        { produto_id: 2, produto_nome: "Ração", produto_codigo: "RAC-02" },
        { produto_id: "2", produto_nome: "Ração", produto_codigo: "RAC-02" },
        { produto_id: 3, produto_nome: "Ração", produto_codigo: "RAC-03" },
        { produto_id: 1, produto_nome: "Areia", produto_codigo: "ARE-01" },
        { produto_nome: "Sem identificação" },
        { produto_id: null, produto_nome: "Sem identificação" },
        { produto_id: "", produto_nome: "Sem identificação" },
      ],
    },
    {},
  ]);

  assert.deepEqual(
    opcoes.map(({ value, label }) => ({ value, label })),
    [
      { value: "1", label: "Areia (ARE-01)" },
      { value: "2", label: "Ração (RAC-02)" },
      { value: "3", label: "Ração (RAC-03)" },
    ],
  );
});

function vendasMistas() {
  return [
    {
      id: 1,
      vendedor_funcionario_id: 10,
      vendedor_nome: "Ana",
      numero_venda: "VEN-1",
      data_venda: "2026-10-17",
      cliente_nome: "Cliente",
      total_venda: 190,
      itens: [
        {
          produto_id: 2,
          produto_nome: "Ração",
          quantidade: 0.125,
          preco_unitario: 20,
          venda_bruta: 2.5,
        },
        {
          produto_id: "2",
          produto_nome: "Ração",
          quantidade: 0.375,
          preco_unitario: 20,
          venda_bruta: 7.5,
        },
        {
          produto_id: 3,
          produto_nome: "Areia",
          quantidade: 2,
          preco_unitario: 100,
          venda_bruta: 200,
        },
      ],
    },
    {
      id: 2,
      vendedor_funcionario_id: 11,
      vendedor_nome: "Ana",
      numero_venda: "VEN-2",
      total_venda: 40,
      itens: [
        {
          produto_id: 2,
          produto_nome: "Ração",
          quantidade: 0.001,
          preco_unitario: 20,
          venda_bruta: 0.02,
        },
      ],
    },
    {
      id: 3,
      vendedor_funcionario_id: 10,
      vendedor_nome: "Ana",
      total_venda: 50,
      itens: [{ produto_id: 3, produto_nome: "Areia", quantidade: 1, venda_bruta: 50 }],
    },
    { id: 4, total_venda: 100 },
  ];
}

test("grupo de produtos soma apenas os itens selecionados sem duplicar a venda", () => {
  const grupos = agruparVendasPorVendedor(vendasMistas(), ["2", "3", "2"]);
  assert.deepEqual(
    grupos.map(({ chave, quantidade, quantidadeProdutos, total }) => ({
      chave,
      quantidade,
      quantidadeProdutos,
      total,
    })),
    [
      { chave: "10", quantidade: 2, quantidadeProdutos: 3.5, total: 260 },
      { chave: "11", quantidade: 1, quantidadeProdutos: 0.001, total: 0.02 },
    ],
  );
  assert.equal(grupos[0].vendas[0].total_relatorio, 210);
  assert.equal(grupos[0].vendas[0].total_venda, 190);
});

test("produto sem código público não mostra o ID interno como código", () => {
  assert.deepEqual(
    opcoesProdutosVendas([{ itens: [{ produto_id: 99999, produto_nome: "Serviço" }] }]).map(
      ({ value, label }) => ({ value, label }),
    ),
    [{ value: "99999", label: "Serviço" }],
  );
});

test("produto em venda mista soma só seus itens e conta a venda uma vez, preservando três decimais", () => {
  const grupos = agruparVendasPorVendedor(vendasMistas(), "2");

  assert.deepEqual(
    grupos.map(({ chave, quantidade, quantidadeProdutos, total }) => ({
      chave,
      quantidade,
      quantidadeProdutos,
      total,
    })),
    [
      { chave: "10", quantidade: 1, quantidadeProdutos: 0.5, total: 10 },
      { chave: "11", quantidade: 1, quantidadeProdutos: 0.001, total: 0.02 },
    ],
  );
  assert.equal(grupos[0].vendas[0].total_venda, 190);
  assert.equal(grupos[0].vendas[0].total_relatorio, 10);
  assert.equal(grupos[0].vendas[0].itens.length, 2);
});

test("bruto zero é respeitado, ausência usa preço vezes quantidade e ausência de vendedor fica visível", () => {
  const grupos = agruparVendasPorVendedor(
    [
      {
        total_venda: 100,
        itens: [
          { produto_id: 2, quantidade: 1, preco_unitario: 50, venda_bruta: 0 },
          { produto_id: 2, quantidade: 0.125, preco_unitario: 20, venda_bruta: null },
          { produto_id: 2, quantidade: 0.25, preco_unitario: 20 },
        ],
      },
    ],
    2,
  );

  assert.equal(grupos[0].chave, "sem-vendedor");
  assert.equal(grupos[0].vendedor, "Sem vendedor");
  assert.equal(grupos[0].total, 7.5);
  assert.equal(grupos[0].quantidadeProdutos, 1.375);
});

test("filtro sem correspondência não atribui vendas de outros produtos", () => {
  assert.deepEqual(agruparVendasPorVendedor(vendasMistas(), "999"), []);
  assert.deepEqual(agruparVendasPorVendedor([], "2"), []);
  assert.deepEqual(opcoesProdutosVendas(), []);
});

test("agrupamento não altera venda, itens nem valores originais", () => {
  const vendas = vendasMistas();
  const originais = structuredClone(vendas);
  for (const venda of vendas) {
    for (const item of venda.itens || []) Object.freeze(item);
    if (venda.itens) Object.freeze(venda.itens);
    Object.freeze(venda);
  }
  Object.freeze(vendas);

  const filtrados = agruparVendasPorVendedor(vendas, "2");
  const todos = agruparVendasPorVendedor(vendas);
  assert.equal(filtrados[0].vendas[0].total_relatorio, 10);
  assert.equal(todos[0].vendas[0].total_relatorio, 190);
  assert.equal(todos[0].vendas[0].itens.length, 3);
  assert.deepEqual(vendas, originais);
});

test("Excel do produto traz quantidade e bruto do produto em resumo e vendas, com período e identificação", () => {
  const grupos = agruparVendasPorVendedor(vendasMistas(), "2");
  const planilhas = planilhasVendasPorVendedor(
    grupos,
    { inicio: "2026-10-01", fim: "2026-10-17" },
    { value: "2", label: "Ração (#2)" },
  );

  assert.deepEqual(planilhas[0].linhas[0], [
    "Vendedor",
    "Quantidade de vendas",
    "Quantidade do produto",
    "Valor bruto do produto",
    "Produto",
    "Período inicial",
    "Período final",
  ]);
  assert.deepEqual(planilhas[0].linhas[1], [
    "Ana",
    1,
    0.5,
    10,
    "Ração (#2)",
    "2026-10-01",
    "2026-10-17",
  ]);
  assert.deepEqual(planilhas[1].linhas[0], [
    "Vendedor",
    "Data",
    "Número da venda",
    "Cliente",
    "Quantidade do produto",
    "Valor bruto do produto",
  ]);
  assert.deepEqual(planilhas[1].linhas[1], ["Ana", "2026-10-17", "VEN-1", "Cliente", 0.5, 10]);
  assert.equal(planilhas[2].linhas.length, 4);
  assert.ok(planilhas[2].linhas.slice(1).every((linha) => linha[2] === "Ração"));
  assert.equal(
    planilhas[2].linhas.slice(1).reduce((total, linha) => total + linha[5], 0),
    10.02,
  );
});

test("exporta vendas e produtos em planilhas separadas sem duplicar total da venda", () => {
  const grupos = agruparVendasPorVendedor([
    {
      id: 1,
      vendedor_funcionario_id: 10,
      vendedor_nome: "Ana",
      numero_venda: "VEN-1",
      data_venda: "2026-10-17",
      cliente_nome: "Cliente",
      total_venda: 90,
      itens: [
        { produto_nome: "Ração", quantidade: 2, preco_unitario: 30, venda_bruta: 60 },
        { produto_nome: "Areia", quantidade: 1, preco_unitario: 40, venda_bruta: 40 },
      ],
    },
  ]);
  const planilhas = planilhasVendasPorVendedor(grupos, {
    inicio: "2026-10-01",
    fim: "2026-10-17",
  });

  assert.equal(planilhas[0].linhas[1][2], 90);
  assert.equal(planilhas[1].linhas.length, 2);
  assert.equal(planilhas[1].linhas[1][4], 90);
  assert.equal(planilhas[2].linhas.length, 3);
  assert.deepEqual(
    planilhas[2].linhas.slice(1).map((linha) => linha[2]),
    ["Ração", "Areia"],
  );
});
