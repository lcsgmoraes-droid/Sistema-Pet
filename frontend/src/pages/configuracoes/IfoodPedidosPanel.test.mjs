import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elements,
  elementText,
} from "../../../scripts/helpers/reactControllerHarness.mjs";

const file = fileURLToPath(new URL("./IfoodPedidosPanel.jsx", import.meta.url));
const bridge = { enabled: true, eligible: true, status: "not_imported", sale_id: null };
const order = { ifood_order_id: "test-order-1", display_id: "1234", pdv_bridge: bridge };

function pending() {
  let resolve;
  const promise = new Promise((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

function prepare({ enabled = true, initial, detail = order, importResponse } = {}) {
  const calls = [];
  const messages = [];
  const first = initial || Promise.resolve({ data: { orders: [order] } });
  let listCalls = 0;
  let currentDetail = detail;
  const mocks = new Map([
    ["lucide-react", {}],
    [
      "../../services/api",
      {
        api: {
          get: async (url) => {
            calls.push(["GET", url]);
            if (url.endsWith("/pedidos")) {
              listCalls++;
              return listCalls === 1 ? first : { data: { orders: [currentDetail] } };
            }
            return { data: currentDetail };
          },
          post: async (url) => {
            calls.push(["POST", url]);
            return importResponse || { data: currentDetail };
          },
        },
      },
    ],
    ["../../services/corepetDialog", { confirmarCorePet: async () => true }],
    [
      "../../components/v2/BotaoInteracao/BotaoInteracao",
      { __esModule: true, default: "BotaoInteracao" },
    ],
    [
      "../../components/v2/InputQuantidade/InputQuantidade",
      { __esModule: true, default: "InputQuantidade" },
    ],
    [
      "../../components/ifood/IfoodPedidoPdvPilot",
      {
        __esModule: true,
        default: "IfoodPedidoPdvPilot",
        canImportIfoodPdvPilot: (value) =>
          Boolean(
            value?.enabled &&
            value?.eligible &&
            value?.status === "not_imported" &&
            !value?.sale_id,
          ),
      },
    ],
  ]);
  const harness = createControllerHarness(file, {
    mocks,
    props: { enabled, onMessage: (...args) => messages.push(args) },
  });
  return {
    harness,
    calls,
    messages,
    mocks,
    setDetail: (value) => {
      currentDetail = value;
    },
  };
}

function orderDetailsElement(harness) {
  return elements(harness.tree).find((item) => typeof item.type === "function");
}

const checkout = {
  items_total: 65,
  delivery_fee: 8.9,
  ifood_service_fee: 1.99,
  operational_total: 73.9,
  customer_total: 75.89,
};

async function renderListAndDetails(value) {
  const env = prepare({ initial: Promise.resolve({ data: { orders: [value] } }), detail: value });
  await env.harness.settle();
  const listText = elementText(env.harness.tree);
  const details = await selectOrder(env);
  const detailHarness = createControllerHarness(file, {
    exportName: "OrderDetails",
    mocks: env.mocks,
    props: details.props,
  });
  await detailHarness.settle();
  return [listText, elementText(detailHarness.tree)];
}

test("lista e cabecalho online usam total do consumidor comprovado sem modificar total legado", async () => {
  const value = {
    ...order,
    total: 65,
    pdv_bridge: { ...bridge, payment_mode: "online", checkout },
  };
  const before = structuredClone(value);
  for (const text of await renderListAndDetails(value)) {
    assert.match(text, /Total do consumidor/);
    assert.match(text, /75,89/);
    assert.doesNotMatch(text, /65,00|73,90/);
  }
  assert.deepEqual(value, before);
});

test("checkout online invalido nao apresenta subtotal legado como total; offline conserva exibição", async () => {
  for (const invalid of [
    undefined,
    {},
    { ...checkout, customer_total: null },
    { ...checkout, customer_total: "" },
    { ...checkout, customer_total: true },
    { ...checkout, customer_total: -1 },
    { ...checkout, customer_total: 65 },
    { ...checkout, operational_total: 65 },
  ]) {
    for (const text of await renderListAndDetails({
      ...order,
      total: 65,
      pdv_bridge: { ...bridge, payment_mode: "online", checkout: invalid },
    })) {
      assert.match(text, /Total do consumidor/);
      assert.match(text, /Não informado/);
      assert.doesNotMatch(text, /65,00|75,89|0,00/);
    }
  }
  for (const summary of [undefined, { ...bridge, payment_mode: "offline", checkout }]) {
    for (const text of await renderListAndDetails({ ...order, total: 65, pdv_bridge: summary })) {
      assert.match(text, /65,00/);
      assert.doesNotMatch(text, /Total do consumidor|75,89/);
    }
  }
});

test("conclusao online local nao depende de operacoes externas e trava o duplo clique", async () => {
  const response = pending();
  const online = {
    ...bridge,
    eligible: false,
    status: "reserved",
    sale_id: 42,
    ifood_order_id: order.ifood_order_id,
    payment_mode: "online",
    can_finalize_online: true,
  };
  const env = prepare({
    enabled: false,
    detail: { ...order, pdv_bridge: online },
    importResponse: response.promise,
  });
  const details = await selectOrder(env);
  const first = details.props.onFinalizeOnlinePdv();
  const second = details.props.onFinalizeOnlinePdv();
  assert.deepEqual(
    env.calls.filter(([method]) => method === "POST"),
    [["POST", "/integracoes/ifood/pedidos/test-order-1/piloto-pdv/finalizar-online"]],
  );
  response.resolve({
    data: {
      ...order,
      pdv_bridge: { ...online, status: "sold", can_finalize_online: false, stock_decreased: true },
    },
  });
  await env.harness.act(() => Promise.all([first, second]));
  assert.equal(orderDetailsElement(env.harness).props.order.pdv_bridge.stock_decreased, true);
  assert.match(env.messages[0][1], /Repasse do iFood a conciliar/);
  assert.equal(
    env.calls.some(([, url]) => /\/vendas\/|pagamento|processar-eventos/.test(url)),
    false,
  );
});

test("conclusao online sem capacidade ou ja vendida nao chama endpoint", async () => {
  for (const patch of [
    { enabled: false },
    { can_finalize_online: false },
    { status: "sold" },
    { payment_mode: "offline" },
  ]) {
    const env = prepare({
      detail: {
        ...order,
        pdv_bridge: {
          ...bridge,
          ifood_order_id: order.ifood_order_id,
          status: "reserved",
          sale_id: 42,
          payment_mode: "online",
          can_finalize_online: true,
          ...patch,
        },
      },
    });
    const details = await selectOrder(env);
    await env.harness.act(() => details.props.onFinalizeOnlinePdv());
    assert.equal(
      env.calls.some(([method]) => method === "POST"),
      false,
    );
  }
});

test("importar online apenas reserva e orienta a conclusao sem cobrar automaticamente", async () => {
  const env = prepare({
    enabled: false,
    detail: { ...order, pdv_bridge: { ...bridge, payment_mode: "online" } },
    importResponse: {
      data: {
        ...order,
        pdv_bridge: { ...bridge, payment_mode: "online", status: "reserved", sale_id: 42 },
      },
    },
  });
  const details = await selectOrder(env);
  await env.harness.act(() => details.props.onImportPdv());
  assert.deepEqual(
    env.calls.filter(([method]) => method === "POST"),
    [["POST", "/integracoes/ifood/pedidos/test-order-1/piloto-pdv/importar"]],
  );
  assert.match(env.messages[0][1], /sem nova cobrança/);
});

async function selectOrder(env) {
  await env.harness.settle();
  const button = elements(env.harness.tree).find(
    (item) => item.type === "BotaoInteracao" && elementText(item).startsWith("Ver pedido #"),
  );
  await env.harness.act(() => button.props.onClick());
  return orderDetailsElement(env.harness);
}

test("carregamento inicial nao exibe vazio antes da resposta", async () => {
  const request = pending();
  const env = prepare({ initial: request.promise });
  assert.match(elementText(env.harness.tree), /Carregando pedidos/);
  assert.doesNotMatch(elementText(env.harness.tree), /Nenhum pedido de teste recebido/);
  request.resolve({ data: { orders: [] } });
  await env.harness.settle();
  assert.match(elementText(env.harness.tree), /Nenhum pedido de teste recebido/);
});

test("importacao manual chama somente endpoint DEV uma vez durante duplo clique", async () => {
  const response = pending();
  const env = prepare({ importResponse: response.promise });
  const details = await selectOrder(env);
  assert.ok(details, "detalhe selecionado carregado");
  const first = details.props.onImportPdv();
  const second = details.props.onImportPdv();
  assert.deepEqual(
    env.calls.filter(([method]) => method === "POST"),
    [["POST", "/integracoes/ifood/pedidos/test-order-1/piloto-pdv/importar"]],
  );
  response.resolve({
    data: { ...order, pdv_bridge: { ...bridge, status: "reserved", sale_id: 42 } },
  });
  await env.harness.act(() => Promise.all([first, second]));
  assert.match(env.messages[0][1], /baixa ocorre ao finalizar a venda no PDV/);
  assert.equal(
    env.calls.some(([, url]) => /finalizar|pagamento/.test(url)),
    false,
  );
});

test("pedido fora do piloto nao chama importacao mesmo invocando o handler", async () => {
  const env = prepare({ detail: { ...order, pdv_bridge: { ...bridge, eligible: false } } });
  const details = await selectOrder(env);
  await env.harness.act(() => details.props.onImportPdv());
  assert.equal(
    env.calls.some(([method]) => method === "POST"),
    false,
  );
});

test("ponte local elegivel importa com operacoes externas desligadas sem liberar polling ou picking", async () => {
  const env = prepare({
    enabled: false,
    detail: {
      ...order,
      payload: { bag: { items: [{ uniqueId: "item-1", name: "Teste", quantity: 1 }] } },
    },
  });
  const details = await selectOrder(env);
  const poll = elements(env.harness.tree).find(
    (item) => item.type === "BotaoInteracao" && elementText(item) === "Buscar eventos agora",
  );
  assert.equal(poll.props.disabled, true);
  assert.equal(details.props.actionsEnabled, false);
  const detailHarness = createControllerHarness(file, {
    mocks: env.mocks,
    exportName: "OrderDetails",
    props: details.props,
  });
  await detailHarness.settle();
  assert.equal(
    elements(detailHarness.tree).find((item) => item.type === "InputQuantidade").props.disabled,
    true,
  );
  assert.ok(
    elements(detailHarness.tree)
      .filter((item) => item.type === "BotaoInteracao")
      .every((item) => item.props.disabled === true),
  );
  const pilot = elements(detailHarness.tree).find((item) => item.type === "IfoodPedidoPdvPilot");
  assert.equal(pilot.props.bridge.eligible, true);
  assert.equal(pilot.props.busy, false);
  assert.equal(pilot.props.disabled, undefined);
  await env.harness.act(() => poll.props.onClick());
  await env.harness.act(() => details.props.onAction("iniciar-separacao"));
  await env.harness.act(() => details.props.onItemAction("update", "item-1", { quantity: 1 }));
  assert.equal(
    env.calls.some(([method]) => method === "POST"),
    false,
  );
  await env.harness.act(() => details.props.onImportPdv());
  assert.deepEqual(
    env.calls.filter(([method]) => method === "POST"),
    [["POST", "/integracoes/ifood/pedidos/test-order-1/piloto-pdv/importar"]],
  );
});

test("reserva existente bloqueia a edicao de quantidade e remocao no picking", async () => {
  const env = prepare();
  const harness = createControllerHarness(file, {
    mocks: env.mocks,
    exportName: "OrderDetails",
    props: {
      order: {
        ...order,
        pdv_bridge: { ...bridge, sale_id: 42, status: "reserved" },
        payload: { bag: { items: [{ uniqueId: "item-1", name: "Teste", quantity: 1 }] } },
      },
      actionsEnabled: true,
      onAction() {},
      onItemAction() {},
      onImportPdv() {},
      action: null,
    },
  });
  await harness.settle();
  const input = elements(harness.tree).find((item) => item.type === "InputQuantidade");
  assert.equal(input.props.disabled, true);
  for (const label of ["Atualizar quantidade", "Marcar indisponível"]) {
    const button = elements(harness.tree).find(
      (item) => item.type === "BotaoInteracao" && elementText(item) === label,
    );
    assert.equal(button.props.disabled, true);
  }
});

test("atualizacao local reflete baixa do PDV sem consultar eventos nem importar novamente", async () => {
  const env = prepare();
  await selectOrder(env);
  env.setDetail({
    ...order,
    pdv_bridge: {
      ...bridge,
      status: "sold",
      sale_id: 42,
      stock_decreased: true,
      reserved_quantity: 0,
    },
  });
  const refresh = elements(env.harness.tree).find(
    (item) => item.type === "BotaoInteracao" && elementText(item) === "Atualizar pedidos",
  );
  await env.harness.act(() => refresh.props.onClick());
  assert.equal(orderDetailsElement(env.harness).props.order.pdv_bridge.status, "sold");
  assert.equal(orderDetailsElement(env.harness).props.order.pdv_bridge.stock_decreased, true);
  assert.equal(
    env.calls.some(([method]) => method === "POST"),
    false,
  );
});
