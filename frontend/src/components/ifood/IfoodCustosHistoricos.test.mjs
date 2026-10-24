import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elements,
  elementText,
} from "../../../scripts/helpers/reactControllerHarness.mjs";

const stub = (value) => ({ __esModule: true, default: value });
function setup(order, extra = {}) {
  const controls = [
    "BotaoInteracao",
    "InputCheck",
    "InputCombobox",
    "InputTexto",
    "InputTextoLongo",
  ];
  const vinculo = {
    sales: [],
    vendaId: "",
    busca: "",
    sourceNote: "",
    confirmado: false,
    ocupado: false,
    podeEditar: true,
    ...extra,
  };
  const harness = createControllerHarness(
    fileURLToPath(new URL("./IfoodCustosHistoricos.jsx", import.meta.url)),
    {
      props: { order, vinculo },
      mocks: new Map([
        ...controls.map((name) => [`../v2/${name}/${name}`, stub(name)]),
        ["../ui/DataTable", stub("DataTable")],
        ["lucide-react", {}],
        [
          "./ifoodPresentation",
          {
            moedaIfood: (value) =>
              value === null || value === undefined ? "Não informado" : `R$ ${value}`,
          },
        ],
      ]),
    },
  );
  return { harness, vinculo };
}

test("CMV histórico total usa prova enviada pelo servidor e não preenche campos manuais", () => {
  const env = setup({
    effective_cmv: "60.00",
    effective_cmv_source: "erp_original_stock_out",
    historical_cost: {
      status: "verified",
      cmv: "60.00",
      sale: { id: 42, number: 100, date: "2025-08-01", status: "finalizada" },
      items: [
        {
          sale_item_id: 1,
          product_id: 3,
          quantity: 2,
          cost: "60.00",
          status: "verified",
          missing: [],
        },
      ],
      missing: [],
    },
  });
  assert.match(elementText(env.harness.tree), /CMV histórico automático do ERP\s+·\s+R\$ 60.00/);
  const table = elements(env.harness.tree).find((item) => item.type === "DataTable");
  assert.equal(
    table.props.columns.find((item) => item.key === "cost").render(table.props.data[0]),
    "R$ 60.00",
  );
  assert.equal(
    table.props.columns.find((item) => item.key === "quantity").render({ quantity: "1.000" }),
    "1",
  );
  assert.equal(
    table.props.columns.find((item) => item.key === "quantity").render({ quantity: "1.500" }),
    "1,5",
  );
  assert.equal(
    elements(env.harness.tree).some((item) => item.type === "InputMoeda"),
    false,
  );
});

test("CMV manual zero preserva origem e histórico pendente exibe motivo de bloqueio", () => {
  const env = setup({
    effective_cmv: "0.00",
    effective_cmv_source: "manual",
    historical_cost: { status: "pending", cmv: null, missing: ["Custo original da saída ausente"] },
  });
  assert.match(elementText(env.harness.tree), /CMV informado manualmente\s+·\s+R\$ 0.00/);
  assert.match(elementText(env.harness.tree), /Custo original da saída ausente/);
  assert.match(elementText(env.harness.tree), /Custo atual do produto não substitui o histórico/);
});

test("venda candidata com pendências bloqueia confirmação e mantém justificativa", () => {
  const env = setup(
    { effective_cmv: null },
    {
      vendaId: 42,
      sourceNote: "Justificativa em edição",
      sales: [{ venda_id: 42, numero: 100, linkable: false, missing: ["Venda cancelada"] }],
    },
  );
  assert.match(elementText(env.harness.tree), /Venda cancelada/);
  const confirm = elements(env.harness.tree).find(
    (item) =>
      item.type === "BotaoInteracao" && elementText(item) === "Confirmar vínculo com venda ERP",
  );
  assert.equal(confirm.props.disabled, true);
  assert.equal(
    elements(env.harness.tree).find((item) => item.type === "InputTextoLongo").props.value,
    "Justificativa em edição",
  );
});
