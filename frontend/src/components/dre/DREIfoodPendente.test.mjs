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
  assert.equal(amount.render({ campo: "taxas_cartao", valor: 0 }).props.zeroAsDash, false);
  assert.match(
    elementText(amount.render({ ...pendencia, valor: null, valor_conhecido: 6.5 })),
    /Pendente iFood.*Subtotal conhecido:\s*R\$\s*6,50/,
  );
  assert.equal(
    DRE_DETAIL_COLUMNS.find((column) => column.key === "valor").render({
      meta: pendencia,
      valor: null,
    }),
    "Pendente iFood",
  );
  assert.ok(canaisDisponiveis.some((canal) => canal.id === "ifood"));
});

test("DRE mantém pagamento conhecido e detalha taxas por nome mesmo com comissão pendente", () => {
  const financeiro = {
    charges: [
      {
        code: "PAYMENT_TRANSACTION_FEE",
        label: "Taxa de pagamento iFood",
        amount: 0,
        status: "known",
      },
    ],
    pending_components: [{ code: "ORDER_COMMISSION", label: "Comissão iFood" }],
    complete: false,
  };
  const tree = view("demonstrativo", {
    linhaDetalhe: {
      ...pendencia,
      valor: null,
      valor_conhecido: 6.5,
      campo: "taxas_marketplace",
      canal: "ifood",
    },
    detalhesLinha: {
      ...pendencia,
      total: null,
      items: [
        {
          id: "ifood-1420",
          descricao: "Pedido 1420",
          valor: 0,
          meta: { ...pendencia, ifood_financial: financeiro },
        },
      ],
    },
    formatarData: () => "24/10/2026",
  });
  assert.match(elementText(tree), /Subtotal conhecido:\s*R\$\s*6,50.*Apuração pendente/);
  const panel = elements(tree).find((node) => node.props?.financeiro === financeiro);
  assert.ok(panel, "o extrato da DRE reutiliza as cobranças individuais da venda");
  const payment = elements(tree).find(
    (node) => node.type === "ui/MoneyCell" && node.props.value === 0,
  );
  assert.equal(payment.props.zeroAsDash, false);
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
