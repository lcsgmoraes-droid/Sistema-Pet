import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elements,
  elementText,
} from "../../scripts/helpers/reactControllerHarness.mjs";

// O carregador resolve imports sem extensão como .js. Esta ponte carrega o
// CurrencyInput.jsx real para exercitar também a máscara monetária existente.
const CurrencyInput = createControllerHarness(
  fileURLToPath(new URL("./CurrencyInput.jsx", import.meta.url)),
  { mocks: new Map(), props: {}, invoke: (Component) => Component },
).tree;

function preparar(props = {}) {
  const confirmados = [];
  const harness = createControllerHarness(
    fileURLToPath(new URL("./SubtotalInput.jsx", import.meta.url)),
    {
      mocks: new Map([["./CurrencyInput", { __esModule: true, default: CurrencyInput }]]),
      props: {
        subtotal: 13,
        precoUnitario: 13,
        onSubtotalChange: (valor) => confirmados.push(valor),
        ...props,
      },
      invoke: (Component, currentProps) => {
        const container = Component(currentProps);
        const campo = elements(container).find((node) => node.type === CurrencyInput);
        return { container, input: campo ? CurrencyInput(campo.props) : null };
      },
    },
  );
  const target = {
    value: "",
    selectionStart: 0,
    selectionEnd: 0,
    select() {
      this.selectionStart = 0;
      this.selectionEnd = this.value.length;
    },
    blur() {
      harness.tree.input.props.onBlur();
    },
  };
  const focar = async () => {
    target.value = harness.tree.input.props.value;
    await harness.act(() => harness.tree.input.props.onFocus({ target }));
  };
  const tecla = async (key) => {
    let prevenido = false;
    const evento = {
      key,
      target,
      preventDefault: () => {
        prevenido = true;
      },
    };
    await harness.act(() => {
      harness.tree.input.props.onKeyDown(evento);
      harness.tree.container.props.onKeyDown(evento);
    });
    target.value = harness.tree.input.props.value;
    target.selectionStart = target.value.length;
    target.selectionEnd = target.value.length;
    return prevenido;
  };
  const digitar = async (digitos) => {
    for (const digito of digitos) await tecla(digito);
  };
  const sair = () => harness.act(() => target.blur());
  return { harness, confirmados, focar, tecla, digitar, sair, target };
}

test("digitar R$ 20,00 mantém o valor local e só confirma o subtotal ao sair", async () => {
  const env = preparar();
  await env.focar();
  assert.equal(env.target.selectionStart, 0);
  assert.equal(env.target.selectionEnd, "13,00".length);
  await env.digitar("2000");

  assert.equal(env.harness.tree.input.props.value, "20,00");
  assert.deepEqual(env.confirmados, []);
  // Uma atualização dos dados do pai durante a digitação não apaga a edição.
  await env.harness.update({ subtotal: 13 });
  assert.equal(env.harness.tree.input.props.value, "20,00");

  await env.sair();
  assert.deepEqual(env.confirmados, [20]);
  await env.harness.update({ subtotal: 20 });
  assert.equal(env.harness.tree.input.props.value, "20,00");
});

test("Enter confirma uma única vez pelo blur e preserva R$ 20,00 ao reabrir", async () => {
  const env = preparar();
  await env.focar();
  await env.digitar("2000");
  assert.equal(await env.tecla("Enter"), true);
  assert.deepEqual(env.confirmados, [20]);

  await env.harness.update({ subtotal: 20 });
  await env.focar();
  await env.sair();
  assert.deepEqual(env.confirmados, [20, 20]);
  assert.equal(env.harness.tree.input.props.value, "20,00");
});

test("Escape descarta a edição e a próxima edição continua confirmando normalmente", async () => {
  const env = preparar();
  await env.focar();
  await env.digitar("2000");
  await env.tecla("Escape");
  assert.deepEqual(env.confirmados, []);
  assert.equal(env.harness.tree.input.props.value, "13,00");

  await env.focar();
  await env.digitar("2000");
  await env.sair();
  assert.deepEqual(env.confirmados, [20]);
});

test("subtotal zerado não confirma e visualização desabilitada mostra a moeda correta", async () => {
  const env = preparar();
  await env.focar();
  await env.tecla("Delete");
  await env.sair();
  assert.deepEqual(env.confirmados, []);

  await env.harness.update({ subtotal: 20, disabled: true });
  assert.equal(env.harness.tree.input, null);
  assert.match(elementText(env.harness.tree.container), /R\$\s+20,00/);
});
