import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";
import ts from "typescript";

const controllerPath = fileURLToPath(new URL("./ModalDevolucao.jsx", import.meta.url));

// Exercise the actual controller and handlers without a DOM or additional test dependencies.
// Each harness owns its state, effects and API mocks; JSX remains an inspectable element tree.
function createHarness({
  caixaId = 30,
  beneficio = true,
  cliente = true,
  saldo = 2,
  postRegistro,
  postPrevia,
} = {}) {
  const venda = {
    id: 100,
    cliente_id: cliente ? 200 : null,
    cliente: cliente ? { id: 200, nome: "Cliente" } : null,
    itens: [{ id: 1, quantidade: 2, preco_unitario: 38.9, tipo_produto: "PRODUTO" }],
    pagamentos: beneficio ? [{ forma_pagamento: "cashback", valor: 10 }] : [],
  };
  const calls = [];
  const confirmations = [];
  const successes = [];
  const slots = [];
  let index = 0;
  let dirty = false;
  let effects = [];
  let tree;
  let saldoAtual = saldo;
  let caixaAtual = null;
  let previewCount = 0;
  let registrationCount = 0;
  const Sections = () => null;
  const AbrirCaixa = () => null;
  const sameDependencies = (previous, next) =>
    previous &&
    next &&
    previous.length === next.length &&
    previous.every((value, i) => Object.is(value, next[i]));
  const hooks = {
    useState(initial) {
      const slot = index++;
      if (!slots[slot])
        slots[slot] = { value: typeof initial === "function" ? initial() : initial };
      return [
        slots[slot].value,
        (update) => {
          const value = typeof update === "function" ? update(slots[slot].value) : update;
          if (!Object.is(value, slots[slot].value)) {
            slots[slot].value = value;
            dirty = true;
          }
        },
      ];
    },
    useRef(initial) {
      const slot = index++;
      if (!slots[slot]) slots[slot] = { current: initial };
      return slots[slot];
    },
    useEffect(effect, dependencies) {
      const slot = index++;
      if (!sameDependencies(slots[slot]?.dependencies, dependencies)) {
        slots[slot]?.cleanup?.();
        slots[slot] = { dependencies };
        effects.push(() => {
          slots[slot].cleanup = effect();
        });
      }
    },
  };
  const api = {
    async get(url) {
      calls.push({ method: "get", url });
      if (url === "/vendas") return { data: { vendas: [venda] } };
      if (url === "/vendas/100") return { data: venda };
      if (url === "/vendas/100/devolucao/saldos") {
        return {
          data: {
            itens: [
              {
                item_id: 1,
                quantidade_devolvida: 2 - saldoAtual,
                quantidade_disponivel: saldoAtual,
              },
            ],
          },
        };
      }
      throw new Error(`Unexpected GET ${url}`);
    },
    async post(url, payload) {
      calls.push({ method: "post", url, payload: structuredClone(payload) });
      if (url.endsWith("/previa")) {
        previewCount += 1;
        if (postPrevia) return postPrevia(payload, previewCount);
        return {
          data: {
            valor_total_devolucao: 38.9,
            restituicao: {
              cashback: beneficio ? 10 : 0,
              credito_cliente: 0,
              valor_restante: beneficio ? 28.9 : 38.9,
              cashback_expirado: 0,
            },
          },
        };
      }
      if (url === "/vendas/100/devolucao") {
        registrationCount += 1;
        if (postRegistro) return postRegistro(payload, registrationCount);
        return { data: { success: true } };
      }
      throw new Error(`Unexpected POST ${url}`);
    },
  };
  const jsx = (type, props) => ({ type, props });
  const mocks = new Map([
    ["react", hooks],
    ["react/jsx-runtime", { jsx, jsxs: jsx, Fragment: "fragment" }],
    ["lucide-react", { X: "icon", RotateCcw: "icon" }],
    ["../api", { __esModule: true, default: api }],
    [
      "../api/caixa",
      {
        obterCaixaAberto: async () => {
          calls.push({ method: "caixa" });
          return caixaAtual;
        },
      },
    ],
    [
      "../services/corepetDialog",
      {
        confirmarCorePet: async (options) => {
          confirmations.push(options);
          return true;
        },
      },
    ],
    ["./ModalAbrirCaixa", { __esModule: true, default: AbrirCaixa }],
    ["./devolucao/ModalDevolucaoSections", { __esModule: true, default: Sections }],
  ]);
  const cache = new Map();
  function loadModule(path) {
    if (cache.has(path)) return cache.get(path);
    const source = readFileSync(path, "utf8");
    const { outputText, diagnostics } = ts.transpileModule(source, {
      fileName: path,
      reportDiagnostics: true,
      compilerOptions: {
        target: ts.ScriptTarget.ES2022,
        module: ts.ModuleKind.CommonJS,
        jsx: ts.JsxEmit.ReactJSX,
        esModuleInterop: true,
      },
    });
    assert.equal(
      diagnostics?.filter((item) => item.category === ts.DiagnosticCategory.Error).length,
      0,
    );
    const module = { exports: {} };
    cache.set(path, module.exports);
    const requireMock = (specifier) => {
      if (mocks.has(specifier)) return mocks.get(specifier);
      if (specifier.startsWith(".")) {
        const target = resolve(dirname(path), specifier);
        return loadModule(/\.[cm]?[jt]sx?$/.test(target) ? target : `${target}.js`);
      }
      throw new Error(`Unexpected module ${specifier}`);
    };
    new Function("require", "module", "exports", "alert", "console", outputText)(
      requireMock,
      module,
      module.exports,
      () => {},
      { error() {} },
    );
    return module.exports;
  }
  const Controller = loadModule(controllerPath).default;
  function render() {
    index = 0;
    dirty = false;
    effects = [];
    tree = Controller({
      caixaId,
      vendaInicial: venda,
      onClose() {},
      onSucesso: (result) => successes.push(result),
    });
    effects.forEach((effect) => effect());
  }
  function findElement(node, type) {
    if (!node || typeof node !== "object") return null;
    if (node.type === type) return node;
    const children = Array.isArray(node.props?.children)
      ? node.props.children
      : [node.props?.children];
    return children.map((child) => findElement(child, type)).find(Boolean) || null;
  }
  async function settle() {
    for (let pass = 0; pass < 20; pass += 1) {
      await Promise.resolve();
      if (dirty) render();
    }
  }
  render();
  return {
    calls,
    confirmations,
    successes,
    get sections() {
      return findElement(tree, Sections).props;
    },
    get abrirCaixa() {
      return findElement(tree, AbrirCaixa)?.props;
    },
    setCaixa(value) {
      caixaAtual = value;
    },
    setSaldo(value) {
      saldoAtual = value;
    },
    settle,
    async act(callback) {
      const result = callback();
      await settle();
      await result;
      await settle();
    },
  };
}

