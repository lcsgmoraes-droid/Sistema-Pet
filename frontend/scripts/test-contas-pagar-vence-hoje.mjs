import assert from "node:assert/strict";

import {
  ehVencimentoHojeContasPagar,
  getStatusVisualContasPagar,
} from "../src/components/contas-pagar/contasPagarDisplayHelpers.js";

const hojeNoBrasil = new Date(2026, 6, 17, 16, 30);

assert.equal(
  ehVencimentoHojeContasPagar("2026-07-17", hojeNoBrasil),
  true,
  "A data de vencimento atual deve ser identificada como hoje sem conversao para UTC",
);
assert.equal(
  getStatusVisualContasPagar({ status: "pendente", data_vencimento: "2026-07-17" }, hojeNoBrasil),
  "vence_hoje",
);
assert.equal(
  getStatusVisualContasPagar({ status: "pago", data_vencimento: "2026-07-17" }, hojeNoBrasil),
  "pago",
);
assert.equal(
  getStatusVisualContasPagar({ status: "pendente", data_vencimento: "2026-07-16" }, hojeNoBrasil),
  "vencida",
);
assert.equal(
  getStatusVisualContasPagar({ status: "parcial", data_vencimento: "2026-07-18" }, hojeNoBrasil),
  "parcial",
);

console.log("OK: indicacao de vencimento hoje validada.");
