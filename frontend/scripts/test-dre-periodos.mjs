import assert from "node:assert/strict";
import { obterPeriodoPresetDRE } from "../src/utils/drePeriodos.js";

const hoje = new Date(2026, 7, 14, 12, 0, 0);

assert.deepEqual(obterPeriodoPresetDRE("ano_atual", hoje), {
  periodo: "2026-08",
  mesInicial: 1,
  dataFinal: "2026-08-14",
});

assert.deepEqual(obterPeriodoPresetDRE("mes_atual", hoje), {
  periodo: "2026-08",
  mesInicial: null,
  dataFinal: null,
});

assert.deepEqual(obterPeriodoPresetDRE("mes_anterior", new Date(2026, 0, 10)), {
  periodo: "2025-12",
  mesInicial: null,
  dataFinal: null,
});

console.log("Filtro de período da DRE validado com sucesso.");
