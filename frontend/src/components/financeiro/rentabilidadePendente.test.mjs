import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  ajustarVendaImposto,
  calcularAnaliseInteligenteVendas,
  calcularDistribuicaoTemporalVendasFinanceiro,
  calcularTotalizadoresListaVendasFinanceiro,
  COLUNAS_RELATORIO_VENDAS,
  montarCardsTotalizadoresListaVendasFinanceiro,
  montarFluxoResultadoCardsFinanceiro,
  ordenarVendasRelatorio,
} from "./vendasFinanceiroUtils.js";
import {
  PENDENCIA_IFOOD_LABEL,
  temRentabilidadePendente,
} from "./vendasFinanceiro/rentabilidadePendente.js";
import {
  createControllerHarness,
  elements,
  elementText,
} from "../../../scripts/helpers/reactControllerHarness.mjs";
import { calculateDashboardIndicators } from "../../pages/dashboard/dashboardOverview.js";

const pendente = {
  id: 1420,
  status: "finalizada",
  data_venda: "2026-10-24T20:43:00-03:00",
  rentabilidade_status: "pending_ifood_financial",
  taxas_ifood_pendentes: true,
  venda_bruta: 65,
  custo_produtos: 40,
  imposto: 3,
  taxa_cartao: null,
  venda_liquida: null,
  lucro: null,
  margem_sobre_venda: null,
  margem_sobre_custo: null,
  itens: [
    {
      taxas_ifood_pendentes: true,
      venda_bruta: 65,
      custo_total: 40,
      imposto: 3,
      valor_liquido: null,
      lucro: null,
      lucro_unitario: null,
      margem_sobre_venda: null,
      margem_sobre_custo: null,
    },
  ],
};
const completa = {
  id: 2,
  venda_bruta: 100,
  custo_produtos: 50,
  venda_liquida: 90,
  lucro: 40,
  taxa_cartao: 5,
};

test("pendência explícita distingue taxa desconhecida de zero confirmado", () => {
  assert.equal(temRentabilidadePendente(pendente), true);
  assert.equal(temRentabilidadePendente({ vendas_rentabilidade_pendente: 1 }), true);
  assert.equal(
    temRentabilidadePendente({ rentabilidade_status: "complete", taxa_cartao: 0 }),
    false,
  );
  assert.equal(temRentabilidadePendente(null), false);
});

test("total misto permanece pendente sem esconder faturamento, quantidade ou CMV", () => {
  const total = calcularTotalizadoresListaVendasFinanceiro([completa, pendente]);
  assert.equal(total.quantidade, 2);
  assert.equal(total.venda_bruta, 165);
  assert.equal(total.custo_produtos, 90);
  assert.equal(total.vendas_rentabilidade_pendente, 1);
  for (const campo of [
    "taxa_cartao",
    "venda_liquida",
    "lucro",
    "margem_sobre_venda",
    "margem_sobre_custo",
  ])
    assert.equal(total[campo], null, campo);
  const cards = montarCardsTotalizadoresListaVendasFinanceiro(total);
  for (const label of ["Tx. Pagto", "Liquida", "Lucro", "MG Venda", "MG Custo"])
    assert.equal(cards.find((card) => card.label === label).value, PENDENCIA_IFOOD_LABEL);
  const somenteCompleta = calcularTotalizadoresListaVendasFinanceiro([completa]);
  assert.equal(somenteCompleta.lucro, 40);
  assert.equal(somenteCompleta.taxa_cartao, 5);
});

test("mostrar e ocultar imposto não transforma margem pendente em resultado calculado", () => {
  for (const mostrar of [false, true]) {
    const venda = ajustarVendaImposto(pendente, mostrar);
    for (const campo of ["venda_liquida", "lucro", "margem_sobre_venda", "margem_sobre_custo"])
      assert.equal(venda[campo], null, campo);
    assert.equal(venda.itens[0].valor_liquido, null);
    assert.equal(venda.itens[0].lucro, null);
    assert.equal(venda.imposto, mostrar ? 3 : 0);
  }
});

