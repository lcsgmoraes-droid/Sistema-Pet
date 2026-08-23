import assert from "node:assert/strict";

import { calcularSaldoFinanceiro, ehLancamentoFinanceiroCancelado } from "./financeiroStatus.js";

assert.equal(ehLancamentoFinanceiroCancelado("cancelado"), true);
assert.equal(ehLancamentoFinanceiroCancelado({ status: "cancelada" }), true);
assert.equal(ehLancamentoFinanceiroCancelado({ status: "pendente" }), false);

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
  calcularSaldoFinanceiro({ status: "cancelado", valor_final: 10.66, valor_pago: 0 }, "valor_pago"),
  0,
);

console.log("financeiroStatus: ok");
