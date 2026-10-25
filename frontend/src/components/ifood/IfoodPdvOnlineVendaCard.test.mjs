import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import * as fiscalStatus from "../../utils/pdvFiscalStatus.js";
import {
  createControllerHarness,
  elements,
  elementText,
} from "../../../scripts/helpers/reactControllerHarness.mjs";

const bridge = {
  enabled: true,
  eligible: false,
  payment_mode: "online",
  can_finalize_online: true,
  status: "reserved",
  sale_id: 42,
  ifood_order_id: "test-order",
};
function prepare(summary = bridge, post, reload) {
  const calls = [],
    updates = [];
  const harness = createControllerHarness(
    fileURLToPath(new URL("./IfoodPdvOnlineVendaCard.jsx", import.meta.url)),
    {
      props: {
        venda: { id: 42, canal: "ifood", ifood_pdv_pilot: summary },
        onUpdated: async (saleId) => {
          updates.push(saleId);
          await reload?.(saleId);
        },
      },
      mocks: new Map([
        ["../api", { __esModule: true, default: {} }],
        [
          "../../api",
          {
            __esModule: true,
            default: {
              post: (url) => {
                calls.push(url);
                return post ? post(url) : Promise.resolve({ data: {} });
              },
            },
          },
        ],
        ["./IfoodPedidoPdvPilot", { __esModule: true, default: "IfoodPedidoPdvPilot" }],
        ["./IfoodPdvOnlineResumo", { __esModule: true, default: "IfoodPdvOnlineResumo" }],
      ]),
    },
  );
  return { harness, calls, updates };
}

test("acao do PDV conclui online uma vez no duplo clique, sem endpoint de pagamento", async () => {
  let resolve;
  const response = new Promise((done) => {
    resolve = done;
  });
  const env = prepare(bridge, () => response);
  const card = elements(env.harness.tree).find((node) => node.type === "IfoodPedidoPdvPilot");
  const first = card.props.onFinalizeOnline();
  const second = card.props.onFinalizeOnline();
  assert.deepEqual(env.calls, [
    "/integracoes/ifood/pedidos/test-order/piloto-pdv/finalizar-online",
  ]);
  assert.deepEqual(env.updates, []);
  resolve({ data: { pdv_bridge: { status: "sold", stock_decreased: true } } });
  await env.harness.act(() => Promise.all([first, second]));
  assert.deepEqual(env.updates, [42]);
  assert.match(elementText(env.harness.tree), /repasse a conciliar/);
});

test("piloto desativado nao permite cobranca manual e bloqueio servidor nao finge sucesso", async () => {
  const disabled = prepare({
    enabled: false,
    payment_mode: "unknown",
    reason: "Piloto DEV indisponível",
  });
  assert.match(elementText(disabled.harness.tree), /cobrança manual.*bloqueada/);
  assert.deepEqual(disabled.calls, []);
  const env = prepare(bridge, async () => {
    throw { response: { data: { detail: "Sacola mudou; confira o pedido." } } };
  });
  const card = elements(env.harness.tree).find((node) => node.type === "IfoodPedidoPdvPilot");
  await env.harness.act(() => card.props.onFinalizeOnline());
  assert.match(elementText(env.harness.tree), /Sacola mudou/);
  assert.deepEqual(env.updates, []);
});

