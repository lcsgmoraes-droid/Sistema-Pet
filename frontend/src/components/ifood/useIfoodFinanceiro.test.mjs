import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createControllerHarness } from "../../../scripts/helpers/reactControllerHarness.mjs";

const state = { read_enabled: true, mode: "homologation", can_sync: true, can_edit_costs: true };
const report = (extra = {}) => ({
  mode: "homologation",
  begin_date: "2026-10-23",
  end_date: "2026-10-23",
  imported: true,
  metadata: { source: "ifood_financial_events", retrieved_at: "2026-10-23T12:00:00Z" },
  orders: [
    { order_id: "sale-a", manual_costs: null, contribution: { calculated: false, amount: null } },
  ],
  ...extra,
});
function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}
function setup(enabled = true, periodoSugerido = null) {
  const requests = { status: [], report: [], sync: [], costs: [] };
  const request = (type, payload, config) => {
    const result = deferred();
    requests[type].push({ payload, config, ...result });
    return result.promise;
  };
  const harness = createControllerHarness(
    fileURLToPath(new URL("./useIfoodFinanceiro.js", import.meta.url)),
    {
      props: { enabled, periodoSugerido },
      mocks: new Map([
        [
          "../../api/ifood",
          {
            getIfoodFinanceiroStatus: (config) => request("status", null, config),
            getIfoodFinanceiroRelatorio: (payload, config) => request("report", payload, config),
            sincronizarIfoodFinanceiro: (payload) => request("sync", payload),
            salvarIfoodCustosPedido: (id, payload) => request("costs", { id, ...payload }),
          },
        ],
        ["./ifoodPresentation", { mensagemErroIfood: (_, fallback) => fallback }],
      ]),
      globals: { AbortController, Intl, Date },
    },
  );
  async function load(data = report(), status = state) {
    requests.status.at(-1).resolve({ data: status });
    requests.report.at(-1).resolve({ data });
    await harness.settle();
  }
  return { harness, requests, load };
}

test("aba inativa não faz consulta nem usa dados fictícios", () => {
  const env = setup(false);
  assert.equal(env.harness.tree.relatorio, null);
  assert.equal(env.requests.report.length, 0);
  assert.equal(env.requests.sync.length, 0);
});

test("período sugerido válido consulta somente dados locais e não substitui edição posterior", async () => {
  const env = setup(true, { inicio: "2025-08-01", fim: "2025-08-03" });
  assert.deepEqual(env.requests.report[0].payload, {
    begin_date: "2025-08-01",
    end_date: "2025-08-03",
  });
  assert.equal(env.requests.sync.length, 0);
  await env.load();
  await env.harness.act(() => env.harness.tree.abrirCustos("sale-a"));
  await env.harness.act(() => env.harness.tree.alterarCusto("cmv", 17));
  const periodoEditado = { inicio: "2025-08-05", fim: "2025-08-06" };
  await env.harness.act(() => env.harness.tree.alterarPeriodo(periodoEditado));
  await env.harness.update({
    enabled: false,
    periodoSugerido: { inicio: "2026-01-01", fim: "2026-01-02" },
  });
  await env.harness.update({ enabled: true });
  assert.deepEqual(env.harness.tree.periodo, periodoEditado);
  assert.equal(env.harness.tree.rascunho.cmv, 17);
  assert.equal(env.requests.sync.length, 0);
});

test("períodos editados inválidos e acima de 33 dias não consultam nem sincronizam", async () => {
  const env = setup();
  await env.load();
  const consultas = env.requests.report.length;
  for (const periodo of [
    { inicio: "2025-02-30", fim: "2025-03-01" },
    { inicio: "2025-08-01", fim: "2025-09-03" },
    { inicio: "2025-08-03", fim: "2025-08-01" },
  ]) {
    await env.harness.act(() => env.harness.tree.alterarPeriodo(periodo));
    assert.equal(env.harness.tree.periodoValido, false);
    await env.harness.act(() => env.harness.tree.sincronizar());
    assert.equal(env.requests.report.length, consultas);
    assert.equal(env.requests.sync.length, 0);
  }
});

test("falha inicial não fabrica relatório ou mock de eventos", async () => {
  const env = setup();
  env.requests.status[0].resolve({ data: state });
  env.requests.report[0].reject(new Error("HTTP 502"));
  await env.harness.settle();
  assert.equal(env.harness.tree.relatorio, null);
  assert.match(env.harness.tree.erro, /Não foi possível consultar/);
});

test("falha de atualização mantém dados recebidos e o rascunho manual", async () => {
  const env = setup();
  const original = report();
  await env.load(original);
  await env.harness.act(() => env.harness.tree.abrirCustos("sale-a"));
  await env.harness.act(() => env.harness.tree.alterarCusto("cmv", 19.99));
  await env.harness.act(() => env.harness.tree.atualizar());
  env.requests.status.at(-1).resolve({ data: state });
  env.requests.report.at(-1).reject(new Error("timeout"));
  await env.harness.settle();
  assert.equal(env.harness.tree.relatorio, original);
  assert.equal(env.harness.tree.rascunho.cmv, 19.99);
  assert.equal(env.harness.tree.rascunho.tax, null);
  assert.equal(env.harness.tree.pedido, "sale-a");
});

