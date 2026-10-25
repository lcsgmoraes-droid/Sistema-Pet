import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  IFOOD_FINANCIAL_REFRESH_MS,
  IFOOD_FINANCIAL_UPDATED_EVENT,
  scheduleIfoodFinancialReportRefresh,
} from "./ifoodFinancialRefresh.js";
import { createControllerHarness } from "../../scripts/helpers/reactControllerHarness.mjs";

function environment(onRefresh, enabled = true) {
  const listeners = new Map();
  const target = () => ({
    hidden: false,
    visibilityState: "visible",
    addEventListener(type, callback) {
      listeners.set(type, callback);
    },
    removeEventListener(type, callback) {
      if (listeners.get(type) === callback) listeners.delete(type);
    },
  });
  const documentTarget = target(),
    windowTarget = target();
  const timers = new Map();
  let timerId = 0,
    instant = 0;
  const stop = scheduleIfoodFinancialReportRefresh(onRefresh, {
    enabled,
    documentTarget,
    windowTarget,
    setTimer(callback, delay) {
      timers.set(++timerId, { callback, delay });
      return timerId;
    },
    clearTimer(id) {
      timers.delete(id);
    },
    now: () => instant,
  });
  return {
    stop,
    documentTarget,
    listeners,
    timers,
    advance(ms) {
      instant += ms;
    },
    tick() {
      const [id, timer] = timers.entries().next().value;
      timers.delete(id);
      timer.callback();
    },
  };
}
const settle = async () => {
  for (let i = 0; i < 8; i++) await Promise.resolve();
};

test("timer relê sem requisições sobrepostas e recupera foco após aba oculta", async () => {
  let calls = 0,
    release;
  const env = environment(() => {
    calls++;
    return new Promise((resolve) => {
      release = resolve;
    });
  });
  assert.equal(calls, 0);
  assert.equal([...env.timers.values()][0].delay, IFOOD_FINANCIAL_REFRESH_MS);
  env.tick();
  await settle();
  assert.equal(calls, 1);
  env.tick();
  await settle();
  assert.equal(calls, 1);
  release();
  await settle();
  env.documentTarget.hidden = true;
  env.documentTarget.visibilityState = "hidden";
  env.tick();
  await settle();
  assert.equal(calls, 1);
  env.documentTarget.hidden = false;
  env.documentTarget.visibilityState = "visible";
  env.listeners.get("visibilitychange")();
  env.listeners.get("focus")();
  await settle();
  assert.equal(calls, 2);
  release();
  await settle();
  env.advance(1_001);
  env.listeners.get(IFOOD_FINANCIAL_UPDATED_EVENT)();
  await settle();
  assert.equal(calls, 3);
  release();
  await settle();
  env.stop();
  assert.equal(env.timers.size, 0);
  assert.equal(env.listeners.size, 0);
});

test("falha pode recuperar na próxima leitura e desmontagem impede chamada agendada", async () => {
  let calls = 0;
  const env = environment(async () => {
    calls++;
    throw new Error("ERP temporariamente indisponível");
  });
  env.tick();
  await settle();
  assert.equal(calls, 1);
  env.tick();
  await settle();
  assert.equal(calls, 2);
  env.listeners.get(IFOOD_FINANCIAL_UPDATED_EVENT)();
  env.stop();
  await settle();
  assert.equal(calls, 2);
  const disabled = environment(() => {
    throw new Error("Não deve consultar sem iFood");
  }, false);
  assert.equal(disabled.timers.size, 0);
  assert.equal(disabled.listeners.size, 0);
  disabled.stop();
});

test("hook usa callback recente sem reiniciar timer ao renderizar ou perder estados da tela", async () => {
  const callbacks = [],
    cleans = [];
  let calls = "";
  const harness = createControllerHarness(
    fileURLToPath(new URL("../hooks/useIfoodFinancialReportRefresh.js", import.meta.url)),
    {
      props: {
        enabled: true,
        refresh: () => {
          calls += "A";
        },
      },
      mocks: new Map([
        [
          "../utils/ifoodFinancialRefresh.js",
          {
            scheduleIfoodFinancialReportRefresh(callback, options) {
              callbacks.push({ callback, options });
              return () => cleans.push(true);
            },
          },
        ],
      ]),
    },
  );
  await harness.update({
    refresh: () => {
      calls += "B";
    },
  });
  assert.equal(callbacks.length, 1);
  callbacks[0].callback();
  assert.equal(calls, "B");
  await harness.update({ enabled: false });
  assert.equal(cleans.length, 1);
  assert.equal(callbacks.at(-1).options.enabled, false);
});

test("importação e custos concluídos avisam relatórios; leitura local não publica evento", async () => {
  let avisos = 0,
    importacoes = 0;
  const relatorio = { orders: [{ order_id: "ordem-1420" }] };
  const harness = createControllerHarness(
    fileURLToPath(new URL("../components/ifood/useIfoodFinanceiro.js", import.meta.url)),
    {
      props: { enabled: true, periodoSugerido: { inicio: "2026-10-24", fim: "2026-10-24" } },
      mocks: new Map([
        [
          "../../api/ifood",
          {
            getIfoodFinanceiroStatus: async () => ({
              data: { can_sync: true, can_edit_costs: true },
            }),
            getIfoodFinanceiroRelatorio: async () => ({ data: relatorio }),
            sincronizarIfoodFinanceiro: async () => {
              importacoes++;
              return { data: relatorio };
            },
            salvarIfoodCustosPedido: async () => ({ data: { order_id: "ordem-1420" } }),
          },
        ],
        [
          "../../utils/ifoodFinancialRefresh.js",
          {
            notifyIfoodFinancialUpdated: () => {
              avisos++;
            },
          },
        ],
      ]),
      globals: { AbortController, Intl, Date },
    },
  );
  await harness.settle();
  assert.equal(avisos, 0);
  assert.equal(importacoes, 0);
  await harness.act(() => harness.tree.sincronizar());
  assert.equal(importacoes, 1);
  assert.equal(avisos, 1);
  await harness.act(() => harness.tree.abrirCustos("ordem-1420"));
  await harness.act(() =>
    harness.tree.alterarCusto("source_note", "Documento Financial conferido"),
  );
  await harness.act(() => harness.tree.salvarCustos());
  assert.equal(avisos, 2);
});