test("ordenação de lucro mantém pendentes fora do ranking numérico em ambas direções", () => {
  const negativa = { id: 3, lucro: -10 };
  assert.deepEqual(
    ordenarVendasRelatorio([pendente, completa, negativa], "lucro_desc").map((v) => v.id),
    [2, 3, 1420],
  );
  assert.deepEqual(
    ordenarVendasRelatorio([pendente, completa, negativa], "lucro_asc").map((v) => v.id),
    [3, 2, 1420],
  );
});

test("Excel distingue pendência de custo zero sem alterar colunas comerciais", () => {
  for (const campo of [
    "taxa_cartao",
    "venda_liquida",
    "lucro",
    "margem_sobre_venda",
    "margem_sobre_custo",
  ]) {
    const coluna = COLUNAS_RELATORIO_VENDAS.find((c) => c.key === campo);
    assert.equal(coluna.value(pendente), PENDENCIA_IFOOD_LABEL);
    assert.equal(coluna.value({ rentabilidade_status: "complete", [campo]: 0 }), 0);
  }
  assert.equal(COLUNAS_RELATORIO_VENDAS.find((c) => c.key === "venda_bruta").value(pendente), 65);
});

test("composição renderiza pendência em vez de R$0 ou0% e preserva custos conhecidos", () => {
  const resumo = {
    ...pendente,
    vendas_rentabilidade_pendente: 1,
    lucro_total: null,
    margem_media: null,
    taxa_cartao_total: null,
    custo_total: 40,
  };
  const cards = montarFluxoResultadoCardsFinanceiro(resumo);
  for (const titulo of ["Cartao", "Venda Liquida", "Lucro", "Margem"]) {
    const card = cards.find((c) => c.titulo === titulo);
    assert.equal(card.valor, null);
    assert.equal(card.pendente, true);
  }
  const tree = createControllerHarness(
    fileURLToPath(new URL("./VendasResultadoComposicaoPanel.jsx", import.meta.url)),
    {
      mocks: new Map(),
      props: { resumo, fluxoResultadoCards: cards, formatarMoeda: (v) => `money:${v}` },
    },
  ).tree;
  assert.match(elementText(tree), /Pendente iFood/);
  assert.match(elementText(tree), /money:65/);
  assert.match(elementText(tree), /money:40/);
  assert.doesNotMatch(elementText(tree), /money:null|null%/);
});

test("célula financeira protege lucro e percentual e volta a exibir zero conhecido", async () => {
  const harness = createControllerHarness(
    fileURLToPath(new URL("./RentabilidadeCell.jsx", import.meta.url)),
    {
      mocks: new Map([
        ["../ui/MoneyCell", { __esModule: true, default: "money-cell" }],
        ["../ui/NumberCell", { __esModule: true, default: "number-cell" }],
      ]),
      props: { dados: pendente, percentual: true, value: null },
    },
  );
  assert.equal(elementText(harness.tree), PENDENCIA_IFOOD_LABEL);
  await harness.update({ dados: { rentabilidade_status: "complete", taxa_cartao: 0 }, value: 0 });
  assert.equal(harness.tree.type, "number-cell");
  assert.equal(harness.tree.props.value, 0);
});

test("análise de produtos não inventa lucro nem alerta de baixa margem para iFood pendente", () => {
  const produtos = [
    {
      nome: "iFood pendente",
      categoria: "Ração",
      quantidade: 1,
      valor_total: 65,
      custo_total: 40,
      taxas_ifood_pendentes: true,
    },
    {
      nome: "Loja conhecida",
      categoria: "Ração",
      quantidade: 1,
      valor_total: 100,
      custo_total: 50,
    },
  ];
  const analise = calcularAnaliseInteligenteVendas({ produtosAnalise: produtos });
  assert.deepEqual(
    analise.produtosMaisLucrativos.map((p) => p.nome),
    ["Loja conhecida"],
  );
  assert.equal(analise.produtosPorCategoria.Ração.total, 165);
  assert.equal(analise.produtosPorCategoria.Ração.quantidade, 2);
  assert.equal(analise.produtosPorCategoria.Ração.margem_media, null);
  assert.equal(
    analise.alertasInteligentesVendas.some((a) => a.id === "mix-baixa-margem"),
    false,
  );
});

