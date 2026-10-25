import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createControllerHarness } from "../../../scripts/helpers/reactControllerHarness.mjs";

function setup() {
  const requests = [];
  let latestRefresh, autoEnabled;
  const period = { start: "2026-10-24", end: "2026-10-24", quickFilter: "personalizado" };
  const search = new URLSearchParams();
  const storage = new Map();
  const harness = createControllerHarness(
    fileURLToPath(new URL("../VendasFinanceiro.jsx", import.meta.url)),
    {
      exportName: "VendasFinanceiroPorVenda",
      props: {},
      mocks: new Map([
        [
          "react-hot-toast",
          { __esModule: true, default: { error() {}, success() {}, loading() {} } },
        ],
        ["react-router-dom", { useNavigate: () => () => {}, useSearchParams: () => [search] }],
        [
          "../api",
          {
            __esModule: true,
            default: {
              get(path, config) {
                return new Promise((resolve, reject) =>
                  requests.push({ path, config, resolve, reject }),
                );
              },
            },
          },
        ],
        ["../contexts/AuthContext", { useAuth: () => ({ user: { is_admin: true } }) }],
        ["./financeiro/VendasFinanceiroView", { __esModule: true, default: "report-view" }],
        ["./financeiro/VisaoVendasFinanceiro", { __esModule: true, default: "commercial-view" }],
        ["../pages/dashboard/dashboardOverview", { getDashboardPeriodFromSearch: () => period }],
        [
          "../hooks/useIfoodFinancialReportRefresh.js",
          {
            __esModule: true,
            default({ enabled, refresh }) {
              autoEnabled = enabled;
              latestRefresh = refresh;
            },
          },
        ],
        [
          "./financeiro/vendasFinanceiro/useVendasFinanceiroActions",
          {
            useVendasFinanceiroActions(props) {
              return {
                toggleSelecaoVenda(id) {
                  props.setVendasSelecionadasIds((previous) => new Set([...previous, id]));
                },
              };
            },
          },
        ],
        [
          "./ui/MoneyCell",
          {
            formatMoneyCellValue: (value) => `money:${value}`,
            isZeroMoneyValue: (value) => Number(value || 0) === 0,
          },
        ],
        ["write-excel-file/browser", { __esModule: true, default: async () => ({ toFile() {} }) }],
      ]),
      globals: {
        window: {
          localStorage: {
            getItem: (key) => storage.get(key) || null,
            setItem: (key, value) => storage.set(key, value),
          },
        },
        document: { addEventListener() {}, removeEventListener() {} },
        console: { error() {} },
      },
    },
  );
  const report = (extra = {}) => ({
    resumo: { venda_bruta: 65, vendas_rentabilidade_pendente: 1 },
    lista_vendas: [
      {
        id: 1420,
        numero_venda: "202610240002",
        data_venda: "2026-10-24T20:53:00",
        venda_bruta: 65,
        custo_produtos: 40,
        canal: "ifood",
        itens: [],
        ifood_financial: { charges: [], complete: false },
        ...extra,
      },
    ],
  });
  return {
    harness,
    requests,
    report,
    refresh: () => latestRefresh(),
    enabled: () => autoEnabled,
    async resolveLatest(extra) {
      requests.at(-1).resolve({ data: report(extra) });
      await harness.settle();
    },
  };
}

test("Financial atualizado relê somente GET ERP sem loading nem perder edição, seleção e expansão", async () => {
  const env = setup();
  await env.resolveLatest();
  assert.equal(env.harness.tree.type, "report-view");
  await env.harness.act(() => {
    const props = env.harness.tree.props;
    props.setAbaAtiva("lista");
    props.setFiltroFormaPagamento("iFood online");
    props.toggleVendaExpandida(1420);
    props.toggleSelecaoVenda(1420);
    props.setNovoFeriadoNome("Rascunho preservado");
  });
  await env.resolveLatest();
  const before = env.harness.tree.props;
  assert.equal(env.enabled(), true);
  let refreshing;
  await env.harness.act(() => {
    refreshing = env.refresh();
  });
  assert.equal(env.harness.tree.type, "report-view");
  assert.equal(env.harness.tree.props.loading, false);
  assert.equal(env.requests.at(-1).path, "/relatorios/vendas/relatorio");
  env.requests.at(-1).resolve({
    data: env.report({
      taxa_cartao: 0,
      ifood_financial: {
        charges: [{ code: "PAYMENT_TRANSACTION_FEE", amount: 0 }],
        complete: false,
      },
    }),
  });
  await refreshing;
  await env.harness.settle();
  const after = env.harness.tree.props;
  assert.equal(after.abaAtiva, "lista");
  assert.equal(after.novoFeriadoNome, "Rascunho preservado");
  assert.equal(after.filtroFormaPagamento, "iFood online");
  assert.deepEqual([...after.vendasSelecionadasIds], [...before.vendasSelecionadasIds]);
  assert.deepEqual([...after.vendasExpandidas], [1420]);
  assert.equal(after.listaVendasPorCanal[0].taxa_cartao, 0);
});

test("resposta silenciosa antiga não substitui o relatório de outro período", async () => {
  const env = setup();
  await env.resolveLatest();
  let oldRefresh;
  await env.harness.act(() => {
    oldRefresh = env.refresh();
  });
  const stale = env.requests.at(-1);
  await env.harness.act(() => env.harness.tree.props.setDataInicio("2026-10-01"));
  await env.resolveLatest({ numero_venda: "PERIODO-NOVO" });
  stale.resolve({ data: env.report({ numero_venda: "RESPOSTA-ANTIGA" }) });
  await oldRefresh;
  await env.harness.settle();
  assert.equal(env.harness.tree.props.dataInicio, "2026-10-01");
  assert.equal(env.harness.tree.props.listaVendasPorCanal[0].numero_venda, "PERIODO-NOVO");
});
