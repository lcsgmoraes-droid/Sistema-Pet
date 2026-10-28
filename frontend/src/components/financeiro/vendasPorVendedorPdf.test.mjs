import assert from "node:assert/strict";
import test from "node:test";

import { prepararDadosVendasPorVendedorPdf } from "./vendasPorVendedorPdf.js";

const periodo = { inicio: "2026-10-01", fim: "2026-10-21" };
const geradoEm = new Date("2026-10-21T15:30:00Z");
const grupos = [
  {
    vendedor: "João da Conceição",
    quantidade: 1,
    quantidadeProdutos: 0.125,
    total: 2.5,
    vendas: [
      {
        id: 1,
        numero_venda: "VEN-1",
        data_venda: "2026-10-21T00:30:00",
        cliente_nome: "Márcia",
        total_venda: 200,
        total_relatorio: 2.5,
        itens: [
          { produto_nome: "Ração", quantidade: 0.125, preco_unitario: 999, venda_bruta: 999 },
        ],
      },
    ],
  },
];

test("PDF usa valores dos grupos filtrados, sem recalcular com preço ou bruto de itens", () => {
  const originais = structuredClone(grupos);
  const dados = prepararDadosVendasPorVendedorPdf({
    grupos,
    periodo,
    geradoEm,
    produto: { value: "2", label: "Ração (#2)" },
    vendedor: "João da Conceição",
  });

  assert.equal(dados.periodo, "01/10/2026 a 21/10/2026");
  assert.equal(dados.geradoEm, "21/10/2026, 12:30:00");
  assert.equal(dados.produto, "Ração (#2)");
  assert.equal(dados.vendedor, "João da Conceição");
  assert.match(dados.totalizadores, /Quantidade do produto: 0,125/);
  assert.match(dados.totalizadores, /Valor bruto do produto: R\$ 2,50/);
  assert.match(dados.nota, /antes de descontos e taxas/);
  assert.match(dados.nota, /devoluções não são abatidas/);
  assert.deepEqual(dados.resumo, [["João da Conceição", "1", "0,125", "R$ 2,50"]]);
  assert.deepEqual(dados.detalhes, [
    ["João da Conceição", "21/10/2026", "VEN-1", "Márcia", "Ração - 0,125", "R$ 2,50"],
  ]);
  assert.deepEqual(grupos, originais);
});

test("PDF sem produto não mistura unidades no resumo e usa o total original da venda", () => {
  const dados = prepararDadosVendasPorVendedorPdf({ grupos, periodo, geradoEm });

  assert.equal(dados.produto, "Todos os produtos");
  assert.equal(dados.vendedor, "Todos os vendedores");
  assert.doesNotMatch(dados.totalizadores, /Quantidade do produto/);
  assert.deepEqual(dados.resumo, [["João da Conceição", "1", "R$ 2,50"]]);
  assert.equal(dados.detalhes[0][5], "R$ 200,00");
});

test("PDF mantém todos os itens de uma venda extensa para a paginação, com nomes completos", () => {
  const itens = Array.from({ length: 120 }, (_, indice) => ({
    produto_nome: `Ração especial para cães de grande porte ${indice + 1}`,
    quantidade: indice + 1,
  }));
  const dados = prepararDadosVendasPorVendedorPdf({
    grupos: [
      {
        ...grupos[0],
        vendas: [{ ...grupos[0].vendas[0], itens }],
      },
    ],
    periodo,
    geradoEm,
  });

  assert.equal(dados.detalhes[0][4].split("\n").length, 120);
  assert.match(dados.detalhes[0][4], /grande porte 120 - 120$/);
});

test("PDF aceita recorte vazio e mantém identificação do período", () => {
  const dados = prepararDadosVendasPorVendedorPdf({ grupos: [], periodo, geradoEm });
  assert.deepEqual(dados.resumo, []);
  assert.deepEqual(dados.detalhes, []);
  assert.match(dados.totalizadores, /0 venda\(s\)/);
  assert.match(dados.totalizadores, /R\$ 0,00/);
});
