import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elements,
} from "../../../scripts/helpers/reactControllerHarness.mjs";
import { atualizarCanalClone, CNPJ_PUBLICO_AMAZON } from "./clonagemNotaUtils.js";

function setup(modelo = 55) {
  const changes = [];
  const mocks = new Map(
    ["BotaoInteracao", "InputCombobox", "InputCpfCnpj", "InputTexto", "LinkPadrao"].map((nome) => [
      `../../components/v2/${nome}/${nome}`,
      nome,
    ]),
  );
  const harness = createControllerHarness(
    fileURLToPath(new URL("./NFSaidaCloneComercial.jsx", import.meta.url)),
    {
      props: {
        modelo,
        dados: { indicadorPresenca: "1" },
        alterar: (...args) => changes.push(args),
        alterarCanal: (valor) => changes.push(["canal", valor]),
        disabled: false,
      },
      mocks,
    },
  );
  const field = (label) => elements(harness.tree).find((item) => item.props?.label === label);
  return { harness, field, changes };
}

test("cópia NF55 apresenta Amazon e permite revisar CNPJ e Seller ID sem dados pessoais fixos", async () => {
  const env = setup();
  await env.harness.act(() => env.field("Canal da cópia").props.onChange("amazon"));
  assert.deepEqual(env.changes, [["canal", "amazon"]]);
  await env.harness.update({ dados: atualizarCanalClone({ indicadorPresenca: "1" }, "amazon") });
  assert.equal(env.field("CNPJ do intermediador da cópia").props.value, CNPJ_PUBLICO_AMAZON);
  const cadastro = env.field("Identificação da loja ou vendedor no intermediador");
  assert.equal(cadastro.props.value, "");
  assert.match(cadastro.props.help, /Seller ID.*idCadIntTran.*diferente do número do pedido/);
  await env.harness.act(() => cadastro.props.onChange("LOJA-QA-777"));
  assert.deepEqual(env.changes.at(-1), ["intermediador.identificadorCadastro", "LOJA-QA-777"]);
  await env.harness.update({ disabled: true });
  assert.equal(env.field("Canal da cópia").props.disabled, true);
});

test("NFC-e não oferece edição de intermediação", () => {
  const env = setup(65);
  assert.equal(env.harness.tree, null);
});
