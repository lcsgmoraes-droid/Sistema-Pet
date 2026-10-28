import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elements,
  elementText,
} from "../../../scripts/helpers/reactControllerHarness.mjs";

test("modal apresenta o mesmo bruto, limite de desconto e liquido que serao salvos", () => {
  const item = {
    quantidade: 1.538,
    preco_unitario: 13,
    preco: 13,
    subtotal: 20,
    desconto_valor: 0,
    tipoDesconto: "valor",
    descontoValor: 2,
  };
  const CurrencyInput = "currency-input";
  const preparar = (itemEditando) =>
    createControllerHarness(fileURLToPath(new URL("./PDVDescontoItemModal.jsx", import.meta.url)), {
      props: { itemEditando },
      mocks: new Map([
        ["lucide-react", { X: "icon" }],
        ["../../utils/mediaUrl", { resolveMediaUrl: () => null }],
        ["../CurrencyInput", { __esModule: true, default: CurrencyInput }],
      ]),
    }).tree;
  const tree = preparar(item);
  assert.ok(elements(tree).some((node) => node.props?.readOnly && node.props.value === "20,00"));
  assert.ok(
    elements(tree).some((node) => node.type === CurrencyInput && node.props.maxValue === 20),
  );
  assert.ok(elementText(tree).includes("18,00"));
  const precoAlterado = preparar({ ...item, preco: 14 });
  assert.ok(
    elements(precoAlterado).some((node) => node.props?.readOnly && node.props.value === "21,53"),
  );
});
