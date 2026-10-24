import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elements,
  elementText,
} from "../../../scripts/helpers/reactControllerHarness.mjs";

const stub = (value) => ({ __esModule: true, default: value });
const publication = {
  product_id: 6398,
  barcode: "0789000000011",
  snapshot_saved: { codigo: "018631.1", nome: "Produto fictício" },
  pending: [],
  capabilities: { write_enabled: false, can_confirm: true },
  last_submission: { status: "accepted", created_at: "2026-10-23T12:00:00Z" },
  last_confirmation: null,
};
const defaults = () => ({
  publication,
  loading: false,
  busy: "",
  error: "",
  success: "",
  dirty: false,
  ready: true,
  mode: "existing",
  fields: ["price", "stock"],
  portalChecked: false,
  confirmSend: false,
  confirmPortal: false,
  present: true,
  observedPrice: null,
  observedStock: null,
  operation: "update",
  canLink: true,
  canPrepare: true,
  canSend: false,
  canConfirm: false,
  alterar() {},
  atualizar() {},
  vincular() {},
  preparar() {},
  enviar() {},
  confirmar() {},
});
function setup(extra = {}, props = {}) {
  const c = { ...defaults(), ...extra };
  const controls = [
    "BotaoCancelar",
    "BotaoInteracao",
    "InputCheckTexto",
    "InputTexto",
    "InputRadio",
    "LinkPadrao",
    "ModalPadrao",
  ];
  const harness = createControllerHarness(
    fileURLToPath(new URL("./IfoodPublicacaoProduto.jsx", import.meta.url)),
    {
      props: { productId: 6398, onFechar() {}, ...props },
      mocks: new Map([
        ...controls.map((name) => [`../v2/${name}/${name}`, stub(name)]),
        ["lucide-react", {}],
        ["../../utils/modalEscape", { useEscapeToClose() {} }],
        ["./useIfoodPublicacaoProduto", stub(() => c)],
      ]),
    },
  );
  return { harness, c };
}
const text = (env) => elementText(env.harness.tree);
const button = (env, label) =>
  elements(env.harness.tree).find(
    (el) => el.type === "BotaoInteracao" && elementText(el).includes(label),
  );

test("202 aceito é apresentado separado da confirmação manual no Portal", () => {
  const env = setup();
  assert.match(text(env), /Aceito pela API — confira no Portal/);
  assert.match(text(env), /Aceite da API não confirma a publicação/);
  assert.doesNotMatch(text(env), /Última conferência manual:/);
  assert.match(text(env), /018631.1/);
  assert.equal(button(env, "Registrar conferência manual").props.disabled, true);
});

test("valores desconhecidos permanecem vazios, sem converter ausência em zero", () => {
  const env = setup();
  const inputs = elements(env.harness.tree).filter((el) => el.type === "InputTexto");
  assert.equal(inputs.length, 2);
  assert.deepEqual(
    inputs.map((input) => input.props.value),
    ["", ""],
  );
  assert.match(inputs[1].props.help, /zero é uma declaração explícita/);
});

test("rascunho bloqueia ações e a conferência anterior permanece declarada como humana", () => {
  const env = setup({
    dirty: true,
    ready: false,
    canLink: false,
    canPrepare: false,
    publication: {
      ...publication,
      last_confirmation: {
        present: true,
        price: "100.00",
        stock: "0",
        confirmed_at: "2026-10-22T12:00:00Z",
      },
    },
  });
  assert.match(text(env), /Salve o cadastro antes/);
  assert.match(text(env), /não confirma envios posteriores/);
  assert.match(text(env), /Estoque conferido:\s+0/);
  assert.equal(button(env, "Preparar prévia").props.disabled, true);
});

test("sem capacidade de envio a prévia nunca libera publicação", () => {
  const env = setup({
    review: {
      eligible: true,
      operation: "create",
      payload: { barcode: "0789000000011" },
      pending: [],
    },
    operation: "create",
  });
  assert.match(text(env), /Envios estão desabilitados neste ambiente/);
  assert.equal(button(env, "Publicar este produto").props.disabled, true);
  assert.equal(
    elements(env.harness.tree).some((el) =>
      ["input", "button", "select", "textarea"].includes(el.type),
    ),
    false,
  );
});

test("incerteza e falha preservam histórico sem declarar publicação", () => {
  const env = setup({
    uncertain: true,
    error: "Falha de consulta",
    publication: { ...publication, last_submission: { status: "uncertain" } },
  });
  assert.match(text(env), /Não repita o envio/);
  assert.match(text(env), /Resultado do envio desconhecido/);
  assert.doesNotMatch(text(env), /Produto publicado com sucesso/);
});

test("memória de atualização mostra somente valores enviados e preserva promoção", () => {
  const harness = createControllerHarness(
    fileURLToPath(new URL("./IfoodPublicacaoProduto.jsx", import.meta.url)),
    {
      exportName: "MemoriaEnvio",
      props: {
        review: {
          operation: "update",
          payload: { barcode: "0789000000011", inventory: { stock: 0 } },
        },
      },
      mocks: new Map([
        ["react", {}],
        ["lucide-react", {}],
        ...[
          "BotaoCancelar",
          "BotaoInteracao",
          "InputCheckTexto",
          "InputTexto",
          "InputRadio",
          "LinkPadrao",
          "ModalPadrao",
        ].map((name) => [`../v2/${name}/${name}`, stub(name)]),
        ["../../utils/modalEscape", { useEscapeToClose() {} }],
        ["./useIfoodPublicacaoProduto", stub(() => ({}))],
      ]),
    },
  );
  assert.match(elementText(harness.tree), /Estoque disponível enviado\s+0/);
  assert.doesNotMatch(elementText(harness.tree), /Preço regular enviado/);
  assert.match(elementText(harness.tree), /promoção do iFood serão preservados/);
});