async function selectItem(harness) {
  await harness.settle();
  await harness.act(() => harness.sections.toggleItem(1));
  await harness.act(() => harness.sections.handleQuantidadeChange(1, "1"));
  await harness.act(() => harness.sections.setMotivo("Troca solicitada pelo cliente"));
}

test("cashback recovery keeps the selection and sends restitution to its original balance", async () => {
  const harness = createHarness();
  await selectItem(harness);
  await harness.act(() => harness.sections.handleConfirmar());
  assert.equal(harness.calls.filter((call) => call.method === "post").length, 0);
  assert.ok(
    harness.sections.recuperacao.acoes.some((action) => action.id === "devolver_na_origem"),
  );
  await harness.act(() => harness.sections.onRecuperar("devolver_na_origem"));
  assert.equal(harness.sections.itensSelecionados[1], true);
  assert.equal(harness.sections.quantidades[1], 1);
  assert.equal(harness.sections.motivo, "Troca solicitada pelo cliente");
  await harness.act(() => harness.sections.handleConfirmar());
  const posts = harness.calls.filter((call) => call.method === "post");
  assert.equal(posts.length, 2);
  assert.equal(posts[0].payload.devolver_na_origem, true);
  assert.deepEqual(posts[1].payload.itens, [{ item_id: 1, quantidade: 1 }]);
  assert.equal(posts[1].payload.devolver_na_origem, true);
  assert.equal(posts[1].payload.valor_previsto, 38.9);
  assert.deepEqual(posts[1].payload.restituicao_prevista, {
    cashback: 10,
    credito_cliente: 0,
    valor_restante: 28.9,
    cashback_expirado: 0,
  });
  assert.match(posts[1].payload.chave_operacao, /^[0-9a-f-]{36}$/);
  assert.equal(harness.confirmations.length, 1);
  assert.equal(harness.successes.length, 1);
});

