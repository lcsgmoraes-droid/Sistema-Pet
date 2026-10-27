import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elements,
  elementText,
} from "../../../../scripts/helpers/reactControllerHarness.mjs";
import * as utils from "./amazonFiscalUtils.js";

const leafMocks = (names, prefix = "../../../components/v2") =>
  names.map((name) => [`${prefix}/${name}/${name}`, name]);
function control(harness, label) {
  return elements(harness.tree).find((item) => item.props?.label === label);
}

test("conta nova inicia sem automação e exige confirmação específica ao mudar política de descontos", async () => {
  const saved = [];
  const harness = createControllerHarness(
    fileURLToPath(new URL("./AmazonFiscalAccountForm.jsx", import.meta.url)),
    {
      props: { account: {}, onSave: (form) => saved.push(form) },
      mocks: new Map([
        ...leafMocks([
          "BotaoCancelar",
          "BotaoSalva",
          "InputCheck",
          "InputCombobox",
          "InputCpfCnpj",
          "InputTexto",
          "ModalPadrao",
        ]),
        ["./amazonFiscalUtils", utils],
      ]),
    },
  );
  assert.equal(
    control(harness, "Ativar fluxo de pedidos Amazon com EcommerceAI nesta empresa").props.checked,
    false,
  );
  assert.equal(control(harness, "Política de descontos").props.value, "source_discounts");
  await harness.act(() =>
    control(harness, "Política de descontos").props.onChange("buyer_payment_total"),
  );
  assert.equal(
    control(harness, "Autorizo ajustar o desconto ao pagamento documentado").props.checked,
    false,
  );
  assert.match(
    control(harness, "Ativar fluxo de pedidos Amazon com EcommerceAI nesta empresa").props.help,
    /Pedidos anteriores exigem/,
  );
  const save = () => elements(harness.tree.props.rodape).find((item) => item.type === "BotaoSalva");
  await harness.act(() => save().props.onClick());
  assert.equal(saved[0].discount_consent, false);
  assert.equal(saved[0].upload_enabled, false);
  assert.equal(saved[0].active, false);
  assert.equal(
    control(harness, "Emitir NF-e automaticamente após as validações").props.disabled,
    true,
  );
  await harness.act(() =>
    control(harness, "Ativar fluxo de pedidos Amazon com EcommerceAI nesta empresa").props.onChange(
      true,
    ),
  );
  await harness.act(() => save().props.onClick());
  assert.equal(saved.at(-1).active, true);
  assert.equal(saved.at(-1).auto_issue_enabled, false);
  await harness.act(() =>
    control(harness, "Emitir NF-e automaticamente após as validações").props.onChange(true),
  );
  await harness.act(() => save().props.onClick());
  assert.equal(saved.at(-1).auto_issue_enabled, true);
  assert.equal(saved.at(-1).upload_enabled, false);
  await harness.act(() =>
    control(harness, "Autorizar envio automático do XML à Amazon quando permitido").props.onChange(
      true,
    ),
  );
  await harness.act(() => save().props.onClick());
  assert.equal(saved.at(-1).upload_enabled, true);
  await harness.update({ hasFiscalScopes: false });
  assert.match(elementText(harness.tree), /ainda precisa das permissões fiscais aprovadas/);
  await harness.act(() =>
    control(harness, "Ativar fluxo de pedidos Amazon com EcommerceAI nesta empresa").props.onChange(
      false,
    ),
  );
  assert.equal(
    control(harness, "Ativar fluxo de pedidos Amazon com EcommerceAI nesta empresa").props.disabled,
    true,
  );
  assert.equal(
    control(harness, "Emitir NF-e automaticamente após as validações").props.checked,
    false,
  );
  assert.equal(
    control(harness, "Autorizar envio automático do XML à Amazon quando permitido").props.checked,
    false,
  );
  assert.equal(
    control(harness, "Autorizar envio automático do XML à Amazon quando permitido").props.disabled,
    true,
  );
});

for (const fiscal of [true, false])
  test(`nova aprovação ${fiscal ? "fiscal exige opt-in" : "legada preserva escopos"}`, async () => {
    const posts = [];
    let finish;
    const pending = new Promise((resolve) => {
      finish = resolve;
    });
    const data = {
      connected: false,
      request: {
        status: "pending",
        requested_scopes: fiscal
          ? ["catalog:read", ...utils.FISCAL_SCOPES]
          : ["catalog:read", "events:write"],
      },
    };
    const api = {
      get: async () => ({ data }),
      post: (path, body) => {
        posts.push({ path, body });
        return pending;
      },
    };
    const harness = createControllerHarness(
      fileURLToPath(new URL("../EcommerceAIIntegracaoCard.jsx", import.meta.url)),
      {
        mocks: new Map([
          ["react-icons/fi", new Proxy({}, { get: (_target, key) => String(key) })],
          ["../../services/api", { api }],
          ["../../services/corepetDialog", { confirmarCorePet: async () => true }],
          ...leafMocks(["BotaoCancelar", "BotaoInteracao", "InputCheck"], "../../components/v2"),
          ["./amazonFiscal/AmazonFiscalPanel", "AmazonFiscalPanel"],
          ["./amazonFiscal/amazonFiscalUtils", utils],
        ]),
        globals: { globalThis: { location: { search: "?ecommerceai_request=qa-request" } } },
      },
    );
    await harness.settle();
    const approve = () =>
      elements(harness.tree).find(
        (item) => item.type === "BotaoInteracao" && /Aceitar e conectar/.test(elementText(item)),
      );
    if (fiscal) {
      assert.equal(approve().props.disabled, true);
      await harness.act(() => approve().props.onClick());
      assert.equal(posts.length, 0);
      await harness.act(() =>
        control(
          harness,
          "Autorizo as permissões fiscais solicitadas para esta empresa",
        ).props.onChange(true),
      );
      assert.equal(approve().props.disabled, false);
    }
    let approving;
    await harness.act(() => {
      approving = approve().props.onClick();
    });
    await harness.act(() => approve()?.props.onClick());
    assert.equal(posts.length, 1);
    assert.deepEqual(posts[0].body, fiscal ? { confirm_fiscal_scopes: true } : undefined);
    finish({ data: {} });
    await approving;
    await harness.settle();
  });
