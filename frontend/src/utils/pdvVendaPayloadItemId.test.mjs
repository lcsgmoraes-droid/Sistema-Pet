import assert from "node:assert/strict";
import test from "node:test";

import { montarItensVendaPayload } from "./pdvVendaPayload.js";

const item = {
  id: 91,
  tipo: "produto",
  produto_id: 11,
  quantidade: 1,
  preco_unitario: 100,
  subtotal: 100,
};

test("envia o ID da linha quando o item veio da venda aberta", () => {
  const [payload] = montarItensVendaPayload({
    id: 123,
    itens: [{ ...item, venda_id: 123 }],
  });

  assert.equal(payload.item_id, 91);
});

test("não confunde ID de produto do carrinho com ID de linha da venda", () => {
  const [payload] = montarItensVendaPayload({
    id: 123,
    itens: [{ ...item, venda_id: null }],
  });

  assert.equal(payload.item_id, null);
});