test("retry after an uncertain response reuses the operation key without another preview", async () => {
  const harness = createHarness({
    beneficio: false,
    postRegistro: (_payload, count) => {
      if (count === 1) throw new Error("Network Error");
      return { data: { success: true } };
    },
  });
  await selectItem(harness);
  await harness.act(() => harness.sections.handleConfirmar());
  assert.equal(harness.successes.length, 0);
  assert.equal(
    harness.sections.recuperacao.acoes.some((action) => action.id === "atualizar_saldos"),
    false,
  );
  await harness.act(() => harness.sections.onRecuperar("tentar_novamente"));
  const records = harness.calls.filter((call) => call.url === "/vendas/100/devolucao");
  assert.equal(records.length, 2);
  assert.deepEqual(records[0].payload, records[1].payload);
  assert.equal(harness.calls.filter((call) => call.url?.endsWith("/previa")).length, 1);
  assert.equal(harness.confirmations.length, 1);
  assert.equal(harness.successes.length, 1);
});

test("editing the draft after an uncertain response cannot replace the pending operation during retry", async () => {
  const harness = createHarness({
    beneficio: false,
    postRegistro: (_payload, count) => {
      if (count === 1) throw new Error("Network Error");
      return { data: { success: true } };
    },
  });
  await selectItem(harness);
  await harness.act(() => harness.sections.handleConfirmar());
  await harness.act(() => harness.sections.setMotivo("Motivo corrigido depois do envio"));
  await harness.act(() => harness.sections.onRecuperar("tentar_novamente"));
  const records = harness.calls.filter((call) => call.url === "/vendas/100/devolucao");
  assert.equal(records.length, 2);
  assert.deepEqual(records[0].payload, records[1].payload);
  assert.equal(harness.calls.filter((call) => call.url?.endsWith("/previa")).length, 1);
  assert.equal(harness.confirmations.length, 1);
  assert.equal(harness.successes.length, 1);
});

test("returning to the sale list cannot discard an uncertain operation and provides a way to check it", async () => {
  const harness = createHarness({
    beneficio: false,
    postRegistro: (_payload, count) => {
      if (count === 1) throw new Error("Network Error");
      return { data: { success: true } };
    },
  });
  await selectItem(harness);
  await harness.act(() => harness.sections.handleConfirmar());
  await harness.act(() => {
    // This is the return modal's Back button handler.
    harness.sections.setPasso(1);
    harness.sections.setVendaSelecionada(null);
    harness.sections.setItensSelecionados({});
    harness.sections.setQuantidades({});
    harness.sections.setMotivo("");
    harness.sections.setErro("");
  });
  await harness.act(() => harness.sections.selecionarVenda({ id: 100 }));
  assert.ok(harness.sections.recuperacao.acoes.some((action) => action.id === "tentar_novamente"));
  await harness.act(() => harness.sections.onRecuperar("tentar_novamente"));
  const records = harness.calls.filter((call) => call.url === "/vendas/100/devolucao");
  assert.equal(records.length, 2);
  assert.deepEqual(records[0].payload, records[1].payload);
  assert.equal(harness.calls.filter((call) => call.url?.endsWith("/previa")).length, 1);
  assert.equal(harness.successes.length, 1);
});

test("opening a cash register preserves the return draft and uses the newly opened register", async () => {
  const harness = createHarness({ beneficio: false, caixaId: null });
  await selectItem(harness);
  await harness.act(() => harness.sections.handleConfirmar());
  assert.equal(harness.calls.filter((call) => call.url === "/vendas/100/devolucao").length, 0);
  assert.ok(harness.sections.recuperacao.acoes.some((action) => action.id === "abrir_caixa"));
  await harness.act(() => harness.sections.onRecuperar("abrir_caixa"));
  assert.ok(harness.abrirCaixa);
  harness.setCaixa({ id: 77 });
  await harness.act(() => harness.abrirCaixa.onSucesso());
  assert.equal(harness.abrirCaixa, undefined);
  assert.equal(harness.sections.itensSelecionados[1], true);
  assert.equal(harness.sections.quantidades[1], 1);
  assert.equal(harness.sections.motivo, "Troca solicitada pelo cliente");
  await harness.act(() => harness.sections.handleConfirmar());
  const record = harness.calls.find((call) => call.url === "/vendas/100/devolucao");
  assert.equal(record.payload.caixa_id, 77);
});

