import assert from "node:assert/strict";
import test from "node:test";

import { criarCsvNaoVendas } from "./naoVendaRelatorioCsv.js";

test("CSV de não vendas inclui motivos, produtos livres e atendimentos sem produto", () => {
  const csv = criarCsvNaoVendas({
    periodo: { data_inicio: "2026-08-01", data_fim: "2026-08-27" },
    resumo: {
      total_atendimentos: 2,
      atendimentos_identificados: 1,
      atendimentos_anonimos: 1,
      total_produtos_distintos: 1,
      quantidade_total: 3,
      valor_estimado_total: 75,
    },
    motivos: [
      {
        motivo: "Produto não vendido pela loja",
        total_atendimentos: 2,
        percentual: 100,
        valor_estimado_total: 75,
      },
    ],
    produtos: [
      {
        fornecedor: "Fornecedor sugerido",
        marca: "Marca nova",
        sku: "Produto não cadastrado",
        produto_nome: "Ração de pato 15 kg",
        total_atendimentos: 1,
        total_solicitacoes: 1,
        quantidade_total: 3,
        valor_estimado_total: 75,
      },
    ],
    detalhes: [
      {
        data_registro: "2026-08-27T15:00:00Z",
        cliente_nome: "Cliente não identificado",
        cliente_telefone: null,
        motivo: "Cliente estava pesquisando",
        usuario_registrou: "Lucas",
        observacoes: "Sem produto específico",
        valor_estimado_total: 0,
        itens: [],
      },
    ],
  });

  assert.match(csv, /RELATÓRIO DE ATENDIMENTOS SEM VENDA/);
  assert.match(csv, /Produto não vendido pela loja/);
  assert.match(csv, /Ração de pato 15 kg/);
  assert.match(csv, /Fornecedor sugerido/);
  assert.match(csv, /Sem produto informado/);
  assert.ok(csv.startsWith("\uFEFF"));
});
