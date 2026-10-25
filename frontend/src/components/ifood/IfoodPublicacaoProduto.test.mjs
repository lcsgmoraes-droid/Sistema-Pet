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
  confirmation_context_token: "c".repeat(64),
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
  observedActive: null,
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
  const active = elements(env.harness.tree).find(
    (el) => el.type === "InputRadio" && el.props.label === "Disponibilidade no Portal",
  );
  assert.equal(active.props.value, "unknown");
  assert.deepEqual(
    active.props.opcoes.map((item) => item.label),
    ["Ativo", "Inativo", "Não conferi"],
  );
});

test("disponibilidade usa o componente V2, mantém três estados e respeita as capacidades", () => {
  for (const [active, expected] of [
    [true, "active"],
    [false, "inactive"],
    [null, "unknown"],
  ]) {
    const calls = [];
    const env = setup({ observedActive: active, alterar: (...args) => calls.push(args) });
    const input = elements(env.harness.tree).find(
      (el) => el.type === "InputRadio" && el.props.label === "Disponibilidade no Portal",
    );
    assert.equal(input.props.value, expected);
    assert.equal(input.props.disabled, false);
    for (const value of ["active", "inactive", "unknown"]) input.props.onChange(value);
    assert.deepEqual(calls, [
      ["observedActive", true],
      ["observedActive", false],
      ["observedActive", null],
    ]);
  }
  for (const extra of [
    { present: false },
    { ready: false },
    { publication: { ...publication, capabilities: { can_confirm: false } } },
    { publication: { ...publication, confirmation_context_token: null } },
  ]) {
    const env = setup(extra);
    const input = elements(env.harness.tree).find(
      (el) => el.type === "InputRadio" && el.props.label === "Disponibilidade no Portal",
    );
    assert.equal(input.props.disabled, true);
  }
});

test("automação ativa permite só a conferência autorizada e preserva o bloqueio manual", () => {
  const env = setup({
    canLink: false,
    canPrepare: false,
    canSend: false,
    canConfirm: true,
    observedActive: true,
    publication: {
      ...publication,
      stock_sync: {
        enabled: true,
        status: "accepted",
        provider_mode: "ifood_api",
        environment: "production",
      },
      capabilities: { can_confirm: true, can_link: false, can_send: false, write_enabled: true },
    },
  });
  assert.equal(button(env, "Registrar conferência manual").props.disabled, false);
  assert.equal(button(env, "Registrar conferência do EAN").props.disabled, true);
  assert.equal(button(env, "Preparar prévia").props.disabled, true);
  const active = elements(env.harness.tree).find(
    (el) => el.type === "InputRadio" && el.props.label === "Disponibilidade no Portal",
  );
  assert.equal(active.props.disabled, false);
  assert.match(text(env), /Não envia alterações ao iFood nem muda/);
  assert.equal(
    elements(env.harness.tree).some((el) =>
      ["input", "button", "select", "textarea"].includes(el.type),
    ),
    false,
  );
});

