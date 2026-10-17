import assert from "node:assert/strict";
import test from "node:test";

import {
  agruparVendasPorVendedor,
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
