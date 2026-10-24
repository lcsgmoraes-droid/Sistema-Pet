import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elements,
  elementText,
} from "../../../scripts/helpers/reactControllerHarness.mjs";

function setup(vendaAtual) {
  return createControllerHarness(fileURLToPath(new URL("./PDVEntregaCard.jsx", import.meta.url)), {
    mocks: new Map([
      ["lucide-react", {}],
      ["../CurrencyInput", { __esModule: true, default: "CurrencyInput" }],
      ["../ui/Panel", { __esModule: true, default: "Panel" }],
    ]),
    props: { vendaAtual, entregadores: [], modoVisualizacao: false },
  });
}

test("DELIVERY iFood exibe acompanhamento externo sem seletor ou alteracao de modalidade", () => {
  const sale = { canal: "ifood", tem_entrega: true, entregador_id: null };
  const harness = setup(sale);
  assert.match(elementText(harness.tree), /Entrega acompanhada pelo iFood/);
  assert.equal(
    elements(harness.tree).some((item) => ["input", "textarea", "select"].includes(item.type)),
    false,
  );
  assert.equal(sale.tem_entrega, true);
  assert.equal(sale.entregador_id, null);
});

test("app e ecommerce continuam com campos e seletor de entregador da loja", () => {
  for (const canal of ["app", "ecommerce"]) {
    const harness = setup({ canal, tem_entrega: true, entrega: {} });
    assert.ok(elements(harness.tree).some((item) => item.type === "select"));
    assert.match(elementText(harness.tree), /Selecione um entregador/);
  }
});
