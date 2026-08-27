import assert from "node:assert/strict";
import test from "node:test";

import {
  criarCsvListaEspera,
  formatarQuantidadeListaEspera,
} from "./pendenciasEstoqueRelatorio.js";

test("gera CSV com totalizador por SKU e lista cliente x produto", () => {
  const csv = criarCsvListaEspera({
    resumo: {
      total_clientes: 2,
      total_skus: 1,
      quantidade_total: 3,
      total_registros: 2,
    },
    produtos: [
      {
        fornecedor: "Distribuidora Pet",
        marca: "Special Dog",
        sku: "SD-15KG",
        produto_nome: "Special Dog Carne 15 kg",
        total_clientes: 2,
        quantidade_total: 3,
      },
    ],
    detalhes: [
      {
        cliente_nome: "Ana",
        cliente_telefone: "21999999999",
        fornecedor: "Distribuidora Pet",
        marca: "Special Dog",
        sku: "SD-15KG",
        produto_nome: "Special Dog Carne 15 kg",
        quantidade_desejada: 1,
        status: "pendente",
        prioridade: 1,
        data_registro: "2026-08-27T10:30:00",
      },
    ],
  });

  assert.match(csv, /TOTALIZADOR POR SKU/);
  assert.match(csv, /CLIENTE X PRODUTO/);
  assert.match(csv, /"SD-15KG";"Special Dog Carne 15 kg";"2";"3"/);
  assert.match(csv, /"Ana";"21999999999"/);
});

test("formata quantidade no padrao brasileiro sem casas desnecessarias", () => {
  assert.equal(formatarQuantidadeListaEspera(10), "10");
  assert.equal(formatarQuantidadeListaEspera(7.5), "7,5");
});
