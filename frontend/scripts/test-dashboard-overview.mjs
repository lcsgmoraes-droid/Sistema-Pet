import assert from "node:assert/strict";
import { test } from "node:test";
import {
  calculateDashboardIndicators,
  createEmptyDashboardSummary,
  getExecutiveStatus,
  getPeriodLabel,
} from "../src/pages/dashboard/dashboardOverview.js";

test("dashboard diferencia resultado de caixa e cobertura de despesas", () => {
  const summary = createEmptyDashboardSummary();
  summary.fluxo_periodo = { entradas: 1500, saidas: 1000, lucro: 500 };
  summary.vendas_periodo.quantidade = 8;

  const indicators = calculateDashboardIndicators(summary);

  assert.equal(indicators.cashResult, 500);
  assert.equal(indicators.cashMargin, (500 / 1500) * 100);
  assert.equal(indicators.expenseCoverage, 150);
  assert.equal(getExecutiveStatus(summary).tone, "positive");
});

test("dashboard prioriza caixa negativo com contas vencidas", () => {
  const summary = createEmptyDashboardSummary();
  summary.fluxo_periodo = { entradas: 800, saidas: 1200, lucro: -400 };
  summary.contas_pagar.vencidas = 300;

  const status = getExecutiveStatus(summary);

  assert.equal(status.tone, "critical");
  assert.match(status.description, /contas vencidas/i);
});

test("dashboard não chama ausência de dados de operação saudável", () => {
  assert.equal(getExecutiveStatus(createEmptyDashboardSummary()).tone, "neutral");
  assert.equal(getPeriodLabel(1), "Hoje");
  assert.equal(getPeriodLabel(30), "Últimos 30 dias");
});
