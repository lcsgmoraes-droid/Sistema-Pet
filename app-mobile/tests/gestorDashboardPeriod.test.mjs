import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import ts from "typescript";

const source = readFileSync(
  new URL("../src/screens/gestor/GestorDashboardUtils.ts", import.meta.url),
  "utf8",
);
const compiled = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2022,
  },
}).outputText;
const utility = { exports: {} };
Function("exports", "module", compiled)(utility.exports, utility);
const {
  resolveGestorPeriod,
  refreshGestorPeriod,
  toBrasiliaIsoDate,
  parseBRDate,
} = utility.exports;

test("hoje acompanha Brasília mesmo em aparelhos com outros fusos", () => {
  const previousTimezone = process.env.TZ;
  try {
    for (const timezone of [
      "UTC",
      "America/Los_Angeles",
      "Asia/Tokyo",
      "America/Sao_Paulo",
    ]) {
      process.env.TZ = timezone;
      const beforeMidnight = new Date("2026-10-21T02:59:59Z");
      assert.equal(toBrasiliaIsoDate(beforeMidnight), "2026-10-20");
      assert.deepEqual(resolveGestorPeriod("hoje", beforeMidnight), {
        key: "hoje",
        label: "Hoje",
        start: "2026-10-20",
        end: "2026-10-20",
      });
      assert.equal(
        resolveGestorPeriod("hoje", new Date("2026-10-21T03:00:00Z")).end,
        "2026-10-21",
      );
    }
  } finally {
    if (previousTimezone === undefined) delete process.env.TZ;
    else process.env.TZ = previousTimezone;
  }
});

test("atualizar um período rápido após meia-noite passa a consultar o dia atual", () => {
  const selected = resolveGestorPeriod(
    "hoje",
    new Date("2026-10-20T18:00:00Z"),
  );
  const refreshed = refreshGestorPeriod(
    selected,
    new Date("2026-10-21T03:00:00Z"),
  );
  assert.equal(selected.end, "2026-10-20");
  assert.equal(refreshed.start, "2026-10-21");
  assert.equal(refreshed.end, "2026-10-21");
});

test("períodos atravessam ano e mês bissexto com limites inclusivos", () => {
  const newYear = new Date("2027-01-01T04:00:00Z");
  assert.deepEqual(resolveGestorPeriod("ontem", newYear), {
    key: "ontem",
    label: "Ontem",
    start: "2026-12-31",
    end: "2026-12-31",
  });
  assert.equal(resolveGestorPeriod("sete_dias", newYear).start, "2026-12-26");
  assert.deepEqual(
    resolveGestorPeriod("mes_anterior", new Date("2028-03-01T04:00:00Z")),
    {
      key: "mes_anterior",
      label: "Mes anterior",
      start: "2028-02-01",
      end: "2028-02-29",
    },
  );
});

test("período personalizado não se move ao atualizar e data digitada continua civil", () => {
  const custom = {
    key: "personalizado",
    label: "Período",
    start: "2026-10-15",
    end: "2026-10-19",
  };
  assert.equal(
    refreshGestorPeriod(custom, new Date("2026-10-21T03:00:00Z")),
    custom,
  );
  assert.equal(parseBRDate("20/10/2026"), "2026-10-20");
  assert.equal(parseBRDate("29/02/2027"), null);
});
