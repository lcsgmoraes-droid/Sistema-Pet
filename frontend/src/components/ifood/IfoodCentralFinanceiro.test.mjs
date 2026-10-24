import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elements,
} from "../../../scripts/helpers/reactControllerHarness.mjs";

const stub = (value) => ({ __esModule: true, default: value });
async function setup(user) {
  let promotionRefresh;
  let calls = 0;
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
    refresh: () => promotionRefresh(),
    get calls() {
      return calls;
    },
  };
}

test("Financeiro exige permissão financeira mesmo quando usuário pode ver produtos", async () => {
  const env = await setup({ id: 1, permissions: ["produtos.visualizar"] });
  const tabs = elements(env.harness.tree).find((item) => item.type === "AbasNavegacao");
  assert.equal(
    tabs.props.abas.some((tab) => tab.id === "financeiro"),
    false,
  );
  assert.equal(
    elements(env.harness.tree).some((item) => item.type === "IfoodFinanceiro"),
    false,
  );
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
