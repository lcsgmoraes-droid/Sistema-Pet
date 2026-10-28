import assert from "node:assert/strict";
import test from "node:test";
import { DASHBOARD_REFRESH_INTERVAL_MS, iniciarAtualizacaoDashboard } from "./dashboardRefresh.js";

function criarAlvoEventos(visibilityState) {
  const listeners = new Map();
  return {
    visibilityState,
    listeners,
    addEventListener(tipo, callback) {
      if (!listeners.has(tipo)) listeners.set(tipo, new Set());
      listeners.get(tipo).add(callback);
    },
    removeEventListener(tipo, callback) {
      listeners.get(tipo)?.delete(callback);
    },
    disparar(tipo) {
      for (const callback of [...(listeners.get(tipo) || [])]) callback({ type: tipo });
    },
    quantidadeListeners() {
      return [...listeners.values()].reduce((total, callbacks) => total + callbacks.size, 0);
    },
  };
}

function criarRelogio() {
  let agora = 0;
  let proximoId = 0;
  const timers = new Map();
  const cancelados = [];
  return {
    timers,
    cancelados,
    setTimer(callback, intervalo) {
      const id = ++proximoId;
      timers.set(id, { callback, intervalo, proxima: agora + intervalo });
      return id;
    },
    clearTimer(id) {
      cancelados.push(id);
      timers.delete(id);
    },
    avancar(milisegundos) {
      const destino = agora + milisegundos;
      while (true) {
        const proximo = [...timers.values()]
          .filter((timer) => timer.proxima <= destino)
          .sort((a, b) => a.proxima - b.proxima)[0];
        if (!proximo) break;
        agora = proximo.proxima;
        proximo.proxima += proximo.intervalo;
        proximo.callback();
      }
      agora = destino;
    },
  };
}

function preparar(atualizar) {
  const documentTarget = criarAlvoEventos("visible");
  const windowTarget = criarAlvoEventos();
  const relogio = criarRelogio();
  const iniciar = (callback = atualizar) =>
    iniciarAtualizacaoDashboard({
      atualizar: callback,
      documentTarget,
      windowTarget,
      setTimer: relogio.setTimer,
      clearTimer: relogio.clearTimer,
    });
  return { documentTarget, windowTarget, relogio, iniciar, cleanup: iniciar() };
}

async function concluirTentativa() {
  await Promise.resolve();
  await Promise.resolve();
}

test("agenda 30 segundos sem repetir a carga inicial", async () => {
  let chamadas = 0;
  const caso = preparar(() => chamadas++);
  assert.equal(DASHBOARD_REFRESH_INTERVAL_MS, 30000);
  assert.equal(chamadas, 0);
  caso.relogio.avancar(29999);
  assert.equal(chamadas, 0);
  caso.relogio.avancar(1);
  assert.equal(chamadas, 1);
  await concluirTentativa();
  caso.relogio.avancar(30000);
  assert.equal(chamadas, 2);
  caso.cleanup();
});

test("timer, foco e conexao so consultam quando a aba esta visivel", async () => {
  let chamadas = 0;
  const caso = preparar(() => chamadas++);
  caso.documentTarget.visibilityState = "hidden";
  caso.relogio.avancar(90000);
  caso.windowTarget.disparar("focus");
  caso.windowTarget.disparar("online");
  caso.documentTarget.disparar("visibilitychange");
  assert.equal(chamadas, 0);

  caso.documentTarget.visibilityState = "visible";
  caso.documentTarget.disparar("visibilitychange");
  assert.equal(chamadas, 1);
  await concluirTentativa();
  caso.windowTarget.disparar("focus");
  assert.equal(chamadas, 2);
  await concluirTentativa();
  caso.windowTarget.disparar("online");
  assert.equal(chamadas, 3);
  caso.cleanup();
});

test("prerender tambem aguarda a aba ficar visivel", () => {
  let chamadas = 0;
  const caso = preparar(() => chamadas++);
  caso.documentTarget.visibilityState = "prerender";
  caso.relogio.avancar(30000);
  caso.windowTarget.disparar("focus");
  assert.equal(chamadas, 0);
  caso.cleanup();
});

test("nao sobrepoe timer e eventos enquanto uma consulta esta pendente", async () => {
  let chamadas = 0;
  let resolver;
  const pendente = new Promise((resolve) => {
    resolver = resolve;
  });
  const caso = preparar(() => {
    chamadas++;
    return chamadas === 1 ? pendente : undefined;
  });
  caso.relogio.avancar(30000);
  caso.windowTarget.disparar("focus");
  caso.windowTarget.disparar("online");
  caso.documentTarget.disparar("visibilitychange");
  caso.relogio.avancar(90000);
  assert.equal(chamadas, 1);

  resolver();
  await concluirTentativa();
  caso.relogio.avancar(30000);
  assert.equal(chamadas, 2);
  caso.cleanup();
});

for (const tipo of ["sincrona", "assincrona"]) {
  test(`falha ${tipo} nao impede a proxima tentativa`, async () => {
    let chamadas = 0;
    const caso = preparar(() => {
      chamadas++;
      if (chamadas !== 1) return;
      const erro = new Error("Indisponibilidade temporaria");
      if (tipo === "sincrona") throw erro;
      return Promise.reject(erro);
    });
    caso.relogio.avancar(30000);
    await concluirTentativa();
    caso.relogio.avancar(30000);
    assert.equal(chamadas, 2);
    caso.cleanup();
  });
}

test("cleanup remove recursos e ignora callbacks ja enfileirados", async () => {
  let chamadas = 0;
  const caso = preparar(() => chamadas++);
  const callbackTimer = [...caso.relogio.timers.values()][0].callback;
  const callbackEvento = [...caso.windowTarget.listeners.get("focus")][0];
  assert.equal(caso.windowTarget.quantidadeListeners(), 2);
  assert.equal(caso.documentTarget.quantidadeListeners(), 1);
  caso.cleanup();
  caso.cleanup();
  assert.equal(caso.relogio.timers.size, 0);
  assert.equal(caso.relogio.cancelados.length, 1);
  assert.equal(caso.windowTarget.quantidadeListeners(), 0);
  assert.equal(caso.documentTarget.quantidadeListeners(), 0);

  caso.relogio.avancar(90000);
  caso.windowTarget.disparar("focus");
  caso.windowTarget.disparar("online");
  caso.documentTarget.disparar("visibilitychange");
  await callbackTimer();
  await callbackEvento();
  assert.equal(chamadas, 0);
});

test("resposta tardia apos cleanup nao reativa monitor nem bloqueia nova montagem", async () => {
  let chamadasAntigas = 0;
  let chamadasNovas = 0;
  let rejeitarAntiga;
  const caso = preparar(() => {
    chamadasAntigas++;
    return new Promise((_, reject) => {
      rejeitarAntiga = reject;
    });
  });
  const callbackAntigo = [...caso.relogio.timers.values()][0].callback;
  caso.relogio.avancar(30000);
  caso.cleanup();
  const cleanupNovo = caso.iniciar(() => chamadasNovas++);
  caso.relogio.avancar(30000);
  assert.equal(chamadasAntigas, 1);
  assert.equal(chamadasNovas, 1);
  rejeitarAntiga(new Error("Consulta antiga terminou depois da desmontagem"));
  await concluirTentativa();
  await callbackAntigo();
  caso.windowTarget.disparar("online");
  assert.equal(chamadasAntigas, 1);
  assert.equal(chamadasNovas, 2);
  cleanupNovo();
});