test("conclusao passa ID real ao carregador do PDV e relê venda finalizada e reserva encerrada", async () => {
  const requests = [],
    alerts = [],
    sales = [];
  const finalized = {
    id: 42,
    status: "finalizada",
    canal: "ifood",
    subtotal: 65,
    total: 73.9,
    tem_entrega: true,
    entrega: { taxa_entrega_total: 8.9 },
    itens: [{ produto_id: 1, quantidade: 1, preco_unitario: 65, subtotal: 65 }],
    ifood_pdv_pilot: {
      ...bridge,
      status: "sold",
      can_finalize_online: false,
      stock_decreased: true,
      reserved_quantity: 0,
    },
  };
  const loader = createControllerHarness(
    fileURLToPath(new URL("../../hooks/usePDVVendaCarregamento.js", import.meta.url)),
    {
      exportName: "usePDVVendaCarregamento",
      props: {
        setVendaAtual: (sale) => sales.push(sale),
        setLoading() {},
        setModoVisualizacao() {},
        sincronizarComissaoDaVenda: async () => {},
        sincronizarEntregadorDaVenda: async () => {},
      },
      mocks: new Map([
        [
          "../api",
          {
            __esModule: true,
            default: {
              get: async (url) => {
                requests.push(url);
                return {
                  data: {
                    pagamentos: [{ forma_pagamento: "iFood online", valor: 73.9 }],
                    total_recebido: 73.9,
                  },
                };
              },
            },
          },
        ],
        ["../api/clientes", {}],
        [
          "../api/vendas",
          {
            buscarVendaComSituacaoFiscal: async (saleId) => {
              assert.equal(saleId, 42);
              requests.push(`/vendas/${saleId}`);
              return finalized;
            },
          },
        ],
        ["../utils/debug", { debugLog() {} }],
        ["../utils/pdvFiscalStatus", fiscalStatus],
        ["../services/corepetDialog", {}],
      ]),
      globals: { alert: (message) => alerts.push(message), console: { error() {} } },
    },
  );
  const env = prepare(
    bridge,
    async () => ({ data: { pdv_bridge: finalized.ifood_pdv_pilot } }),
    loader.tree.carregarVendaEspecifica,
  );
  const card = elements(env.harness.tree).find((node) => node.type === "IfoodPedidoPdvPilot");
  await env.harness.act(() => card.props.onFinalizeOnline());
  assert.deepEqual(env.calls, [
    "/integracoes/ifood/pedidos/test-order/piloto-pdv/finalizar-online",
  ]);
  assert.deepEqual(requests, ["/vendas/42", "/vendas/42/pagamentos"]);
  assert.deepEqual(alerts, []);
  assert.equal(sales.length, 1);
  assert.equal(sales[0].status, "finalizada");
  assert.equal(sales[0].ifood_pdv_pilot.status, "sold");
  assert.equal(sales[0].ifood_pdv_pilot.reserved_quantity, 0);
  assert.equal(sales[0].ifood_pdv_pilot.stock_decreased, true);
  await env.harness.update({ venda: sales[0] });
  const refreshed = elements(env.harness.tree).find((node) => node.type === "IfoodPedidoPdvPilot");
  assert.equal(refreshed.props.bridge.can_finalize_online, false);
  assert.equal(refreshed.props.bridge.stock_decreased, true);
});

function financialCard(autoRefresh = true) {
  const requests = [];
  const updates = [];
  let refresh;
  let enabled;
  const venda = {
    id: 42,
    canal: "ifood",
    itens: [{ produto_id: 1, quantidade: 1, preco_unitario: 65 }],
    cliente: { id: 2, nome: "Cliente em edição" },
    total: 73.9,
    observacoes: "Rascunho que deve permanecer",
    ifood_pdv_pilot: {
      ...bridge,
      receivable: { net_amount: null, status: "awaiting_financial" },
      ifood_financial: { fingerprint: "inicial", complete: false },
      ifood_rentabilidade: { lucro: null, rentabilidade_status: "pending_ifood_financial" },
    },
  };
  const harness = createControllerHarness(
    fileURLToPath(new URL("./IfoodPdvOnlineVendaCard.jsx", import.meta.url)),
    {
      props: { venda, autoRefresh, onUpdated: (id) => updates.push(id) },
      globals: { AbortController },
      mocks: new Map([
        ["../../api", { __esModule: true, default: {} }],
        [
          "../api",
          {
            __esModule: true,
            default: {
              get(url, config) {
                return new Promise((resolve, reject) =>
                  requests.push({ url, config, resolve, reject }),
                );
              },
            },
          },
        ],
        [
          "./useIfoodFinancialReportRefresh.js",
          {
            __esModule: true,
            default(options) {
              refresh = options.refresh;
              enabled = options.enabled;
            },
          },
        ],
        ["./IfoodPedidoPdvPilot", { __esModule: true, default: "IfoodPedidoPdvPilot" }],
        ["./IfoodPdvOnlineResumo", { __esModule: true, default: "IfoodPdvOnlineResumo" }],
      ]),
    },
  );
  return {
    harness,
    venda,
    requests,
    updates,
    refresh: () => refresh(),
    get enabled() {
      return enabled;
    },
    get bridge() {
      return elements(harness.tree).find((node) => node.type === "IfoodPedidoPdvPilot").props
        .bridge;
    },
  };
}