test("distribuição derivada de snapshots não soma líquido pendente como zero", () => {
  const analise = calcularDistribuicaoTemporalVendasFinanceiro([pendente]);
  const dia = analise.vendasPorDiaSemanaResumo.find((item) => item.quantidade === 1);
  assert.equal(dia.valor_bruto, 65);
  assert.equal(dia.valor_liquido, null);
  assert.equal(dia.ticket_medio, null);
  assert.equal(analise.vendasPorHorarioComMovimento[0].valor_liquido, null);
  assert.equal(temRentabilidadePendente(analise.melhorDiaSemana), true);
});

test("gráfico não anuncia dia vencedor ou zero vendas quando o líquido está pendente", () => {
  const analise = calcularDistribuicaoTemporalVendasFinanceiro([pendente]);
  const tree = createControllerHarness(
    fileURLToPath(new URL("./VendasFinanceiroGraficosResumo.jsx", import.meta.url)),
    {
      mocks: new Map([
        [
          "recharts",
          Object.fromEntries(
            [
              "Bar",
              "BarChart",
              "CartesianGrid",
              "Cell",
              "Legend",
              "Line",
              "LineChart",
              "ResponsiveContainer",
              "Tooltip",
              "XAxis",
              "YAxis",
            ].map((nome) => [nome, nome]),
          ),
        ],
      ]),
      props: {
        ...analise,
        mostrarGraficos: true,
        formasRecebimentoFiltradas: [],
        produtosDetalhadosFiltrados: [],
        vendasPorDataCalendario: [],
        formatarMoeda: (v) => `money:${v}`,
      },
    },
  ).tree;
  const texto = elementText(tree);
  assert.match(texto, /Melhor dia: Pendente iFood/);
  assert.match(texto, /Pico: Pendente iFood/);
  assert.doesNotMatch(texto, /0 venda\(s\)|money:null/);
});

test("dashboard distingue lucro pendente de resultado de caixa e retorna ao conhecido", () => {
  const summary = {
    vendas_periodo: { quantidade: 1, lucro: null, vendas_rentabilidade_pendente: 1 },
    fluxo_periodo: { entradas: 50, saidas: 20, lucro: 30 },
  };
  const indicadores = calculateDashboardIndicators(summary);
  assert.equal(indicadores.salesProfit, null);
  assert.equal(indicadores.salesProfitPending, true);
  assert.equal(indicadores.cashResult, 30);
  assert.equal(
    calculateDashboardIndicators({
      ...summary,
      vendas_periodo: { lucro: 0, rentabilidade_status: "complete" },
    }).salesProfit,
    0,
  );
});

function resolverComponentes(node) {
  if (Array.isArray(node)) return node.map(resolverComponentes);
  if (!node || typeof node !== "object") return node;
  if (typeof node.type === "function") return resolverComponentes(node.type(node.props));
  return { ...node, props: { ...node.props, children: resolverComponentes(node.props?.children) } };
}