test("resposta antiga e retorno à aba não sobrescrevem período e rascunho", async () => {
  const env = setup();
  const first = env.requests.report[0];
  await env.harness.act(() =>
    env.harness.tree.alterarPeriodo({ inicio: "2026-10-01", fim: "2026-10-02" }),
  );
  assert.equal(first.config.signal.aborted, true);
  await env.load(report({ begin_date: "2026-10-01", end_date: "2026-10-02" }));
  first.resolve({ data: report({ orders: [] }) });
  env.requests.status[0].resolve({ data: state });
  await env.harness.settle();
  assert.equal(env.harness.tree.relatorio.begin_date, "2026-10-01");
  await env.harness.act(() => env.harness.tree.abrirCustos("sale-a"));
  await env.harness.act(() => env.harness.tree.alterarCusto("source_note", "Documento conferido"));
  await env.harness.update({ enabled: false });
  await env.harness.update({ enabled: true });
  assert.equal(env.harness.tree.periodo.inicio, "2026-10-01");
  assert.equal(env.harness.tree.rascunho.source_note, "Documento conferido");
});

test("fonte obrigatória e zero explícito distinto de custo desconhecido", async () => {
  const env = setup();
  await env.load();
  await env.harness.act(() => env.harness.tree.abrirCustos("sale-a"));
  await env.harness.act(() => env.harness.tree.salvarCustos());
  assert.equal(env.requests.costs.length, 0);
  await env.harness.act(() =>
    env.harness.tree.alterarCusto("source_note", "  Conferido em documento  "),
  );
  await env.harness.act(() => env.harness.tree.alterarCusto("tax", 0));
  let saving;
  await env.harness.act(() => {
    saving = env.harness.tree.salvarCustos();
  });
  const saved = env.requests.costs[0];
  assert.equal(saved.payload.revenue, null);
  assert.equal(saved.payload.cmv, null);
  assert.equal(saved.payload.tax, 0);
  assert.equal(saved.payload.source_note, "Conferido em documento");
  saved.reject(new Error("502"));
  await saving;
  await env.harness.settle();
  assert.equal(env.harness.tree.rascunho.tax, 0);
  assert.equal(env.harness.tree.pedido, "sale-a");
  assert.match(env.harness.tree.erroCustos, /rascunho foi mantido/);
});

test("versão salva é preservada mesmo se releitura falhar, sem calcular contribuição na tela", async () => {
  const env = setup();
  await env.load();
  await env.harness.act(() => env.harness.tree.abrirCustos("sale-a"));
  await env.harness.act(() => env.harness.tree.alterarCusto("source_note", "Documento conferido"));
  let saving;
  await env.harness.act(() => {
    saving = env.harness.tree.salvarCustos();
  });
  const result = {
    order_id: "sale-a",
    manual_costs: { version: 2 },
    contribution: { calculated: true, amount: "4.81", percent: "7.01" },
    pending: [],
  };
  env.requests.costs[0].resolve({ data: result });
  await saving;
  await env.harness.settle();
  env.requests.status.at(-1).resolve({ data: state });
  env.requests.report.at(-1).reject(new Error("502"));
  await env.harness.settle();
  assert.deepEqual(env.harness.tree.relatorio.orders[0].contribution, result.contribution);
  assert.equal(env.harness.tree.relatorio.orders[0].manual_costs.version, 2);
  assert.equal(env.harness.tree.pedido, null);
});

test("capacidades do servidor bloqueiam sync mas permitem custos com Financial desligado", async () => {
  const env = setup();
  await env.load(report(), { ...state, read_enabled: false, can_sync: false });
  await env.harness.act(() => env.harness.tree.sincronizar());
  assert.equal(env.requests.sync.length, 0);
  await env.harness.act(() => env.harness.tree.abrirCustos("sale-a"));
  assert.equal(env.harness.tree.pedido, "sale-a");
});

test("falha de status retira capacidades e sincronização falha sem apagar custos", async () => {
  const env = setup();
  await env.load();
  await env.harness.act(() => env.harness.tree.abrirCustos("sale-a"));
  await env.harness.act(() => env.harness.tree.alterarCusto("cmv", 7));
  let sync;
  await env.harness.act(() => {
    sync = env.harness.tree.sincronizar();
  });
  env.requests.sync[0].reject(new Error("429"));
  await sync;
  await env.harness.settle();
  env.requests.status.at(-1).reject(new Error("403"));
  env.requests.report.at(-1).resolve({ data: report() });
  await env.harness.settle();
  assert.equal(env.harness.tree.status, null);
  assert.equal(env.harness.tree.rascunho.cmv, 7);
});
