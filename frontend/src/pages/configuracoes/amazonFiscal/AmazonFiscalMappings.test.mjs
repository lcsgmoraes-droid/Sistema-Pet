import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elements,
  elementText,
} from "../../../../scripts/helpers/reactControllerHarness.mjs";
import * as utils from "./amazonFiscalUtils.js";

test("mapeamento exige SKU exato e seleção explícita de produto/kit existente", async () => {
  const calls = [];
  const api = {
    get: async (path, options) => {
      calls.push({ method: "get", path, options });
      return {
        data: {
          items: path.endsWith("/products")
            ? [{ id: 42, sku: "KIT-LOCAL", name: "Kit de teste", product_type: "kit" }]
            : [],
        },
      };
    },
    post: async (path, body) => {
      calls.push({ method: "post", path, body });
      return { data: {} };
    },
  };
  const harness = createControllerHarness(
    fileURLToPath(new URL("./AmazonFiscalMappings.jsx", import.meta.url)),
    {
      props: { account: { id: 3, seller_id: "QA" }, onChanged: () => {} },
      mocks: new Map([
        ["lucide-react", { Pencil: "Pencil", Search: "Search" }],
        ["../../../services/api", { api }],
        ["./amazonFiscalUtils", utils],
        ...[
          "BotaoCancelar",
          "BotaoInteracao",
          "BotaoSalva",
          "InputCheck",
          "InputCombobox",
          "InputTexto",
          "ModalPadrao",
        ].map((name) => [`../../../components/v2/${name}/${name}`, name]),
      ]),
    },
  );
  assert.match(elementText(harness.tree), /Carregando/);
  await harness.settle();
  const field = (label) => elements(harness.tree).find((item) => item.props?.label === label);
  const save = () => elements(harness.tree).find((item) => item.type === "BotaoSalva");
  await harness.act(() => save().props.onClick());
  assert.equal(
    calls.some((call) => call.method === "post"),
    false,
  );
  await harness.act(() => field("SKU exato na Amazon").props.onChange("Amazon-SKU-QA"));
  await harness.act(() => field("Buscar produto ou kit CorePet").props.onChange("Kit"));
  const search = elements(harness.tree).find(
    (item) => item.type === "BotaoInteracao" && elementText(item) === "Buscar produtos",
  );
  await harness.act(() => search.props.onClick());
  assert.equal(field("Produto ou kit CorePet").props.value, "");
  assert.match(field("Produto ou kit CorePet").props.opcoes[0].label, /KIT-LOCAL.*kit/);
  await harness.act(() => field("Produto ou kit CorePet").props.onChange(42));
  await harness.act(() => save().props.onClick());
  const saved = calls.find((call) => call.method === "post");
  assert.deepEqual(saved.body, {
    account_id: 3,
    seller_sku: "Amazon-SKU-QA",
    product_id: 42,
    active: true,
  });
});
