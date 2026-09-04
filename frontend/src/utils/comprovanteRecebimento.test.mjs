import assert from "node:assert/strict";
import { test } from "node:test";

import {
  montarDadosComprovanteRecebimento,
  montarTextoComprovanteRecebimento,
} from "./comprovanteRecebimento.js";

test("monta comprovante de uma baixa registrada", () => {
  const comprovante = montarDadosComprovanteRecebimento({
    conta: { id: 19, descricao: "Parcela da venda", cliente_nome: "Ana Vitória" },
    formasPagamento: [{ id: 3, nome: "PIX" }],
    recebimento: {
      id: 7,
      data: "2026-09-04",
      valor: 17555.25,
      forma_pagamento_id: 3,
    },
    saldoRestante: 20,
  });
  const texto = montarTextoComprovanteRecebimento(comprovante);

  assert.match(texto, /CR-19-R-7/);
  assert.match(texto, /Cliente: Ana Vitoria/);
  assert.match(texto, /Forma: PIX/);
  assert.match(texto, /R\$ 17\.555,25/);
  assert.match(texto, /Saldo atual da conta: R\$ 20,00/);
});

test("usa o nome da forma persistido ao reimprimir", () => {
  const comprovante = montarDadosComprovanteRecebimento({
    detalhes: { id: 2, descricao: "Mensalidade", cliente: { nome: "Carlos" } },
    recebimento: { id: 4, valor: 50, data: "2026-08-31", forma_pagamento_nome: "Dinheiro" },
  });

  assert.equal(comprovante.formaPagamento, "Dinheiro");
  assert.equal(comprovante.clienteNome, "Carlos");
});
