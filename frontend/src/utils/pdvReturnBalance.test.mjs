import assert from "node:assert/strict";
import test from "node:test";

import { criarMapaSaldosDevolucao, quantidadeDisponivelDevolucao } from "./pdvReturnBalance.js";

test("devolução parcial só oferece a quantidade ainda disponível", () => {
  const venda = { itens: [{ id: 7, quantidade: 2 }] };
  const resposta = {
    itens: [
      { item_id: 7, quantidade_vendida: 2, quantidade_devolvida: 1, quantidade_disponivel: 1 },
    ],
  };
  const saldos = criarMapaSaldosDevolucao(venda, resposta);

  assert.equal(quantidadeDisponivelDevolucao(saldos, 7), 1);
  assert.equal(quantidadeDisponivelDevolucao(saldos, 999), 0);
});

test("ausência ou incoerência de saldo bloqueia a seleção", () => {
  const venda = { itens: [{ id: 7, quantidade: 2 }] };
  assert.throws(() => criarMapaSaldosDevolucao(venda, { itens: [] }), /saldo devolvível/);
  assert.throws(
    () =>
      criarMapaSaldosDevolucao(venda, {
        itens: [{ item_id: 7, quantidade_devolvida: 1, quantidade_disponivel: 2 }],
      }),
    /saldo devolvível/,
  );
});
