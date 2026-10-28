import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elements,
  elementText,
} from "../../../scripts/helpers/reactControllerHarness.mjs";

const pending = {
  rentabilidade_status: "pending_ifood_financial",
  taxas_ifood_pendentes: true,
  vendas_rentabilidade_pendente: 1,
  status: "pending_ifood_financial",
  faturamento: 1500,
  margem_contribuicao: null,
  margem_contribuicao_percentual: null,
  margem_usada_percentual: null,
  margem_periodo_percentual: null,
  ponto_equilibrio: null,
  percentual_atingido: null,
  taxas_cartao: null,
  despesas_variaveis: null,
  custos_variaveis: null,
  despesas_fixas: 200,
  cmv_estimado: 500,
  ticket_medio: 150,
  quantidade_vendas: 10,
};
const localPath = (name) => fileURLToPath(new URL(name, import.meta.url));

test("ponto de equilibrio preserva pendencia, faturamento e custos conhecidos", () => {
  const harness = createControllerHarness(localPath("./PontoEquilibrioResumoTab.jsx"), {
    props: { dados: pending, margemPeriodoPercentual: null, margemUsadaPercentual: null },
    mocks: new Map([
      ["lucide-react", {}],
      ["./PontoEquilibrioMetricCard", { __esModule: true, default: "MetricCard" }],
      ["./DetalhamentoMargemPanel", { __esModule: true, default: "Detalhamento" }],
    ]),
  });
  const cards = elements(harness.tree).filter((node) => node.type === "MetricCard");
  assert.equal(
    cards.find((card) => card.props.title === "Ponto minimo").props.value,
    "Pendente iFood",
  );
  assert.equal(
    cards.find((card) => card.props.title === "Margem usada").props.value,
    "Pendente iFood",
  );
  assert.equal(cards.find((card) => card.props.title === "Faturamento").props.value, "R$ 1.500,00");
  assert.match(elementText(harness.tree), /Cartao:.*Pendente iFood/);
  assert.match(elementText(harness.tree), /500,00/);
});

test("detalhamento mantem linha desconhecida visivel e nao mostra taxa zero", () => {
  const dados = {
    ...pending,
    detalhes_margem: {
      subtotais: [
        { id: "taxas_cartao", label: "Taxas", valor: null, tipo: "deducao" },
        { id: "cmv", label: "CMV", valor: 500, tipo: "deducao" },
      ],
    },
  };
  const harness = createControllerHarness(localPath("./DetalhamentoMargemPanel.jsx"), {
    mocks: new Map([
      [
        "../../components/v2/BotaoInteracao/BotaoInteracao",
        { __esModule: true, default: "BotaoInteracao" },
      ],
    ]),
    props: { dados },
  });
  const text = elementText(harness.tree);
  assert.match(text, /Taxas.*Pendente iFood/);
  assert.match(text, /CMV.*500,00/);
});

test("PE separa taxa iFood parcial do pagamento conhecido zero e preserva demais custos", () => {
  const dados = { ...pending, taxas_cartao: 0, taxas_ifood: null, taxas_ifood_conhecidos: 6.5 };
  const harness = createControllerHarness(localPath("./PontoEquilibrioResumoTab.jsx"), {
    props: { dados, margemPeriodoPercentual: null, margemUsadaPercentual: null },
    mocks: new Map([
      ["lucide-react", {}],
      ["./PontoEquilibrioMetricCard", { __esModule: true, default: "MetricCard" }],
      ["./DetalhamentoMargemPanel", { __esModule: true, default: "Detalhamento" }],
    ]),
  });
  const text = elementText(harness.tree);
  assert.match(text, /Cartao:\s*R\$\s*0,00/);
  assert.match(text, /Taxas iFood:\s*R\$\s*6,50 \(subtotal conhecido; apuração pendente\)/);
  assert.match(text, /500,00/);

  const detalhes = createControllerHarness(localPath("./DetalhamentoMargemPanel.jsx"), {
    props: {
      dados: {
        ...dados,
        detalhes_margem: {
          subtotais: [
            {
              id: "taxas_ifood",
              label: "Comissão iFood",
              valor: null,
              valor_conhecido: 6.5,
              tipo: "deducao",
            },
            { id: "taxas_cartao", label: "Pagamento iFood", valor: 0, tipo: "deducao" },
          ],
        },
      },
    },
    mocks: new Map([
      [
        "../../components/v2/BotaoInteracao/BotaoInteracao",
        { __esModule: true, default: "BotaoInteracao" },
      ],
    ]),
  });
  assert.match(
    elementText(detalhes.tree),
    /Comissão iFood.*6,50.*subtotal conhecido.*Pagamento iFood.*0,00/,
  );
});

