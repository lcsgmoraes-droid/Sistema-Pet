import assert from "node:assert/strict";
import test from "node:test";

import { normalizarEtapaConsultaQuery } from "./consultaEtapaQuery.js";

test("normalizarEtapaConsultaQuery aceita apenas etapas conhecidas", () => {
  assert.equal(normalizarEtapaConsultaQuery("2"), 2);
  assert.equal(normalizarEtapaConsultaQuery("diagnostico"), 2);
  assert.equal(normalizarEtapaConsultaQuery("prescricao"), 2);
  assert.equal(normalizarEtapaConsultaQuery("1"), 1);
  assert.equal(normalizarEtapaConsultaQuery("99"), null);
  assert.equal(normalizarEtapaConsultaQuery("texto qualquer"), null);
});
