import assert from "node:assert/strict";
import test from "node:test";
import {
  IFOOD_PROMOTION_BOUNDARY_GRACE_MS,
  IFOOD_PROMOTION_MAX_TIMEOUT_MS,
  IFOOD_PROMOTION_RETRY_DELAYS_MS,
  scheduleIfoodPromotionRefresh,
} from "./ifoodPromotionRefresh.js";

const BASE = Date.parse("2026-10-20T18:00:00.000Z");
const iso = (offset) => new Date(BASE + offset).toISOString();
const metadata = (evaluated = 0, next = 1_000) => ({
  evaluated_at: iso(evaluated),
  next_price_change_at: next === null ? null : iso(next),
});

class FakeTarget {
  hidden = false;
  visibilityState = "visible";
  listeners = new Map();

  addEventListener(type, listener) {
    if (!this.listeners.has(type)) this.listeners.set(type, new Set());
    this.listeners.get(type).add(listener);
  }

  removeEventListener(type, listener) {
    this.listeners.get(type)?.delete(listener);
  }

  dispatch(type) {
    for (const listener of [...(this.listeners.get(type) || [])]) listener();
  }

  count() {
    return [...this.listeners.values()].reduce((sum, listeners) => sum + listeners.size, 0);
  }
}

function fakeBrowser(initial = 0) {
  let clock = initial;
  let sequence = 0;
  const timers = new Map();
  const documentTarget = new FakeTarget();
  const windowTarget = new FakeTarget();
  const calls = [];
  const activity = {};
  const options = {
    now: () => clock,
    setTimer(callback, delay) {
      const id = ++sequence;
      assert.ok(delay <= IFOOD_PROMOTION_MAX_TIMEOUT_MS);
      timers.set(id, { callback, deadline: clock + delay });
      return id;
    },
    clearTimer(id) {
      timers.delete(id);
    },
    documentTarget,
    windowTarget,
    activity,
  };

  function advance(duration) {
    const end = clock + duration;
    let executions = 0;
    while (true) {
      const next = [...timers].sort((a, b) => a[1].deadline - b[1].deadline)[0];
      if (!next || next[1].deadline > end) break;
      assert.ok(++executions < 50, "scheduler não pode entrar em laço de timers");
      clock = next[1].deadline;
      timers.delete(next[0]);
      next[1].callback();
    }
    clock = end;
  }

  return {
    options,
    calls,
    timers,
    documentTarget,
    windowTarget,
    advance,
    jump(duration) {
      clock += duration;
    },
    start(data = metadata(), callback = () => calls.push(clock), extra = {}) {
      return scheduleIfoodPromotionRefresh(data, callback, { ...options, ...extra });
    },
  };
}

test("agenda pela diferença do servidor, mesmo com relógio local divergente", () => {
  const browser = fakeBrowser(123_456_789);
  browser.start();
  browser.advance(1_000);
  assert.deepEqual(browser.calls, []);
  browser.advance(IFOOD_PROMOTION_BOUNDARY_GRACE_MS);
  assert.deepEqual(browser.calls, [123_457_889]);
});

test("resposta após início rearma o fim inclusivo sem manter o timer anterior", () => {
  const browser = fakeBrowser();
  const stopStart = browser.start(metadata(0, 1_000));
  browser.advance(1_100);
  assert.equal(browser.calls.length, 1);
  stopStart();
  // Fim inclusivo em 2s: o backend anuncia a virada um milissegundo depois.
  const stopEnd = browser.start(metadata(1_100, 2_001));
  browser.advance(900);
  assert.equal(browser.calls.length, 1);
  browser.advance(101);
  assert.equal(browser.calls.length, 2);
  stopEnd();
  browser.start(metadata(2_102, null));
  browser.advance(120_000);
  assert.equal(browser.calls.length, 2);
});

