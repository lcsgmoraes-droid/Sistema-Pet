import assert from "node:assert/strict";
import test from "node:test";

import { montarPayloadVenda } from "./pdvVendaPayload.js";

test("registra vendedor sem marcar comissao", () => {
  const payload = montarPayloadVenda({
    itens: [],
    vendedor_funcionario_id: 10,
    funcionario_id: null,
  });

  assert.equal(payload.vendedor_funcionario_id, 10);
  assert.equal(payload.funcionario_id, null);
});

test("preserva comissao quando a venda foi marcada", () => {
  const payload = montarPayloadVenda({
    itens: [],
    vendedor_funcionario_id: 10,
    funcionario_id: 10,
  });

  assert.equal(payload.vendedor_funcionario_id, 10);
  assert.equal(payload.funcionario_id, 10);
});
