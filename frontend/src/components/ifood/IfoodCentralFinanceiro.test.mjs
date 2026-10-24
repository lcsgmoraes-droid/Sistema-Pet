import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elements,
} from "../../../scripts/helpers/reactControllerHarness.mjs";
import { lerLinkFinanceiro, periodoFinanceiroValido } from "./ifoodFinanceiroNavigation.js";

const stub = (value) => ({ __esModule: true, default: value });
async function setup(user, search = "") {
  let promotionRefresh;
  let calls = 0;
  const location = { search };
  const mocks = new Map([
    ["react-router-dom", { useNavigate: () => () => {} }],
    ["../contexts/AuthContext", { useAuth: () => ({ user }) }],
    [
      "../api/ifood",
      {
        getIfoodCatalogo: async () => {
          calls++;
          return {
            data: {
              items: [],
              total: 0,
              config: { tax_percent: null },
              can_configure: true,
            },
          };
        },
      },
    ],
    [
      "../api/produtos",
      {
        updateProduto() {
          throw new Error("No product writes expected");
        },
      },
    ],
    [
      "../hooks/useIfoodPromotionRefresh",
      stub((_, callback) => {
        promotionRefresh = callback;
      }),
    ],
    ["../components/ui/DataTable", stub("DataTable")],
    ["lucide-react", {}],
  ]);
  for (const name of [
    "AbasNavegacao",
    "BotaoInteracao",
    "BotaoMenuAcoes",
    "CartaoIndicador",
    "InputCheckbox",
    "InputCombobox",
    "InputTexto",
    "SeletorOpcoes",
  ])
    mocks.set(`../components/v2/${name}/${name}`, stub(name));
  for (const name of [
    "IfoodConfiguracao",
    "IfoodProdutoDetalhes",
    "IfoodStatus",
    "IfoodFinanceiro",
  ])
    mocks.set(`../components/ifood/${name}`, stub(name));
  const harness = createControllerHarness(
    fileURLToPath(new URL("../../pages/IfoodCentral.jsx", import.meta.url)),
    {
      props: {},
      mocks,
      globals: {
        AbortController,
        window: {
          location,
          setTimeout() {
            return 1;
          },
          clearTimeout() {},
        },
      },
    },
  );
  await harness.settle();
  return {
    harness,
    location,
    refresh: () => promotionRefresh(),
    get calls() {
      return calls;
    },
  };
}

test("deep link não libera Financeiro para quem só tem permissão de produtos", async () => {
  const env = await setup(
    { id: 1, permissions: ["produtos.visualizar"] },
    "?aba=financeiro&inicio=2025-08-01&fim=2025-08-03",
  );
  const tabs = elements(env.harness.tree).find((item) => item.type === "AbasNavegacao");
  assert.equal(tabs.props.ativa, "catalogo");
  assert.equal(
    tabs.props.abas.some((tab) => tab.id === "financeiro"),
    false,
  );
  assert.equal(
    elements(env.harness.tree).some((item) => item.type === "IfoodFinanceiro"),
    false,
  );
});

test("deep link válido abre Financeiro no período informado somente na montagem", async () => {
  const env = await setup(
    { id: 1, permissions: ["relatorios.financeiro"] },
    "?aba=financeiro&inicio=2025-08-01&fim=2025-08-03",
  );
  const financeiro = () =>
    elements(env.harness.tree).find((item) => item.type === "IfoodFinanceiro");
  assert.equal(financeiro().props.ativo, true);
  assert.deepEqual(financeiro().props.periodoSugerido, { inicio: "2025-08-01", fim: "2025-08-03" });
  const tabs = elements(env.harness.tree).find((item) => item.type === "AbasNavegacao");
  await env.harness.act(() => tabs.props.onChange("configuracao"));
  env.location.search = "?aba=financeiro&inicio=2025-09-01&fim=2025-09-03";
  await env.harness.update({});
  assert.equal(financeiro().props.ativo, false);
  assert.deepEqual(financeiro().props.periodoSugerido, { inicio: "2025-08-01", fim: "2025-08-03" });
});

test("deep link inválido é ignorado sem abrir a aba financeira", async () => {
  for (const search of [
    "?aba=financeiro&inicio=2025-02-29&fim=2025-03-01",
    "?aba=financeiro&inicio=2025-08-03&fim=2025-08-01",
    "?aba=financeiro&inicio=2025-08-01&fim=2025-09-03",
    "?aba=financeiro&inicio=01/08/2025&fim=03/08/2025",
    "?aba=financeiro&inicio=2025-08-01",
    "?aba=financeiro&inicio=0000-01-01&fim=0000-01-01",
    "?aba=catalogo&inicio=2025-08-01&fim=2025-08-03",
  ]) {
    assert.equal(lerLinkFinanceiro(search), null);
    const env = await setup({ id: 1, permissions: ["relatorios.financeiro"] }, search);
    const financeiro = elements(env.harness.tree).find((item) => item.type === "IfoodFinanceiro");
    assert.equal(financeiro.props.ativo, false);
    assert.equal(financeiro.props.periodoSugerido, null);
  }
  assert.equal(periodoFinanceiroValido({ inicio: "2024-02-29", fim: "2024-02-29" }), true);
  assert.deepEqual(lerLinkFinanceiro("?aba=financeiro&inicio=2025-08-01&fim=2025-09-02"), {
    inicio: "2025-08-01",
    fim: "2025-09-02",
  });
});

test("aba financeira preserva configuração montada e timer do catálogo não troca a aba", async () => {
  const env = await setup({ id: 1, tenant_id: "dev-only", permissions: ["relatorios.financeiro"] });
  let tabs = elements(env.harness.tree).find((item) => item.type === "AbasNavegacao");
  await env.harness.act(() => tabs.props.onChange("configuracao"));
  assert.ok(elements(env.harness.tree).some((item) => item.type === "IfoodConfiguracao"));
  tabs = elements(env.harness.tree).find((item) => item.type === "AbasNavegacao");
  await env.harness.act(() => tabs.props.onChange("financeiro"));
  assert.ok(elements(env.harness.tree).some((item) => item.type === "IfoodConfiguracao"));
  const panel = elements(env.harness.tree).find((item) => item.type === "IfoodFinanceiro");
  assert.equal(panel.props.ativo, true);
  await env.harness.act(() => env.refresh());
  tabs = elements(env.harness.tree).find((item) => item.type === "AbasNavegacao");
  assert.equal(tabs.props.ativa, "financeiro");
  assert.ok(env.calls >= 2);
});

test("administrador do tenant e wildcard acessam a aba financeira", async () => {
  for (const user of [
    { id: 1, role: { name: "Admin" } },
    { id: 2, permissions: ["*"] },
  ]) {
    const env = await setup(user);
    assert.ok(
      elements(env.harness.tree)
        .find((item) => item.type === "AbasNavegacao")
        .props.abas.some((tab) => tab.id === "financeiro"),
    );
  }
});
