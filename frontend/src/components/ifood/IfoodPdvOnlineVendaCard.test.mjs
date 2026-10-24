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
