import assert from "node:assert/strict";
import test from "node:test";
import {
  chavePeriodoDashboard,
  parametrosPeriodoDashboard,
  rotuloPeriodoDashboard,
  validarPeriodoDashboard,
} from "./dashboardPeriod.js";
import { getDashboardDetailPath, getDashboardPeriodFromSearch } from "./dashboardOverview.js";

test("contagem inclusiva aceita um dia, bissexto e 90 dias sem depender do fuso", () => {
  assert.deepEqual(validarPeriodoDashboard({ inicio: "2026-10-22", fim: "2026-10-22" }), {
    erro: "",
    dias: 1,
  });
  assert.deepEqual(validarPeriodoDashboard({ inicio: "2024-02-28", fim: "2024-03-01" }), {
    erro: "",
    dias: 3,
  });
  assert.deepEqual(validarPeriodoDashboard({ inicio: "2026-07-25", fim: "2026-10-22" }), {
    erro: "",
    dias: 90,
  });
  for (const periodo of [
    {},
    { inicio: "2026-10-01", fim: "" },
    { inicio: "2026-02-29", fim: "2026-03-01" },
    { inicio: "2026-10-02", fim: "2026-10-01" },
    { inicio: "2026-07-24", fim: "2026-10-22" },
  ])
    assert.ok(validarPeriodoDashboard(periodo).erro);
});

test("chaves e parametros diferenciam intervalos com a mesma duracao", () => {
  const primeiro = { inicio: "2026-10-01", fim: "2026-10-07" };
  const segundo = { inicio: "2026-10-08", fim: "2026-10-14" };
  assert.notEqual(chavePeriodoDashboard(primeiro), chavePeriodoDashboard(segundo));
  assert.notEqual(chavePeriodoDashboard(primeiro), chavePeriodoDashboard({ dias: 7 }));
  assert.deepEqual(parametrosPeriodoDashboard(primeiro), {
    data_inicio: "2026-10-01",
    data_fim: "2026-10-07",
  });
  assert.deepEqual(parametrosPeriodoDashboard({ dias: 7 }), { periodo_dias: 7 });
  assert.equal(rotuloPeriodoDashboard(primeiro), "01/10/2026 a 07/10/2026");
  assert.equal(rotuloPeriodoDashboard({ dias: 1 }), "Hoje");
  assert.equal(rotuloPeriodoDashboard({ dias: 7 }), "Últimos 7 dias");
});

test("relatorios de vendas e fluxo recuperam as datas personalizadas sem trocar por ultimos dias", () => {
  const periodo = { inicio: "2026-10-01", fim: "2026-10-07" };
  for (const relatorio of ["sales", "cashFlow"]) {
    const path = getDashboardDetailPath(relatorio, periodo);
    const params = new URLSearchParams(path.split("?")[1]);
    assert.equal(params.has("periodo_dias"), false);
    assert.deepEqual(getDashboardPeriodFromSearch(params), {
      days: 7,
      start: "2026-10-01",
      end: "2026-10-07",
      quickFilter: "personalizado",
    });
  }
  for (const query of [
    "data_inicio=2026-10-01",
    "data_inicio=2026-10-02&data_fim=2026-10-01",
    "data_inicio=2026-07-24&data_fim=2026-10-22",
  ])
    assert.equal(getDashboardPeriodFromSearch(new URLSearchParams(query)), null);
});