test("lista e detalhes mostram iFood e pendência sem formatar nulos como dinheiro", () => {
  const mocks = new Map([
    ["../../utils/pdvFiscalStatus", { obterPendenciaCancelamentoFiscal: () => null }],
    [
      "lucide-react",
      {
        AlertCircle: "alert",
        CheckCircle2: "check",
        ChevronDown: "down",
        ChevronRight: "right",
        CreditCard: "card",
        ExternalLink: "external",
        RefreshCw: "refresh",
        ShoppingCart: "cart",
        Smartphone: "phone",
        Store: "store",
      },
    ],
    ...[
      "DataTable",
      "CustomerIdentity",
      "MoneyCell",
      "NumberCell",
      "SaleReference",
      "StatusBadge",
      "ProductIdentity",
    ].map((nome) => [`../ui/${nome}`, { __esModule: true, default: nome }]),
  ]);
  const tree = createControllerHarness(
    fileURLToPath(new URL("./VendasFinanceiroListaTable.jsx", import.meta.url)),
    {
      mocks,
      props: {
        vendas: [{ ...pendente, canal_venda: "ifood" }],
        vendasExpandidas: new Set([pendente.id]),
        formatarMoeda: (v) => `money:${v}`,
      },
    },
  ).tree;
  const venda = tree.props.data[0];
  for (const key of ["taxa_cartao", "venda_liquida", "lucro", "margem_venda", "margem_custo"]) {
    const cell = tree.props.columns.find((coluna) => coluna.key === key).render(venda);
    assert.equal(elementText(resolverComponentes(cell)), PENDENCIA_IFOOD_LABEL, key);
  }
  assert.match(
    elementText(
      resolverComponentes(
        tree.props.columns.find((coluna) => coluna.key === "codigo").render(venda),
      ),
    ),
    /iFood/,
  );
  const detalhes = resolverComponentes(tree.props.renderExpandedRow(venda, 0, 20));
  assert.equal((elementText(detalhes).match(/Pendente iFood/g) || []).length, 5);
  assert.doesNotMatch(elementText(detalhes), /money:null|null%/);
});

test("comparação financeira preserva nulos no gráfico e não calcula variação do líquido pendente", () => {
  const resumo = { ...pendente, quantidade_vendas: 1, valor_recebido: 65, em_aberto: 0 };
  const mocks = new Map([
    ["lucide-react", { ArrowDown: "arrow-down", ArrowUp: "arrow-up" }],
    [
      "recharts",
      Object.fromEntries(
        [
          "Bar",
          "BarChart",
          "CartesianGrid",
          "Cell",
          "Legend",
          "Pie",
          "PieChart",
          "ResponsiveContainer",
          "Tooltip",
          "XAxis",
          "YAxis",
        ].map((nome) => [nome, nome]),
      ),
    ],
    ["./VendasComparativoPeriodoTable", { __esModule: true, default: "table" }],
  ]);
  const tree = createControllerHarness(
    fileURLToPath(new URL("./VendasComparacaoPanel.jsx", import.meta.url)),
    {
      mocks,
      props: {
        tipoComparacao: "financeiro",
        resumo,
        resumoComparacao: {
          quantidade_vendas: 1,
          venda_bruta: 100,
          venda_liquida: 90,
          em_aberto: 0,
        },
        calcularVariacao: (atual, anterior) => {
          assert.notEqual(atual, null);
          assert.notEqual(anterior, null);
          return { valor: 0, percentual: 0 };
        },
        formatarMoeda: (v) => `money:${v}`,
        formatarData: String,
        getTextoComparacao: () => "Anterior",
        formasRecebimentoConsolidadas: [],
        formasRecebimentoComparacaoConsolidadas: [],
        vendasPorFuncionario: [],
        vendasPorFuncionarioComparacao: [],
      },
    },
  ).tree;
  const resolved = resolverComponentes(tree);
  assert.match(elementText(resolved), /Pendente iFood/);
  assert.doesNotMatch(elementText(resolved), /money:null/);
  const chart = elements(resolved).find((node) => node.type === "BarChart");
  assert.equal(chart.props.data.find((item) => item.nome === "Vl. Liquido (mil)").Atual, null);
  assert.equal(chart.props.data.find((item) => item.nome === "Vl. Bruto (mil)").Atual, 0.065);
});
