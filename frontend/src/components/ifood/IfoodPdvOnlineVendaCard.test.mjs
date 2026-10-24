import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
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
function prepare(summary = bridge, post) {
  const calls = [],
    updates = [];
  const harness = createControllerHarness(
    fileURLToPath(new URL("./IfoodPdvOnlineVendaCard.jsx", import.meta.url)),
    {
      props: {
        venda: { id: 42, canal: "ifood", ifood_pdv_pilot: summary },
        onUpdated: () => updates.push(42),
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
