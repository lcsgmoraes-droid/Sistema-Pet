import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elements,
  elementText,
} from "../../../scripts/helpers/reactControllerHarness.mjs";

function prepare(vendaAtual) {
  let openings = 0;
  const harness = createControllerHarness(
    fileURLToPath(new URL("./PDVHeaderBar.jsx", import.meta.url)),
    {
      props: {
        vendaAtual: { status: "aberta", ...vendaAtual },
        searchVendaQuery: "",
        temCaixaAberto: true,
        loading: false,
        onAbrirModalPagamento: () => openings++,
      },
      mocks: new Map([
        ["lucide-react", {}],
        ["../MenuCaixa", { __esModule: true, default: "MenuCaixa" }],
        ["../ui/ActionButton", { __esModule: true, default: "ActionButton" }],
        ["../ui/IconActionButton", { __esModule: true, default: "IconActionButton" }],
        ["../ui/PageHeader", { __esModule: true, default: "PageHeader" }],
        ["../v2/BotaoInteracao/BotaoInteracao", { __esModule: true, default: "BotaoInteracao" }],
      ]),
    },
  );
  return { harness, openings: () => openings };
}

test("cabecalho online ou desconhecido nao oferece registrar recebimento", () => {
  for (const summary of [
    { enabled: true, payment_mode: "online" },
    { enabled: false, payment_mode: "unknown" },
    undefined,
  ]) {
    const env = prepare({ canal: "ifood", ifood_pdv_pilot: summary });
    const button = elements(env.harness.tree).find((node) => node.type === "BotaoInteracao");
    assert.equal(button.props.disabled, true);
    assert.equal(button.props.onClick, undefined);
    assert.equal(env.openings(), 0);
    assert.match(
      elementText(button),
      summary?.payment_mode === "online"
        ? /Pagamento online no iFood/
        : /Pagamento iFood a conferir/,
    );
    assert.doesNotMatch(elementText(env.harness.tree), /Registrar Recebimento/);
  }
});

test("cabecalho preserva recebimento de app ecommerce e iFood offline autorizado", () => {
  for (const venda of [
    { canal: "app" },
    { canal: "ecommerce" },
    { canal: "ifood", ifood_pdv_pilot: { enabled: true, payment_mode: "offline" } },
  ]) {
    const env = prepare(venda);
    const button = elements(env.harness.tree).find(
      (node) => node.type === "ActionButton" && elementText(node).includes("Registrar Recebimento"),
    );
    assert.ok(button);
    assert.equal(button.props.disabled, false);
    button.props.onClick();
    assert.equal(env.openings(), 1);
  }
});
