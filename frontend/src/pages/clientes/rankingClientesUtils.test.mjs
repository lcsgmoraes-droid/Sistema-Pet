import assert from "node:assert/strict";
import { test } from "node:test";

import { obterPeriodoRanking } from "./rankingClientesUtils.js";

const referencia = new Date(2026, 8, 16, 12);

test("monta os atalhos de periodo do ranking", () => {
  assert.deepEqual(obterPeriodoRanking("mes_atual", referencia), {
    data_inicio: "2026-09-01",
    data_fim: "2026-09-16",
  });
  assert.deepEqual(obterPeriodoRanking("mes_anterior", referencia), {
    data_inicio: "2026-08-01",
    data_fim: "2026-08-31",
  });
  assert.deepEqual(obterPeriodoRanking("7_dias", referencia), {
    data_inicio: "2026-09-10",
    data_fim: "2026-09-16",
  });
});
