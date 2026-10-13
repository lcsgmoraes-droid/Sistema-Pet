import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";
import test from "node:test";
import {
  createControllerHarness,
  elements,
  elementText,
} from "../../scripts/helpers/reactControllerHarness.mjs";

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
  const calls = [];
  const ModalDevolucao = () => null;
  const ModalSangria = () => null;
  const props = {
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
  const mocks = new Map([
    ["lucide-react", new Proxy({}, { get: (_target, name) => name })],
    ["../api/caixa", { obterResumoCaixa: async () => ({ totais: {} }) }],
    ["./ModalDevolucao", { __esModule: true, default: ModalDevolucao }],
    ["./ModaisCaixa", { ModalSuprimento: () => null, ModalSangria, ModalDespesa: () => null }],
    ["./ModalFecharCaixa", { __esModule: true, default: () => null }],
    ["./ModalMovimentacoesCaixa", { __esModule: true, default: () => null }],
  ]);
  const controller = createControllerHarness(menuPath, { mocks, props });
  return {
    calls,
    get tree() {
      return controller.tree;
    },
    get modal() {
      return elements(controller.tree).find((element) => element.type === ModalDevolucao);
    },
    get sangria() {
      return elements(controller.tree).find((element) => element.type === ModalSangria);
    },
    get buttons() {
      return elements(controller.tree).filter((element) => element.type === "button");
    },
    settle: controller.settle,
    update: controller.update,
    async click(label) {
      const button = elements(controller.tree).find(
        (element) => element.type === "button" && elementText(element).includes(label),
      );
      assert.ok(button, `Button ${label} not found`);
      await button.props.onClick();
      await controller.settle();
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
