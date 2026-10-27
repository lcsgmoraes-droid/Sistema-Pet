import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createControllerHarness } from "../../../scripts/helpers/reactControllerHarness.mjs";

test("fornecedor não exibe ID técnico nem código de documento como código de pessoa", () => {
  const obter = (record) =>
    createControllerHarness(fileURLToPath(new URL("./FornecedorIdentity.jsx", import.meta.url)), {
      exportName: "getFornecedorIdentityCode",
      props: record,
      invoke: (fn, props) => fn(props),
      mocks: new Map([
        ["./CopyableCode", { default: "CopyableCode" }],
        ["./CopyableValue", { default: "CopyableValue" }],
      ]),
    }).tree;
  assert.equal(obter({ fornecedor_id: 999, codigo: "PED-123" }), "");
  assert.equal(obter({ fornecedor: { id: 999, codigo: "2061" } }), "2061");
  assert.equal(obter({ id: 999, codigo: "2061" }), "2061");
});