test("nova resposta cancela retries e agenda outra promoção", () => {
  const browser = fakeBrowser();
  const stop = browser.start();
  browser.advance(1_100);
  stop();
  browser.start(metadata(1_100, 60_000));
  browser.advance(58_899);
  assert.equal(browser.calls.length, 1);
  browser.advance(101);
  assert.equal(browser.calls.length, 2);
});

test("cleanup cancela timer e listeners, inclusive no ciclo duplo do StrictMode", () => {
  const browser = fakeBrowser();
  browser.start()();
  assert.equal(browser.timers.size, 0);
  assert.equal(browser.documentTarget.count(), 0);
  assert.equal(browser.windowTarget.count(), 0);
  browser.start();
  browser.advance(1_100);
  assert.equal(browser.calls.length, 1);
});

test("desabilitar preserva a âncora da resposta ao reabilitar após gravação", () => {
  const browser = fakeBrowser();
  const stop = browser.start(metadata(0, 10_000));
  browser.advance(2_000);
  stop();
  browser.start(metadata(0, 10_000), undefined, { enabled: false });
  browser.advance(3_000);
  browser.start(metadata(0, 10_000));
  browser.advance(5_100);
  assert.deepEqual(browser.calls, [10_100]);
});

test("períodos longos usam blocos limitados sem consultar a cada bloco", () => {
  const browser = fakeBrowser();
  const next = IFOOD_PROMOTION_MAX_TIMEOUT_MS + 60_000;
  browser.start(metadata(0, next));
  browser.advance(IFOOD_PROMOTION_MAX_TIMEOUT_MS);
  assert.equal(browser.calls.length, 0);
  assert.equal(browser.timers.size, 1);
  browser.advance(60_100);
  assert.equal(browser.calls.length, 1);
});

test("aba suspensa consulta imediatamente ao voltar, deduplicando foco/visibilidade", () => {
  const browser = fakeBrowser();
  browser.start();
  browser.jump(10_000); // Timer ainda não executou: aba suspensa pelo navegador.
  browser.documentTarget.dispatch("visibilitychange");
  browser.windowTarget.dispatch("focus");
  assert.deepEqual(browser.calls, [10_000]);
  assert.equal(browser.timers.size, 1);
});

test("aba oculta não consulta na virada e recupera ao ficar visível", () => {
  const browser = fakeBrowser();
  browser.start();
  browser.documentTarget.hidden = true;
  browser.documentTarget.visibilityState = "hidden";
  browser.advance(1_100);
  assert.deepEqual(browser.calls, []);
  browser.documentTarget.hidden = false;
  browser.documentTarget.visibilityState = "visible";
  browser.documentTarget.dispatch("visibilitychange");
  browser.windowTarget.dispatch("focus");
  assert.deepEqual(browser.calls, [1_100]);
});

test("respostas renovadas preservam deduplicação dos eventos da mesma retomada", () => {
  const browser = fakeBrowser();
  const stop = browser.start(metadata(0, null));
  browser.windowTarget.dispatch("focus");
  stop();
  browser.start(metadata(100, null));
  browser.documentTarget.dispatch("visibilitychange");
  assert.equal(browser.calls.length, 1);
  browser.advance(1_001);
  browser.windowTarget.dispatch("focus");
  assert.equal(browser.calls.length, 2);
});

test("retomar antes da virada consulta sem perder o timer agendado", () => {
  const browser = fakeBrowser();
  browser.start(metadata(0, 10_000));
  browser.advance(5_000);
  browser.windowTarget.dispatch("focus");
  assert.deepEqual(browser.calls, [5_000]);
  browser.advance(5_100);
  assert.deepEqual(browser.calls, [5_000, 10_100]);
});

test("consulta falha tem tentativas limitadas sem polling contínuo", async () => {
  const browser = fakeBrowser();
  let attempts = 0;
  browser.start(metadata(), () => {
    attempts++;
    return Promise.reject(new Error("offline"));
  });
  browser.advance(1_100);
  for (const delay of IFOOD_PROMOTION_RETRY_DELAYS_MS) browser.advance(delay);
  browser.advance(600_000);
  await Promise.resolve();
  assert.equal(attempts, 1 + IFOOD_PROMOTION_RETRY_DELAYS_MS.length);
  assert.equal(browser.timers.size, 0);
});

