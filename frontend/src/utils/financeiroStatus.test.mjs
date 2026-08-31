import assert from "node:assert/strict";

import {
  calcularSaldoAtualizadoFinanceiro,
  calcularSaldoFinanceiro,
  ehContaDeRepasseCartao,
  ehLancamentoFinanceiroCancelado,
} from "./financeiroStatus.js";

assert.equal(ehLancamentoFinanceiroCancelado("cancelado"), true);
assert.equal(ehLancamentoFinanceiroCancelado({ status: "cancelada" }), true);
assert.equal(ehLancamentoFinanceiroCancelado({ status: "pendente" }), false);

assert.equal(ehContaDeRepasseCartao({ forma_pagamento_tipo: "cartao_debito" }), true);
assert.equal(ehContaDeRepasseCartao({ forma_pagamento_tipo: "cartao_credito" }), true);
assert.equal(ehContaDeRepasseCartao({ forma_pagamento_tipo: "crediario" }), false);
assert.equal(ehContaDeRepasseCartao({ forma_pagamento_tipo: "pix" }), false);

assert.equal(
  calcularSaldoFinanceiro(
    { status: "pendente", valor_final: 10.66, valor_recebido: 0 },
    "valor_recebido",
  ),
  10.66,
);
assert.equal(
  calcularSaldoFinanceiro(
    { status: "cancelado", valor_final: 10.66, valor_recebido: 0 },
    "valor_recebido",
  ),
  0,
);
assert.equal(
  calcularSaldoAtualizadoFinanceiro(
    {
      status: "vencido",
      valor_final: 26.65,
      valor_recebido: 0,
      saldo_atualizado: 27.22,
    },
    "valor_recebido",
  ),
  27.22,
);
assert.equal(
  calcularSaldoAtualizadoFinanceiro(
    { status: "pendente", valor_final: 26.65, valor_recebido: 0 },
    "valor_recebido",
  ),
  26.65,
);
assert.equal(
  calcularSaldoFinanceiro({ status: "cancelado", valor_final: 10.66, valor_pago: 0 }, "valor_pago"),
  0,
);

console.log("financeiroStatus: ok");
