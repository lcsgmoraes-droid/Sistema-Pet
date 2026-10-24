import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createControllerHarness } from "../../../scripts/helpers/reactControllerHarness.mjs";

const report = {
  imported: true,
  begin_date: "2025-08-01",
  end_date: "2025-08-03",
  basis: "calculation",
  titles: [{ id: "title", difference: null }],
};
const pending = (seconds = 1) => ({
  imported: false,
  job: { id: 7, competence: "2025-08", status: "enqueue", next_retry_after_seconds: seconds },
});
function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}
function setup({ enabled = true, canSync = false } = {}) {
  const requests = { report: [], sync: [], status: [], job: [] };
  const timers = new Map();
  let timerId = 0;
  let now = Date.now();
  class ClockDate extends Date {
    static now() {
      return now;
    }
  }
  const request = (type, payload, config) => {
    const value = deferred();
    requests[type].push({ payload, config, ...value });
    return value.promise;
  };
  const harness = createControllerHarness(
    fileURLToPath(new URL("./useIfoodRepasses.js", import.meta.url)),
    {
      props: { enabled, canSync, periodoSugerido: { inicio: "2025-08-01", fim: "2025-08-03" } },
      mocks: new Map([
        [
          "../../api/ifood",
          {
            getIfoodRepasses: (payload, config) => request("report", payload, config),
            sincronizarIfoodRepasses: (payload, config) => request("sync", payload, config),
            getIfoodConciliacaoStatus: (payload, config) => request("status", payload, config),
            sincronizarIfoodConciliacao: (payload, config) => request("job", payload, config),
          },
        ],
        ["./ifoodPresentation", { mensagemErroIfood: (_, fallback) => fallback }],
      ]),
      globals: {
        AbortController,
        Date: ClockDate,
        setTimeout: (fn, delay) => {
          timers.set(++timerId, {
            fn: () => {
              now += delay;
              fn();
            },
            delay,
          });
          return timerId;
        },
        clearTimeout: (id) => timers.delete(id),
      },
    },
  );
  async function load(data = report) {
    requests.report.at(-1).resolve({ data });
    requests.status.at(-1).resolve({ data: { job: null, imported: false } });
    await harness.settle();
  }
  async function answerJob(data) {
    requests.job.at(-1).resolve({ data });
    await harness.settle();
  }
  async function fire() {
    const [id, timer] = [...timers][0];
    timers.delete(id);
    timer.fn();
    await harness.settle();
  }
  return { harness, requests, timers, load, answerJob, fire };
}

test("repasses inativos não consultam; leitura local não aciona API externa", async () => {
  const inactive = setup({ enabled: false, canSync: true });
  assert.equal(inactive.requests.report.length, 0);
  assert.equal(inactive.requests.status.length, 0);
  const env = setup();
  await env.load();
  await env.harness.act(() => env.harness.tree.sincronizar());
  await env.harness.act(() => env.harness.tree.iniciarConciliacao());
  assert.equal(env.requests.sync.length, 0);
  assert.equal(env.requests.job.length, 0);
});

test("consulta usa base explícita, aceita 90 dias e bloqueia períodos inválidos", async () => {
  const env = setup();
  await env.load();
  await env.harness.act(() => env.harness.tree.alterarBasis("payment"));
  assert.equal(env.requests.report.at(-1).payload.basis, "payment");
  await env.harness.act(() =>
    env.harness.tree.alterarPeriodo({ inicio: "2025-08-01", fim: "2025-10-29" }),
  );
  assert.equal(env.harness.tree.periodoValido, true);
  const count = env.requests.report.length;
  await env.harness.act(() =>
    env.harness.tree.alterarPeriodo({ inicio: "2025-08-01", fim: "2025-10-30" }),
  );
  assert.equal(env.harness.tree.periodoValido, false);
  assert.equal(env.requests.report.length, count);
});

test("resposta antiga não substitui período; falha mantém relatório anterior sem zeros", async () => {
  const env = setup();
  const old = env.requests.report[0];
  await env.harness.act(() =>
    env.harness.tree.alterarPeriodo({ inicio: "2025-08-02", fim: "2025-08-03" }),
  );
  assert.equal(old.config.signal.aborted, true);
  env.requests.report.at(-1).resolve({ data: report });
  await env.harness.settle();
  old.resolve({ data: { titles: [] } });
  await env.harness.settle();
  await env.harness.act(() => env.harness.tree.atualizar());
  env.requests.report.at(-1).reject(new Error("502"));
  await env.harness.settle();
  assert.equal(env.harness.tree.relatorio, report);
  assert.equal(env.harness.tree.relatorio.titles[0].difference, null);
});

test("sincronização de repasses deduplica clique e preserva dados ao falhar", async () => {
  const env = setup({ canSync: true });
  await env.load();
  let saving;
  await env.harness.act(() => {
    saving = env.harness.tree.sincronizar();
  });
  await env.harness.act(() => env.harness.tree.sincronizar());
  assert.equal(env.requests.sync.length, 1);
  env.requests.sync[0].reject(new Error("502"));
  await saving;
  await env.harness.settle();
  assert.equal(env.harness.tree.relatorio, report);
});

