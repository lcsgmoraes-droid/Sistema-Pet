import assert from "node:assert/strict";

import {
  montarFeedbackReprocessamentoVendas,
  normalizarVendaIdsFeedback,
} from "../src/components/financeiro/vendasReprocessamentoFeedback.js";

assert.deepEqual(normalizarVendaIdsFeedback([10, "11", 10, 0, -1, "abc", null]), [10, 11]);

assert.deepEqual(
  montarFeedbackReprocessamentoVendas({
    vendaIds: [3, 2, 1],
    vendasVisiveis: [{ id: 1 }, { id: 2 }, { id: 3 }],
  }),
  {
    ids: [3, 2, 1],
    focoId: 1,
  },
);

assert.deepEqual(
  montarFeedbackReprocessamentoVendas({
    vendaIds: [8],
    vendasVisiveis: [{ id: 1 }, { id: 2 }],
  }),
  {
    ids: [8],
    focoId: 8,
  },
);

assert.deepEqual(
  montarFeedbackReprocessamentoVendas({
    vendaIds: [],
    vendasVisiveis: [{ id: 1 }],
  }),
  {
    ids: [],
    focoId: null,
  },
);
