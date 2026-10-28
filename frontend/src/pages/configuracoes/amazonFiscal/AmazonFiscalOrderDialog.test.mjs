import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elements,
  elementText,
} from "../../../../scripts/helpers/reactControllerHarness.mjs";
import * as utils from "./amazonFiscalUtils.js";

function setup(order) {
  const actions = [];
  const fiscal = {
    busy: false,
    detail: order,
    reviewHistorical: (value) => actions.push(["review", value.id]),
    issue: () => actions.push(["issue"]),
  };
  const harness = createControllerHarness(
    fileURLToPath(new URL("./AmazonFiscalOrderDialog.jsx", import.meta.url)),
    {
      props: { fiscal },
      mocks: new Map([
        [
          "lucide-react",
          { Download: "Download", Printer: "Printer", RefreshCw: "RefreshCw", Send: "Send" },
        ],
        ...["BotaoCancelar", "BotaoInteracao", "InputCheck", "ModalPadrao"].map((name) => [
          `../../../components/v2/${name}/${name}`,
          name,
        ]),
        ["../../../utils/formatters", { formatMoneyBRL: (value) => `R$ ${value}` }],
        ["./amazonFiscalUtils", utils],
      ]),
    },
  );
  return {
    harness,
    actions,
    button: (text) =>
      elements(harness.tree).find(
        (item) => item.type === "BotaoInteracao" && elementText(item) === text,
      ),
  };
}

test("nota autorizada identifica SEFAZ e mantém aceite Amazon separado", () => {
  const { harness, button } = setup({
    id: 7,
    external_order_id: "QA",
    status: "authorized",
    blockers: [],
    xml_available: true,
    danfe_available: true,
  });
  assert.match(elementText(harness.tree), /Autorizada na SEFAZ/);
  assert.match(elementText(harness.tree), /aceite pela Amazon separadamente/);
  assert.equal(button("Confirmar emissão da NF-e").props.disabled, true);
  assert.equal(button("Baixar XML autorizado").props.disabled, false);
});

test("revisão histórica exige confirmação e nunca dispara emissão por si só", async () => {
  const env = setup({
    id: 7,
    status: "blocked",
    blockers: [{ code: "historical_order_requires_review", message: "Pedido anterior" }],
  });
  const button = () => env.button("Registrar revisão do pedido anterior");
  assert.equal(button().props.disabled, true);
  const consent = elements(env.harness.tree).find((item) => item.type === "InputCheck");
  await env.harness.act(() => consent.props.onChange(true));
  assert.equal(button().props.disabled, false);
  await env.harness.act(() => button().props.onClick());
  assert.deepEqual(env.actions, [["review", 7]]);
});

test("revisão apresenta desconto efetivo e ausência de evidência de pagamento sem inventar valor", () => {
  const { harness } = setup({
    id: 7,
    status: "ready",
    source: { buyer_paid_total: null },
    discount_audit: {
      policy: "buyer_payment_total",
      extra_discount: "1.99",
      effective_discount: "3.99",
    },
  });
  const text = elementText(harness.tree).replaceAll(/\s+/g, " ");
  assert.match(text, /Pagamento documentado pelo comprador: Ainda não recebido/);
  assert.match(text, /Ajustar ao pagamento documentado/);
  assert.match(text, /Desconto adicional rateado: R\$ 1.99/);
  assert.match(text, /Desconto fiscal total: R\$ 3.99/);
});
