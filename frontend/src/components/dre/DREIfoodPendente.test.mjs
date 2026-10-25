import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elements,
  elementText,
} from "../../../scripts/helpers/reactControllerHarness.mjs";

const pendencia = {
  rentabilidade_status: "pending_ifood_financial",
  taxas_ifood_pendentes: true,
  vendas_rentabilidade_pendente: 1,
};
const mockComponent = (name) => ({ __esModule: true, default: name });

test("colunas DRE distinguem taxa pendente de zero conhecido e identificam canal ifood", () => {
  const harness = createControllerHarness(fileURLToPath(new URL("../DRE.jsx", import.meta.url)), {
    props: {},
    globals: { window: { setTimeout: () => 1 } },
    mocks: new Map([
      ["lucide-react", {}],
      ["react-hot-toast", mockComponent("toast")],
      ["../api", mockComponent("api")],
      ["./ui/MoneyCell", mockComponent("MoneyCell")],
      ["./ui/NumberCell", mockComponent("NumberCell")],
      ["./dre/DREView", mockComponent("DREView")],
    ]),
  });
  const { DRE_TABLE_COLUMNS, DRE_DETAIL_COLUMNS, canaisDisponiveis } = harness.tree.props;
  const amount = DRE_TABLE_COLUMNS.find((column) => column.key === "valor");
  const percent = DRE_TABLE_COLUMNS.find((column) => column.key === "percentual");
  assert.equal(amount.render({ ...pendencia, valor: null }), "Pendente iFood");
  assert.equal(percent.render({ ...pendencia, percentual: null }), "Pendente iFood");
  assert.equal(amount.render({ valor: 0 }).props.value, 0);
  assert.equal(
    DRE_DETAIL_COLUMNS.find((column) => column.key === "valor").render({
      meta: pendencia,
      valor: null,
    }),
    "Pendente iFood",
  );
  assert.ok(canaisDisponiveis.some((canal) => canal.id === "ifood"));
});

function view(tabAtiva, extraProps = {}) {
  const components = [
    "AnaliseInteligente",
    "ChatIAModal",
    "ClassificarLancamentosModal",
    "ExtratoBancario",
    "ui/ActionButton",
    "ui/DataTable",
    "ui/ExportActionButton",
    "ui/LoadingState",
    "ui/MetricCard",
    "ui/MetricGrid",
    "ui/MoneyCell",
    "ui/ModuleTabs",
    "ui/NumberCell",
  ];
  return createControllerHarness(fileURLToPath(new URL("./DREView.jsx", import.meta.url)), {
    props: {
      tabAtiva,
      periodo: "2026-10",
      dados: {
        ...pendencia,
        totais: { receita_bruta: 1500, cmv: 500, lucro_bruto: null, margem_bruta: null },
        linhas: [],
      },
      DRE_TABS: [],
      DRE_TABLE_COLUMNS: [],
      canaisDisponiveis: [],
      canaisSelecionados: [],
      formatarPercentual: String,
      calcularPercentual: () => 0,
      ...extraProps,
    },
    mocks: new Map([
      ["lucide-react", {}],
      ...components.map((name) => [`../${name}`, mockComponent(name)]),
    ]),
  }).tree;
}

test("cards nao apresentam margem final e analise automatica aguarda Financial", () => {
  const tree = view("demonstrativo");
  const cards = elements(tree).filter((node) => node.type === "ui/MetricCard");
  assert.equal(
    cards.find((card) => card.props.label === "Lucro Bruto").props.value,
    "Pendente iFood",
  );
  assert.equal(
    cards.find((card) => card.props.label === "Margem Bruta").props.value,
    "Pendente iFood",
  );
  assert.equal(
    cards.find((card) => card.props.label === "Receita Bruta").props.value.props.value,
    1500,
  );
  assert.match(elementText(tree), /Cobranças ausentes não equivalem a taxa zero/);
  const analysis = view("analise");
  assert.equal(
    elements(analysis).some((node) => node.type === "AnaliseInteligente"),
    false,
  );
  assert.match(elementText(analysis), /análise de rentabilidade será exibida após a conferência/);
});

test("detalhe responsivo le contrato meta do backend e preserva valor desconhecido", () => {
  const tree = view("demonstrativo", {
    linhaDetalhe: { ...pendencia, valor: null, campo: "taxas_cartao", canal: "ifood" },
    detalhesLinha: {
      ...pendencia,
      total: null,
      items: [{ id: "ifood-1420", descricao: "Pedido 1420", valor: null, meta: pendencia }],
    },
    formatarData: () => "24/10/2026",
  });
  const text = elementText(tree);
  assert.match(text, /Pedido 1420.*Pendente iFood/);
  const cells = elements(tree).filter((node) => node.type === "ui/MoneyCell");
  assert.equal(
    cells.some((cell) => cell.props.value == null),
    false,
  );
});