test("PE usa DTO de taxas no detalhe sem esconder taxa zero comprovada", () => {
  const financeiro = {
    charges: [{ label: "Taxa de pagamento iFood", amount: 0, status: "known" }],
    pending_components: [{ code: "ORDER_COMMISSION", label: "Comissão iFood" }],
  };
  const harness = createControllerHarness(localPath("./DetalhesPontoEquilibrioDrawer.jsx"), {
    props: {
      linha: { grupo: "taxas_cartao", label: "Pagamento", valor: 0 },
      detalhes: {
        total: 0,
        total_itens: 1,
        items: [{ id: 1420, descricao: "Pedido 1420", valor: 0, ifood_financial: financeiro }],
        pages: 1,
      },
    },
    mocks: new Map([
      ["lucide-react", {}],
      [
        "../../components/v2/BotaoCancelar/BotaoCancelar",
        { __esModule: true, default: "BotaoCancelar" },
      ],
      [
        "../../components/v2/BotaoInteracao/BotaoInteracao",
        { __esModule: true, default: "BotaoInteracao" },
      ],
    ]),
  });
  assert.match(elementText(harness.tree), /Pedido 1420.*R\$\s*0,00/);
  assert.ok(elements(harness.tree).some((node) => node.props?.financeiro === financeiro));
});

test("detalhamento PE conserva créditos de taxas com sinal de entrada, débito, zero e pendência", () => {
  for (const [valor, esperado] of [
    [3, "- R$ 3,00"],
    [0, "- R$ 0,00"],
    [-3, "+ R$ 3,00"],
    [null, "Pendente iFood"],
  ]) {
    const harness = createControllerHarness(localPath("./DetalhamentoMargemPanel.jsx"), {
      props: {
        dados: {
          ...pending,
          detalhes_margem: {
            subtotais: [
              { id: "taxas_ifood", label: "Comissão iFood", valor, tipo: "deducao" },
              { id: "taxas_cartao", label: "Pagamento iFood", valor, tipo: "deducao" },
            ],
          },
        },
      },
      mocks: new Map([
        [
          "../../components/v2/BotaoInteracao/BotaoInteracao",
          { __esModule: true, default: "BotaoInteracao" },
        ],
      ]),
    });
    for (const key of ["taxas_ifood", "taxas_cartao"]) {
      const row = elements(harness.tree).find((node) => node.key === key);
      assert.ok(elementText(row).replace(/\s+/g, " ").includes(esperado), `${key}: ${valor}`);
    }
  }
});

test("progresso desconhecido nao aparece como zero por cento", () => {
  const harness = createControllerHarness(localPath("./PontoEquilibrioStatusSummary.jsx"), {
    props: {
      dados: pending,
      percentualAtingido: null,
      statusResumo: {
        tone: "amber",
        title: "Pendente iFood",
        text: "Cobranças pendentes",
      },
    },
    mocks: new Map(),
  });
  assert.match(elementText(harness.tree), /Pendente iFood/);
  assert.doesNotMatch(elementText(harness.tree), /0%|0,00%/);
});

test("controller nao usa margem antiga para simular enquanto Financial estiver pendente", async () => {
  const dados = { ...pending, margem_usada_percentual: 50 };
  const harness = createControllerHarness(localPath("./usePontoEquilibrioController.js"), {
    props: {},
    mocks: new Map([
      ["../../api", { __esModule: true, default: { get: async () => ({ data: dados }) } }],
    ]),
  });
  await harness.settle();
  assert.equal(harness.tree.dados.faturamento, 1500);
  assert.equal(harness.tree.margemUsadaPercentual, null);
  assert.equal(harness.tree.margemPeriodoPercentual, null);
  assert.equal(harness.tree.percentualAtingido, null);
  assert.equal(harness.tree.impactoSimulado, null);
  assert.equal(harness.tree.statusResumo.title, "Pendente iFood");
});

test("zero conhecido continua numerico para periodos sem pendencia", () => {
  const harness = createControllerHarness(localPath("./pontoEquilibrioUtils.js"), {
    mocks: new Map(),
    props: 0,
    exportName: "valorPontoEquilibrio",
    invoke: (format) => format(0, { rentabilidade_status: "complete" }),
  });
  assert.equal(harness.tree, "R$ 0,00");
});
