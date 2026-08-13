import assert from "node:assert/strict";
import { test } from "node:test";
import {
  calculateDashboardIndicators,
  createEmptyDashboardSummary,
  getDashboardDetailPath,
  getDashboardPeriodFromSearch,
  getExecutiveStatus,
  getPeriodLabel,
} from "../src/pages/dashboard/dashboardOverview.js";

test("dashboard diferencia resultado de caixa e cobertura de despesas", () => {
  const summary = createEmptyDashboardSummary();
  summary.fluxo_periodo = { entradas: 1500, saidas: 1000, lucro: 500 };
  summary.vendas_periodo.quantidade = 8;
  summary.vendas_periodo.unidades = 21.5;
  summary.vendas_periodo.lucro = 325.75;
  summary.contas_pagar.vence_hoje = 180;
  summary.contas_receber.vence_hoje = 90;

  const indicators = calculateDashboardIndicators(summary);

  assert.equal(indicators.cashResult, 500);
  assert.equal(indicators.salesProfit, 325.75);
  assert.equal(indicators.unitsSold, 21.5);
  assert.equal(indicators.dueTodayPayable, 180);
  assert.equal(indicators.dueTodayReceivable, 90);
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
  const empty = createEmptyDashboardSummary();
  assert.equal(empty.contas_pagar.vence_hoje, 0);
  assert.equal(empty.contas_receber.vence_hoje, 0);
  assert.equal(empty.vendas_periodo.unidades, 0);
  assert.equal(empty.vendas_periodo.lucro, 0);
  assert.equal(getExecutiveStatus(empty).tone, "neutral");
  assert.equal(getPeriodLabel(1), "Hoje");
  assert.equal(getPeriodLabel(30), "Últimos 30 dias");
});

test("dashboard cria links com o filtro detalhado de cada card", () => {
  assert.equal(
    getDashboardDetailPath("payableOverdue"),
    "/financeiro/contas-pagar?filtro=vencidas",
  );
  assert.equal(
    getDashboardDetailPath("payableDueToday"),
    "/financeiro/contas-pagar?filtro=vence_hoje",
  );
  assert.equal(
    getDashboardDetailPath("receivableOpen"),
    "/financeiro/contas-receber?filtro=em_aberto",
  );
  assert.equal(getDashboardDetailPath("sales", 15), "/financeiro/vendas?periodo_dias=15");
  assert.equal(getDashboardDetailPath("activeCustomers"), "/clientes?visao=ativos");
  assert.equal(getDashboardDetailPath("vipAtRisk"), "/clientes?visao=vip_em_risco");
  assert.equal(getDashboardDetailPath("promisingCustomers"), "/clientes?visao=novos_promissores");
});

test("tela detalhada recupera o mesmo período selecionado no dashboard", () => {
  const period = getDashboardPeriodFromSearch(
    new URLSearchParams("periodo_dias=7"),
    new Date(2026, 7, 13, 15, 30),
  );

  assert.deepEqual(period, {
    days: 7,
    start: "2026-08-07",
    end: "2026-08-13",
    quickFilter: "ultimos_7_dias",
  });
});