test("conciliação acompanha a mesma competência, respeita mínimo 5 s e limite de 8 consultas", async () => {
  const env = setup({ canSync: true });
  await env.load();
  await env.harness.act(() => env.harness.tree.iniciarConciliacao());
  await env.harness.act(() => env.harness.tree.iniciarConciliacao());
  assert.equal(env.requests.job.length, 1);
  await env.answerJob(pending(7));
  assert.equal([...env.timers.values()][0].delay, 7000);
  for (let count = 1; count < 8; count++) {
    await env.fire();
    assert.equal(env.requests.job.length, count + 1);
    await env.answerJob(pending());
    assert.equal(env.requests.job.at(-1).payload.competence, "2025-08");
    if (count < 7) assert.equal([...env.timers.values()][0].delay, 5000);
  }
  await env.fire();
  assert.equal(env.requests.job.length, 8);
  assert.equal(env.timers.size, 0);
  assert.equal(env.harness.tree.limiteAtingido, true);
});

test("inativar aba cancela acompanhamento e preserva competência; retorno faz só GET local", async () => {
  const env = setup({ canSync: true });
  await env.load();
  await env.harness.act(() => env.harness.tree.iniciarConciliacao());
  await env.answerJob(pending());
  await env.harness.update({ enabled: false });
  assert.equal(env.timers.size, 0);
  assert.equal(env.requests.job.at(-1).config.signal.aborted, true);
  await env.harness.update({ enabled: true });
  assert.equal(env.harness.tree.competence, "2025-08");
  assert.equal(env.requests.job.length, 1);
});

test("409 interrompe repetição sem criar outra solicitação e mantém estado recebido", async () => {
  const env = setup({ canSync: true });
  await env.load();
  await env.harness.act(() => env.harness.tree.iniciarConciliacao());
  await env.answerJob(pending());
  await env.fire();
  env.requests.job.at(-1).reject({ response: { status: 409 } });
  await env.harness.settle();
  assert.equal(env.harness.tree.seguindo, false);
  await env.fire();
  assert.equal(env.timers.size, 0);
  assert.equal(env.harness.tree.job.id, 7);
  assert.equal(env.requests.job.length, 2);
});

test("retomar manualmente respeita o backoff e aviso transitório não apaga solicitação", async () => {
  const env = setup({ canSync: true });
  await env.load();
  await env.harness.act(() => env.harness.tree.iniciarConciliacao());
  await env.answerJob({
    ...pending(60),
    job: { ...pending(60).job, last_error: "Arquivo temporariamente indisponível" },
  });
  await env.harness.act(() => env.harness.tree.pausar());
  await env.harness.act(() => env.harness.tree.iniciarConciliacao());
  assert.equal(env.requests.job.length, 1);
  assert.equal(env.harness.tree.aguardandoRetry, true);
  assert.match(env.harness.tree.job.last_error, /temporariamente/);
  await env.fire();
  await env.harness.act(() => env.harness.tree.iniciarConciliacao());
  assert.equal(env.requests.job.length, 2);
});

test("arquivo processado encerra acompanhamento e atualiza repasses locais", async () => {
  const env = setup({ canSync: true });
  await env.load();
  const before = env.requests.report.length;
  await env.harness.act(() => env.harness.tree.iniciarConciliacao());
  await env.answerJob({ imported: true, job: { competence: "2025-08", status: "processed" } });
  assert.equal(env.harness.tree.seguindo, false);
  assert.equal(env.timers.size, 0);
  assert.equal(env.requests.report.length, before + 1);
});

test("conflito normalizado sem identificador não dispara nova solicitação automática", async () => {
  const env = setup({ canSync: true });
  await env.load();
  await env.harness.act(() => env.harness.tree.iniciarConciliacao());
  await env.answerJob({
    imported: false,
    job: { competence: "2025-08", status: "conflict", id: null },
  });
  assert.equal(env.harness.tree.seguindo, false);
  assert.equal(env.timers.size, 0);
  assert.equal(env.requests.job.length, 1);
  assert.equal(env.harness.tree.job.status, "conflict");
});

test("erro terminal encerra polling e mantém relatório, competência e títulos importados", async () => {
  const env = setup({ canSync: true });
  const importado = {
    ...report,
    titles: [
      {
        id: "repasse",
        amount: "91.00",
        reconciliation_status: "matched",
        bank_status: "not_checked",
      },
      {
        id: "boleto",
        amount: "-7.20",
        reconciliation_status: "matched",
        bank_status: "not_checked",
      },
    ],
  };
  await env.load(importado);
  await env.harness.act(() => env.harness.tree.iniciarConciliacao());
  await env.answerJob(pending());
  await env.fire();
  await env.answerJob({
    imported: false,
    job: {
      competence: "2025-08",
      status: "error",
      last_error: "Não há arquivo financeiro disponível nesta competência de homologação.",
    },
  });
  assert.equal(env.harness.tree.seguindo, false);
  assert.equal(env.timers.size, 0);
  assert.equal(env.harness.tree.relatorio, importado);
  assert.equal(env.harness.tree.relatorio.titles.length, 2);
  assert.equal(env.harness.tree.competence, "2025-08");
  assert.match(env.harness.tree.job.last_error, /homologação/);
  await env.harness.update({ enabled: false });
  await env.harness.update({ enabled: true });
  env.requests.status.at(-1).resolve({
    data: {
      imported: false,
      job: {
        competence: "2025-08",
        status: "error",
        last_error: "Não há arquivo financeiro disponível nesta competência de homologação.",
      },
    },
  });
  await env.harness.settle();
  assert.equal(env.requests.job.length, 2);
  assert.equal(env.timers.size, 0);
  assert.equal(env.harness.tree.relatorio, importado);
  assert.equal(env.harness.tree.relatorio.titles[0].bank_status, "not_checked");
});