test("refreshing returnable quantities clamps the selection without losing the reason", async () => {
  const harness = createHarness({ beneficio: false });
  await selectItem(harness);
  harness.setSaldo(0.5);
  await harness.act(() => harness.sections.onRecuperar("atualizar_saldos"));
  assert.equal(harness.sections.quantidades[1], 0.5);
  assert.equal(harness.sections.itensSelecionados[1], true);
  assert.equal(harness.sections.motivo, "Troca solicitada pelo cliente");
  harness.setSaldo(0);
  await harness.act(() => harness.sections.onRecuperar("atualizar_saldos"));
  assert.equal(harness.sections.quantidades[1], 0);
  assert.equal(harness.sections.itensSelecionados[1], false);
});

test("a second confirmation while preview is pending cannot send a duplicate return", async () => {
  let resolvePreview;
  const preview = new Promise((resolve) => {
    resolvePreview = resolve;
  });
  const harness = createHarness({ beneficio: false, postPrevia: () => preview });
  await selectItem(harness);
  const first = harness.sections.handleConfirmar();
  const second = harness.sections.handleConfirmar();
  await harness.settle();
  assert.equal(harness.calls.filter((call) => call.url?.endsWith("/previa")).length, 1);
  resolvePreview({ data: { valor_total_devolucao: 38.9 } });
  await Promise.all([first, second]);
  await harness.settle();
  assert.equal(harness.calls.filter((call) => call.url === "/vendas/100/devolucao").length, 1);
  assert.equal(harness.successes.length, 1);
});

test("a sale without a customer cannot send a credit return and offers a cash refund", async () => {
  const harness = createHarness({ beneficio: false, cliente: false });
  await selectItem(harness);
  await harness.act(() => harness.sections.setGerarCredito(true));
  await harness.act(() => harness.sections.handleConfirmar());
  assert.equal(harness.calls.filter((call) => call.method === "post").length, 0);
  assert.ok(harness.sections.recuperacao.acoes.some((action) => action.id === "usar_dinheiro"));
  await harness.act(() => harness.sections.onRecuperar("usar_dinheiro"));
  await harness.act(() => harness.sections.handleConfirmar());
  const record = harness.calls.find((call) => call.url === "/vendas/100/devolucao");
  assert.equal(record.payload.gerar_credito, false);
});

test("a return entirely restored to cashback does not require an open cash register", async () => {
  const restituicao = {
    cashback: 38.9,
    credito_cliente: 0,
    valor_restante: 0,
    cashback_expirado: 0,
  };
  const harness = createHarness({
    caixaId: null,
    postPrevia: () => ({ data: { valor_total_devolucao: 38.9, restituicao } }),
  });
  await selectItem(harness);
  await harness.act(() => harness.sections.onRecuperar("devolver_na_origem"));
  await harness.act(() => harness.sections.handleConfirmar());
  const record = harness.calls.find((call) => call.url === "/vendas/100/devolucao");
  assert.ok(record);
  assert.equal(record.payload.caixa_id, null);
  assert.deepEqual(record.payload.restituicao_prevista, restituicao);
  assert.equal(harness.abrirCaixa, undefined);
  assert.equal(harness.successes.length, 1);
});

test("changing the return quantity invalidates the previously displayed restitution", async () => {
  const harness = createHarness({ beneficio: false, caixaId: null });
  await selectItem(harness);
  await harness.act(() => harness.sections.handleConfirmar());
  assert.ok(harness.sections.previaRestituicao);
  await harness.act(() => harness.sections.handleQuantidadeChange(1, "0.5"));
  assert.equal(harness.sections.previaRestituicao, null);
});
