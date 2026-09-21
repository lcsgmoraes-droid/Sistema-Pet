import assert from "node:assert/strict";
import test from "node:test";

import { descricaoFormaPagamento, rotuloFormaPagamento } from "./pdvPaymentDisplay.js";

test("formata as formas de pagamento mais comuns do PDV", () => {
  assert.equal(rotuloFormaPagamento({ forma_pagamento: "pix" }), "Pix");
  assert.equal(rotuloFormaPagamento({ forma_pagamento: "cartao_credito" }), "Cartão de crédito");
  assert.equal(
    rotuloFormaPagamento({ forma_pagamento: "cartao", modalidade_cartao: "debito" }),
    "Cartão de débito",
  );
});

test("preserva nomes personalizados e informa o parcelamento", () => {
  assert.equal(rotuloFormaPagamento({ forma_pagamento: "Convênio da loja" }), "Convênio da loja");
  assert.equal(
    descricaoFormaPagamento({ forma_pagamento: "crediario", numero_parcelas: 3 }),
    "Crediário · 3x",
  );
});