test("falha síncrona é recuperável e cleanup cancela a tentativa pendente", () => {
  const browser = fakeBrowser();
  let attempts = 0;
  const stop = browser.start(metadata(), () => {
    attempts++;
    throw new Error("consulta indisponível");
  });
  browser.advance(1_100);
  assert.equal(attempts, 1);
  stop();
  browser.advance(600_000);
  browser.windowTarget.dispatch("focus");
  assert.equal(attempts, 1);
});

test("loading que desabilita o hook não reinicia chamadas imediatas após falha", () => {
  const browser = fakeBrowser();
  let stop = browser.start();
  browser.advance(1_100);
  assert.equal(browser.calls.length, 1);
  for (const delay of IFOOD_PROMOTION_RETRY_DELAYS_MS) {
    stop();
    browser.start(metadata(), undefined, { enabled: false });
    browser.advance(100); // A consulta falha sem renovar os metadados.
    stop = browser.start();
    assert.equal(browser.timers.size, 1);
    const before = browser.calls.length;
    browser.advance(delay - 101);
    assert.equal(browser.calls.length, before);
    browser.advance(1);
    assert.equal(browser.calls.length, before + 1);
  }
  stop();
  browser.start(metadata(), undefined, { enabled: false });
  browser.start();
  browser.advance(600_000);
  assert.equal(browser.calls.length, 4);
  assert.equal(browser.timers.size, 0);
});

test("retomada sem promoção preserva backoff enquanto a consulta desabilita o hook", () => {
  const browser = fakeBrowser();
  const data = metadata(0, null);
  const stop = browser.start(data);
  browser.windowTarget.dispatch("focus");
  assert.equal(browser.calls.length, 1);
  stop();
  browser.start(data, undefined, { enabled: false });
  browser.advance(200);
  browser.start(data);
  browser.advance(4_800);
  assert.equal(browser.calls.length, 2);
});

test("callback de timer já enfileirado não afeta o novo agendamento após cleanup", () => {
  const browser = fakeBrowser();
  const stop = browser.start();
  const queued = [...browser.timers.values()][0].callback;
  stop();
  browser.start(metadata(0, 10_000));
  queued(); // Simula callback retirado da fila antes do clearTimeout.
  assert.equal(browser.calls.length, 0);
  assert.equal(browser.options.activity.boundaryReached, false);
  browser.advance(10_100);
  assert.equal(browser.calls.length, 1);
});

test("metadados ausentes, inválidos ou vencidos não criam loops de timers", () => {
  for (const data of [
    null,
    {},
    metadata(0, null),
    metadata(1_000, 1_000),
    metadata(1_001, 1_000),
    { evaluated_at: "invalido", next_price_change_at: iso(1_000) },
    { evaluated_at: iso(0), next_price_change_at: "invalido" },
  ]) {
    const browser = fakeBrowser();
    browser.start(data);
    browser.advance(600_000);
    assert.equal(browser.calls.length, 0);
    assert.equal(browser.timers.size, 0);
  }
});

test("offset explícito equivale ao instante UTC da próxima virada", () => {
  const browser = fakeBrowser();
  browser.start({
    evaluated_at: "2026-10-20T15:00:00-03:00",
    next_price_change_at: "2026-10-20T18:00:01Z",
  });
  browser.advance(1_100);
  assert.deepEqual(browser.calls, [1_100]);
});

test("escopo novo recebe activity nova e não reaproveita a âncora de outro produto", () => {
  const browser = fakeBrowser();
  const stop = browser.start(metadata(0, 10_000));
  browser.advance(5_000);
  stop();
  browser.start(metadata(0, 10_000), undefined, { activity: {} });
  browser.advance(10_100);
  assert.deepEqual(browser.calls, [15_100]);
});
