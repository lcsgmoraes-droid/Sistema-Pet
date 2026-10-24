import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elements,
  elementText,
} from "../../../scripts/helpers/reactControllerHarness.mjs";

const stub = (value) => ({ __esModule: true, default: value });
const money = (value) =>
  value === null || value === undefined
    ? "Não informado"
    : new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(Number(value));
const percent = (value) => (value === null || value === undefined ? "Não informado" : `${value}%`);

function setup(extra = {}) {
  const order = {
    order_id: "homologation-order",
    events: [
      {
        position: 0,
        name: "Taxa de pagamento",
        amount: "-1.20",
        has_transfer_impact: false,
        payment_liability: "MERCHANT",
        billing: { base_value: "80.00", fee_percentage: "1.50" },
      },
    ],
    totals: {
      registered_payments: "80.00",
      fees: "-1.20",
      store_subsidy: "-4.00",
      ifood_subsidy: "2.00",
      transfer_impact: "-1.20",
    },
    manual_costs: null,
    contribution: {
      calculated: false,
      amount: null,
      percent: null,
      missing: ["CMV não informado"],
    },
    pending: ["Custos incompletos"],
  };
  const controller = {
    periodo: { inicio: "2026-10-01", fim: "2026-10-02" },
    periodoValido: true,
    status: { can_sync: false, can_edit_costs: true, message: "Leitura Financial desativada" },
    relatorio: {
      mode: "homologation",
      imported: true,
      begin_date: "2026-10-01",
      end_date: "2026-10-02",
      metadata: { source: "ifood_financial_events", revision: 3 },
      summary: order.totals,
      orders: [order],
      unallocated_events: [],
      warnings: [],
    },
    carregando: false,
    ocupado: false,
    erro: "",
    sucesso: "",
    pedido: null,
    fecharCustos() {},
    alterarPeriodo() {},
    atualizar() {},
    sincronizar() {},
    abrirCustos() {},
    ...extra,
  };
  const controls = [
    "BotaoCancelar",
    "BotaoInteracao",
    "BotaoSalva",
    "CartaoIndicador",
    "EstadoVazio",
    "InputCheck",
    "InputMoeda",
    "InputPeriodo",
    "InputTextoLongo",
    "ModalPadrao",
  ];
  const harness = createControllerHarness(
    fileURLToPath(new URL("./IfoodFinanceiro.jsx", import.meta.url)),
    {
      props: { ativo: true },
      mocks: new Map([
        ...controls.map((name) => [`../v2/${name}/${name}`, stub(name)]),
        ["../ui/DataTable", stub("DataTable")],
        [
          "lucide-react",
          {
            AlertTriangle: "AlertTriangle",
            DollarSign: "DollarSign",
            Eye: "Eye",
            RefreshCw: "RefreshCw",
          },
        ],
        ["../../utils/modalEscape", { useEscapeToClose() {} }],
        ["./useIfoodFinanceiro", stub(() => controller)],
        [
          "./ifoodPresentation",
          {
            moedaIfood: money,
            percentualIfood: percent,
            valorConhecido: (value) => value !== null && value !== undefined,
          },
        ],
      ]),
    },
  );
  async function detail() {
    const table = elements(harness.tree).find((item) => item.type === "DataTable");
    const action = table.props.columns.find((item) => item.key === "acoes").render(order);
    await harness.act(() => action.props.onClick());
    const modal = elements(harness.tree).find((item) => item.props?.order === order);
    return modal.type(modal.props);
  }
  return { harness, controller, order, detail };
}

test("taxa observada usa base e percentual do evento, sem inferir taxa contratual", async () => {
  const env = setup();
  const detail = await env.detail();
  const table = elements(detail).find((item) => item.type === "DataTable");
  const billing = table.props.columns
    .find((item) => item.key === "billing")
    .render(env.order.events[0]);
  assert.match(elementText(billing), /80,00/);
  assert.match(elementText(billing), /1.50%/);
  assert.match(elementText(detail), /Homologação iFood/);
  assert.match(elementText(env.harness.tree), /Eventos importados · conciliação pendente/);
  assert.match(
    elementText(env.harness.tree),
    /Sales, conciliação e repasses completos são etapas seguintes/,
  );
});

test("eventos conhecidos mostram nome português e código secundário sem renomear desconhecidos", async () => {
  const env = setup();
  const table = elements(await env.detail()).find((item) => item.type === "DataTable");
  const nome = table.props.columns.find((item) => item.key === "name");
  for (const [code, label] of [
    ["ORDER_PAYMENT", "Pagamento do pedido"],
    ["ORDER_COMMISSION", "Comissão iFood"],
    ["PAYMENT_TRANSACTION_FEE", "Taxa de pagamento"],
    ["IFOOD_SUBSIDY", "Subsídio do iFood"],
    ["STORE_SUBSIDY", "Promoção da loja"],
  ]) {
    const result = nome.render({ name: code, description: "Descrição original do provedor" });
    const paragraphs = elements(result).filter((item) => item.type === "p");
    assert.equal(elementText(paragraphs[0]), label);
    assert.equal(elementText(paragraphs[1]), code);
    assert.match(elementText(result), /Descrição original do provedor/);
  }
  const desconhecido = nome.render({ name: "FUTURE_EVENT", trigger: "ORDER_CONCLUDED" });
  assert.equal(
    elementText(elements(desconhecido).find((item) => item.type === "p")),
    "FUTURE_EVENT",
  );
  assert.match(elementText(desconhecido), /ORDER_CONCLUDED/);
});

test("pagamento recebido pela loja e impacto no repasse permanecem separados", async () => {
  const env = setup();
  const table = elements(await env.detail()).find((item) => item.type === "DataTable");
  const event = env.order.events[0];
  assert.match(
    elementText(table.props.columns.find((item) => item.key === "payment").render(event)),
    /Recebido pela loja/,
  );
  assert.equal(table.props.columns.find((item) => item.key === "impact").render(event), "Não");
  const summary = elements(env.harness.tree).filter((item) => item.type === "CartaoIndicador");
  assert.equal(summary.length, 5);
  assert.match(
    elementText(summary.find((item) => item.props.titulo === "Impacto informado no repasse")),
    /-.*1,20/,
  );
});

test("custo ausente mantém contribuição desconhecida e dados sintéticos ficam explícitos", async () => {
  const env = setup();
  const detail = await env.detail();
  assert.match(elementText(detail), /CMV não informado/);
  const contribution = elements(detail).find(
    (item) => item.props?.contribution === env.order.contribution,
  );
  assert.match(elementText(contribution.type(contribution.props)), /Não calculada/);
  env.controller.relatorio.metadata.source = "synthetic";
  await env.harness.update({ ativo: true });
  assert.match(
    elementText(env.harness.tree),
    /Dados sintéticos de teste. Não refletem vendas reais/,
  );
});

test("sem relatório não há eventos de demonstração usados como fallback", () => {
  const env = setup({ relatorio: null, erro: "Falha na consulta do servidor" });
  assert.equal(elements(env.harness.tree).filter((item) => item.type === "DataTable").length, 0);
  assert.match(elementText(env.harness.tree), /Falha na consulta do servidor/);
  assert.ok(elements(env.harness.tree).some((item) => item.type === "EstadoVazio"));
});
