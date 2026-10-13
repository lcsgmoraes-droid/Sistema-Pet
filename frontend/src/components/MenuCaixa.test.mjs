import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";
import ts from "typescript";

const menuPath = fileURLToPath(new URL("./MenuCaixa.jsx", import.meta.url));
const caixa = {
  id: 30,
  numero_caixa: 1,
  valor_abertura: 100,
  data_abertura: "2026-10-13T10:00:00",
};
const venda = { id: 100, status: "finalizada", numero_venda: "V100" };

// Run the component's real state transitions and inspect React element identity.
// The same parent, element type and key preserve a modal's draft during reconciliation.
function createHarness(overrides = {}) {
  const slots = [];
  const calls = [];
  const ModalDevolucao = () => null;
  const ModalSangria = () => null;
  let index = 0;
  let dirty = false;
  let effects = [];
  let tree;
  let props = {
    caixaAberto: caixa,
    contextoCaixa: "usuario:empresa",
    statusConsultaCaixa: "pronto",
    abrirDevolucaoSignal: 0,
    vendaParaDevolucao: venda,
    atualizarCaixa: async () => {
      calls.push("atualizar");
    },
    onAbrirCaixa: async () => {
      calls.push("abrir");
    },
    onDevolucaoSucesso: (resultado) => {
      calls.push(resultado);
    },
    ...overrides,
  };
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
      const previous = slots[slot];
      if (
        !previous?.dependencies ||
        dependencies.some((value, i) => !Object.is(value, previous.dependencies[i]))
      ) {
        previous?.cleanup?.();
        slots[slot] = { dependencies };
        effects.push(() => {
          slots[slot].cleanup = effect();
        });
      }
    },
  };
  const jsx = (type, elementProps, key) => ({ type, props: elementProps, key });
  const mocks = new Map([
    ["react", hooks],
    ["react/jsx-runtime", { jsx, jsxs: jsx, Fragment: "fragment" }],
    ["lucide-react", new Proxy({}, { get: (_target, name) => name })],
    ["../api/caixa", { obterResumoCaixa: async () => ({ totais: {} }) }],
    ["./ModalDevolucao", { __esModule: true, default: ModalDevolucao }],
    ["./ModaisCaixa", { ModalSuprimento: () => null, ModalSangria, ModalDespesa: () => null }],
    ["./ModalFecharCaixa", { __esModule: true, default: () => null }],
    ["./ModalMovimentacoesCaixa", { __esModule: true, default: () => null }],
  ]);
  const cache = new Map();
  function loadModule(path) {
    if (cache.has(path)) return cache.get(path);
    const { outputText, diagnostics } = ts.transpileModule(readFileSync(path, "utf8"), {
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
      diagnostics.filter((item) => item.category === ts.DiagnosticCategory.Error).length,
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
    new Function("require", "module", "exports", outputText)(requireMock, module, module.exports);
    return module.exports;
  }
  const MenuCaixa = loadModule(menuPath).default;
  function render() {
    index = 0;
    dirty = false;
    effects = [];
    tree = MenuCaixa(props);
    effects.forEach((effect) => effect());
  }
  function elements(node) {
    if (!node || typeof node !== "object") return [];
    if (Array.isArray(node)) return node.flatMap(elements);
    return [node, ...elements(node.props?.children)];
  }
  function text(node) {
    if (typeof node === "string") return node;
    if (!node || typeof node !== "object") return "";
    if (Array.isArray(node)) return node.map(text).join(" ");
    return text(node.props?.children);
  }
  async function settle() {
    for (let pass = 0; pass < 20; pass++) {
      await Promise.resolve();
      if (dirty) render();
    }
  }
  render();
  return {
    calls,
    get tree() {
      return tree;
    },
    get modal() {
      return elements(tree).find((element) => element.type === ModalDevolucao);
    },
    get sangria() {
      return elements(tree).find((element) => element.type === ModalSangria);
    },
    get buttons() {
      return elements(tree).filter((element) => element.type === "button");
    },
    settle,
    async update(update) {
      props = { ...props, ...update };
      render();
      await settle();
    },
    async click(label) {
      const button = elements(tree).find(
        (element) => element.type === "button" && text(element).includes(label),
      );
      assert.ok(button, `Button ${label} not found`);
      await button.props.onClick();
      await settle();
    },
  };
}

test("devolução mantém a mesma identidade quando o monitor fecha, consulta ou reabre o caixa", async () => {
  const harness = createHarness({ abrirDevolucaoSignal: 1 });
  await harness.settle();
  const identidade = harness.modal;
  assert.ok(identidade);
  assert.equal(identidade.props.caixaId, 30);
  for (const estado of [
    { caixaAberto: null, statusConsultaCaixa: "carregando" },
    { caixaAberto: null, statusConsultaCaixa: "erro" },
    { caixaAberto: null, statusConsultaCaixa: "pronto" },
    { caixaAberto: { ...caixa, id: 77 }, statusConsultaCaixa: "pronto" },
  ]) {
    await harness.update(estado);
    assert.equal(harness.tree.type, "fragment");
    assert.ok(harness.tree.props.children.includes(harness.modal));
    assert.equal(harness.modal.type, identidade.type);
    assert.equal(harness.modal.key, identidade.key);
    assert.equal(harness.modal.key, "devolucao");
    assert.equal(harness.modal.props.vendaInicial, venda);
    assert.equal(harness.modal.props.caixaId, estado.caixaAberto?.id);
  }
});

test("solicitação de devolução abre sem caixa e não reabre após fechar com o mesmo sinal", async () => {
  const harness = createHarness({
    caixaAberto: null,
    statusConsultaCaixa: "erro",
    abrirDevolucaoSignal: 1,
  });
  await harness.settle();
  assert.ok(harness.modal);
  assert.equal(harness.modal.props.caixaId, undefined);
  harness.modal.props.onClose();
  await harness.settle();
  assert.equal(harness.modal, undefined);
  await harness.update({ caixaAberto: caixa, statusConsultaCaixa: "pronto" });
  assert.equal(harness.modal, undefined);
  await harness.update({ abrirDevolucaoSignal: 2 });
  assert.ok(harness.modal);
});

test("devolução concluída sem caixa atualiza o PDV sem erro de caixa nulo", async () => {
  const harness = createHarness({ caixaAberto: null, abrirDevolucaoSignal: 1 });
  await harness.settle();
  const resultado = { venda_id: 100, cliente_id: 200 };
  harness.modal.props.onSucesso(resultado);
  await harness.settle();
  assert.equal(harness.modal, undefined);
  assert.deepEqual(harness.calls, ["atualizar", resultado]);
});

test("outras operações de caixa continuam fechando quando o caixa muda", async () => {
  const harness = createHarness();
  await harness.settle();
  await harness.click("Caixa #");
  await harness.click("Sangria");
  assert.ok(harness.sangria);
  await harness.update({ caixaAberto: null });
  assert.equal(harness.sangria, undefined);
  assert.equal(harness.modal, undefined);
});