function responseFinancial(id, fingerprint = "financial-completo") {
  return {
    data: {
      id,
      itens: [{ produto_id: 999, quantidade: 100 }],
      cliente: { id: 999 },
      total: 99999,
      observacoes: "Não reaplicar este campo",
      ifood_pdv_pilot: {
        sale_id: id,
        status: "não reaplicar operação",
        can_finalize_online: false,
        stock_decreased: true,
        receivable: { net_amount: 999, status: "não reaplicar repasse" },
        ifood_financial: { fingerprint, complete: true, fee_total: 6.5 },
        ifood_rentabilidade: {
          lucro: 18.5,
          margem_sobre_venda: 28.46,
          rentabilidade_status: "complete",
        },
      },
    },
  };
}

test("PDV atualiza apenas Financial e margem de apresentação sem reaplicar formulário ou operação", async () => {
  const env = financialCard();
  const original = structuredClone(env.venda);
  const read = env.refresh();
  assert.equal(env.requests[0].url, "/vendas/42");
  env.requests[0].resolve(responseFinancial(42));
  await env.harness.act(() => read);
  assert.equal(env.bridge.ifood_financial.fingerprint, "financial-completo");
  assert.equal(env.bridge.ifood_rentabilidade.lucro, 18.5);
  assert.equal(env.bridge.status, original.ifood_pdv_pilot.status);
  assert.equal(env.bridge.can_finalize_online, true);
  assert.deepEqual(env.bridge.receivable, original.ifood_pdv_pilot.receivable);
  assert.deepEqual(env.venda, original);
  assert.deepEqual(env.updates, []);
  assert.equal(env.requests.length, 1);
  env.harness.unmount();
});

test("leitura financeira é opt-in e recusa bridge que não pertence à venda exibida", async () => {
  const env = financialCard(false);
  assert.equal(env.enabled, false);
  await env.harness.act(() => env.refresh());
  assert.equal(env.requests.length, 0);
  await env.harness.update({ autoRefresh: true, venda: { ...env.venda, id: 99 } });
  assert.equal(env.enabled, false);
  await env.harness.act(() => env.refresh());
  assert.equal(env.requests.length, 0);
  env.harness.unmount();
});

test("trocas entre dez vendas cancelam leituras antigas e respostas fora de ordem não trocam as taxas atuais", async () => {
  const env = financialCard();
  const reads = [];
  for (let id = 1; id <= 10; id++) {
    await env.harness.update({
      venda: { ...env.venda, id, ifood_pdv_pilot: { ...env.venda.ifood_pdv_pilot, sale_id: id } },
    });
    reads.push(env.refresh());
  }
  assert.equal(env.requests.length, 10);
  assert.ok(env.requests.slice(0, 9).every((request) => request.config.signal.aborted));
  env.requests[9].resolve(responseFinancial(10, "venda10"));
  await env.harness.act(() => reads[9]);
  for (let index = 8; index >= 0; index--) {
    env.requests[index].resolve(responseFinancial(index + 1, `venda${index + 1}`));
    await env.harness.act(() => reads[index]);
  }
  assert.equal(env.bridge.sale_id, 10);
  assert.equal(env.bridge.ifood_financial.fingerprint, "venda10");
  assert.deepEqual(env.updates, []);
  env.harness.unmount();
});

test("revisão nova, retorno incorreto e desmontagem invalidam respostas anteriores", async () => {
  const env = financialCard();
  const old = env.refresh();
  const newSale = {
    ...env.venda,
    ifood_pdv_pilot: {
      ...env.venda.ifood_pdv_pilot,
      ifood_financial: { fingerprint: "revisao-nova", complete: false },
    },
  };
  await env.harness.update({ venda: newSale });
  assert.equal(env.requests[0].config.signal.aborted, true);
  env.requests[0].resolve(responseFinancial(42, "revisao-antiga"));
  await env.harness.act(() => old);
  assert.equal(env.bridge.ifood_financial.fingerprint, "revisao-nova");
  const incorrect = env.refresh();
  const different = responseFinancial(42);
  different.data.ifood_pdv_pilot.sale_id = 99;
  env.requests[1].resolve(different);
  await env.harness.act(() => incorrect);
  assert.equal(env.bridge.ifood_financial.fingerprint, "revisao-nova");
  const afterUnmount = env.refresh();
  env.harness.unmount();
  assert.equal(env.requests[2].config.signal.aborted, true);
  env.requests[2].resolve(responseFinancial(42, "após-desmontar"));
  await afterUnmount;
  assert.equal(env.bridge.ifood_financial.fingerprint, "revisao-nova");
  assert.deepEqual(env.updates, []);
});
