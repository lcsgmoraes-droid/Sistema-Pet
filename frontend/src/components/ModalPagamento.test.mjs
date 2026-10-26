import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elements,
  elementText,
} from "../../scripts/helpers/reactControllerHarness.mjs";

function render(venda) {
  return createControllerHarness(fileURLToPath(new URL("./ModalPagamento.jsx", import.meta.url)), {
    props: { venda, onClose() {} },
    mocks: new Map([
      ["./ModalPerguntaNFe", { __esModule: true, default: "ModalPerguntaNFe" }],
      ["./modalPagamento/ModalPagamentoView", { __esModule: true, default: "ModalPagamentoView" }],
      [
        "./modalPagamento/useModalPagamentoController",
        {
          __esModule: true,
          default: () => {
            throw new Error("Cobranca nao pode abrir");
          },
        },
      ],
      ["./ifood/IfoodPdvOnlineResumo", { __esModule: true, default: "IfoodPdvOnlineResumo" }],
      ["./v2/BotaoCancelar/BotaoCancelar", { __esModule: true, default: "BotaoCancelar" }],
    ]),
  }).tree;
}

test("abertura direta de modal iFood online ou desconhecido nao oferece nova cobranca", () => {
  for (const summary of [
    { enabled: true, payment_mode: "online" },
    { enabled: false, payment_mode: "unknown" },
    undefined,
  ]) {
    const tree = render({ canal: "ifood", ifood_pdv_pilot: summary });
    assert.match(elementText(tree), /cobrança manual.*bloqueada/);
    assert.equal(
      elements(tree).some((node) => ["ModalPagamentoView", "input", "select"].includes(node.type)),
      false,
    );
    assert.ok(elements(tree).some((node) => node.type === "BotaoCancelar"));
  }
});

test("modal padrao continua para app, ecommerce e iFood offline autorizado", () => {
  for (const venda of [
    { canal: "app" },
    { canal: "ecommerce" },
    { canal: "ifood", ifood_pdv_pilot: { enabled: true, payment_mode: "offline" } },
  ]) {
    assert.equal(typeof render(venda).type, "function");
  }
});