test("histórico distingue ativo, inativo e disponibilidade não conferida sem preencher a nova declaração", () => {
  for (const [active, expected] of [
    [true, "Ativo"],
    [false, "Inativo"],
    [null, "Não conferida"],
  ]) {
    const env = setup({
      publication: { ...publication, last_confirmation: { present: true, portal_active: active } },
    });
    assert.match(text(env), new RegExp(`Disponibilidade conferida:\\s+${expected}`));
    const input = elements(env.harness.tree).find(
      (el) => el.type === "InputRadio" && el.props.label === "Disponibilidade no Portal",
    );
    assert.equal(input.props.value, "unknown");
  }
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

function stockSummary(sync) {
  return createControllerHarness(
    fileURLToPath(new URL("./IfoodPublicacaoProduto.jsx", import.meta.url)),
    {
      exportName: "ResumoEstoqueAutomatico",
      props: { sync },
      mocks: new Map([
        ...[
          "BotaoCancelar",
          "BotaoInteracao",
          "InputCheckTexto",
          "InputTexto",
          "InputRadio",
          "LinkPadrao",
          "ModalPadrao",
        ].map((name) => [`../v2/${name}/${name}`, stub(name)]),
        ["lucide-react", {}],
        ["../../utils/modalEscape", { useEscapeToClose() {} }],
        ["./useIfoodPublicacaoProduto", stub(() => ({}))],
      ]),
    },
  );
}

test("estoque automático preserva zero, distingue referência de confirmação e não oferece envio", () => {
  const env = stockSummary({
    status: "accepted",
    desired_stock: 0,
    last_accepted_stock: 0,
    enabled: true,
  });
  assert.match(elementText(env.tree), /Saldo disponível atual\s*:\s+0/);
  assert.match(elementText(env.tree), /resultado externo a conferir/);
  assert.match(elementText(env.tree), /não comprova aplicação no iFood/);
  assert.match(elementText(env.tree), /Preços não fazem parte/);
  assert.equal(
    elements(env.tree).some((el) => /^(input|button|select|textarea|Botao)/.test(el.type)),
    false,
  );
});

test("histórico da automação desligada mantém saldo desconhecido e resultado incerto", () => {
  const env = stockSummary({
    status: "uncertain",
    desired_stock: null,
    last_accepted_stock: 21,
    enabled: false,
  });
  assert.match(elementText(env.tree), /Saldo disponível atual\s*:\s+Não conferido/);
  assert.match(elementText(env.tree), /Resultado desconhecido; confira antes de reenviar/);
  assert.match(elementText(env.tree), /Piloto desativado; histórico preservado/);
});

test("aceite do simulador DEV não aparece como aceite do iFood real", () => {
  const env = setup({
    publication: {
      ...publication,
      last_submission: {
        status: "accepted",
        source: "auto_stock",
        provider_mode: "local_simulator",
        message: "Ensaio com simulador local em DEV",
      },
    },
  });
  assert.match(text(env), /Aceito pelo simulador DEV — iFood real não conferido/);
  assert.doesNotMatch(text(env), /Aceito pela API — confira no Portal/);
});

test("histórico real usa o modo persistido e continua separando aceite de aplicação", () => {
  const env = stockSummary({
    status: "accepted",
    desired_stock: 21,
    last_accepted_stock: 21,
    enabled: true,
    provider_mode: "ifood_api",
    environment: "production",
    reference_source: "api_acceptance",
  });
  assert.match(elementText(env.tree), /Sincronização ativa somente para este produto/);
  assert.match(elementText(env.tree), /aceite não confirma a aplicação/);
  assert.match(elementText(env.tree), /Preços não fazem parte/);
  assert.doesNotMatch(elementText(env.tree), /simulador|piloto DEV/);
});

test("observação de ausente, inativo ou desconhecido explica a espera sem substituir o aceite histórico", () => {
  for (const [reason, expected] of [
    ["portal_item_not_found", /produto não localizado no Portal/],
    ["portal_item_inactive", /produto conferido como inativo no Portal/],
    ["portal_activity_unknown", /disponibilidade no Portal não conferida/],
  ]) {
    const sync = {
      status: "accepted",
      desired_stock: 21,
      last_accepted_stock: 21,
      enabled: true,
      provider_mode: "ifood_api",
      environment: "production",
      reference_source: "api_acceptance",
      observation_block_reason: reason,
    };
    const env = stockSummary(sync);
    assert.match(elementText(env.tree), /Novos envios em espera/);
    assert.match(elementText(env.tree), expected);
    assert.match(elementText(env.tree), /Último saldo calculado pela automação\s*:\s+21/);
    assert.doesNotMatch(elementText(env.tree), /Saldo disponível atual\s*:/);
    assert.match(elementText(env.tree), /Último saldo enviado ou conferido:\s+21/);
    assert.equal(sync.status, "accepted");
    assert.equal(sync.last_accepted_stock, 21);
  }
});
