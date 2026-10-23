import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elements,
  elementText,
} from "../../scripts/helpers/reactControllerHarness.mjs";

function preparar() {
  let user = { id: 7, tenant: { id: "tenant-a" } };
  let token = "sessao-teste";
  const storage = new Map([["selectedTenant", JSON.stringify(user.tenant)]]);
  const consultas = [];
  const h = createControllerHarness(
    fileURLToPath(new URL("./ModulosContext.jsx", import.meta.url)),
    {
      exportName: "ModulosProvider",
      props: { children: null },
      globals: {
        localStorage: { getItem: (key) => storage.get(key) ?? null },
        window: {
          addEventListener() {},
          removeEventListener() {},
          setInterval() {},
          clearInterval() {},
        },
        document: { addEventListener() {}, removeEventListener() {}, visibilityState: "visible" },
      },
      mocks: new Map([
        ["./AuthContext", { useAuth: () => ({ user }) }],
        ["../auth/tokenStorage", { getAccessToken: () => token }],
        [
          "../services/api",
          {
            api: {
              get(url) {
                assert.equal(url, "/modulos/status");
                return new Promise((resolve, reject) => consultas.push({ resolve, reject }));
              },
            },
          },
        ],
      ]),
    },
  );
  const contexto = () => h.tree.props.value;
  const filhos = { type: "tela-premium", props: {} };
  function tela() {
    return createControllerHarness(
      fileURLToPath(new URL("../components/ModuloBloqueado.jsx", import.meta.url)),
      {
        props: { modulo: "compras", children: filhos },
        globals: { sessionStorage: { getItem: () => null, setItem() {} } },
        mocks: new Map([
          ["lucide-react", { RefreshCw: "RefreshCw", WifiOff: "WifiOff" }],
          [
            "react-icons/fi",
            Object.fromEntries(
              ["FiCheckCircle", "FiHelpCircle", "FiLock", "FiMessageCircle", "FiTrendingUp"].map(
                (name) => [name, name],
              ),
            ),
          ],
          ["react-router-dom", { Link: "Link" }],
          [
            "../contexts/ModulosContext",
            {
              useModulos: contexto,
              MODULOS_INFO: { compras: { nome: "Compras", recursos: [] } },
            },
          ],
          ["./moduloBloqueado/ModuloBloqueadoPreviews", { PREVIEWS: {} }],
          ["./v2/BotaoInteracao/BotaoInteracao", { __esModule: true, default: "BotaoInteracao" }],
        ]),
      },
    ).tree;
  }
  async function confirmar(modulos = ["compras"], extras = {}) {
    const data = {
      tenant_id: user.tenant.id,
      modulos_ativos: modulos,
      plano: "pet-gestao",
      assinatura: { status: "active", acesso_operacional_ativo: true },
      ...extras,
    };
    const ultima = consultas.length;
    consultas.at(-1).resolve({ data });
    await h.settle();
    // A primeira mudanca do status da assinatura ajusta o intervalo de atualizacao.
    if (consultas.length > ultima) {
      consultas.at(-1).resolve({ data });
      await h.settle();
    }
  }
  async function atualizar() {
    await h.act(() => {
      void contexto().carregarModulos();
    });
  }
  return {
    h,
    consultas,
    contexto,
    tela,
    filhos,
    confirmar,
    atualizar,
    async trocar({ userId = user.id, tenantId = user.tenant.id, accessToken = token }) {
      user = { id: userId, tenant: { id: tenantId } };
      token = accessToken;
      storage.set("selectedTenant", JSON.stringify(user.tenant));
      await h.update({});
    },
  };
}

test("falha inicial mostra consulta indisponivel e permite repetir sem oferecer Beta", async () => {
  const c = preparar();
  c.consultas[0].reject(new Error("Network Error"));
  await c.h.settle();
  assert.equal(c.contexto().moduloAtivo("compras"), false);
  const tela = c.tela();
  assert.match(elementText(tela), /Não foi possível confirmar o acesso/);
  assert.doesNotMatch(elementText(tela), /Solicitar acesso Beta/);
  const repetir = elements(tela).find((item) => item.type === "BotaoInteracao");
  assert.ok(repetir);
  await c.h.act(() => {
    void repetir.props.onClick();
  });
  await c.confirmar();
  assert.equal(c.contexto().erroCarregamento, false);
  assert.equal(c.tela(), c.filhos);
});

test("falha de rede ou servidor preserva a tela e acesso antes confirmados na mesma empresa", async () => {
  const c = preparar();
  await c.confirmar();
  const assinatura = c.contexto().assinaturaAtual;
  for (const error of [new Error("Network Error"), { response: { status: 503 } }]) {
    await c.atualizar();
    c.consultas.at(-1).reject(error);
    await c.h.settle();
    assert.equal(c.contexto().erroCarregamento, true);
    assert.equal(c.contexto().planoAtual, "pet-gestao");
    assert.equal(c.contexto().assinaturaAtual, assinatura);
    assert.equal(c.tela(), c.filhos);
  }
});

test("negacao explicita da API descarta acesso anterior sem transformar erro em venda", async () => {
  for (const status of [401, 403]) {
    const c = preparar();
    await c.confirmar();
    await c.atualizar();
    c.consultas.at(-1).reject({ response: { status } });
    await c.h.settle();
    assert.equal(c.contexto().moduloAtivo("compras"), false);
    assert.equal(c.contexto().assinaturaAtual, null);
    assert.doesNotMatch(elementText(c.tela()), /Solicitar acesso Beta/);
  }
});

test("empresa ou usuario diferentes nao recebem cache nem resposta atrasada da sessao anterior", async () => {
  for (const destino of [{ tenantId: "tenant-b" }, { userId: 8 }]) {
    const c = preparar();
    await c.confirmar();
    await c.atualizar();
    const consultaAntiga = c.consultas.at(-1);
    await c.trocar(destino);
    assert.equal(c.contexto().moduloAtivo("compras"), false);
    assert.equal(c.contexto().assinaturaAtual, null);
    c.consultas.at(-1).reject(new Error("Network Error"));
    await c.h.settle();
    consultaAntiga.resolve({ data: { tenant_id: "tenant-a", modulos_ativos: ["compras"] } });
    await c.h.settle();
    assert.equal(c.contexto().moduloAtivo("compras"), false);
    assert.match(elementText(c.tela()), /Não foi possível confirmar o acesso/);
  }
});

test("voltar ao usuario ou empresa anterior exige nova confirmacao apos troca de escopo", async () => {
  for (const destino of [{ tenantId: "tenant-b" }, { userId: 8 }]) {
    const c = preparar();
    await c.confirmar();
    await c.trocar(destino);
    c.consultas.at(-1).reject(new Error("Network Error"));
    await c.h.settle();
    await c.trocar({ userId: 7, tenantId: "tenant-a" });
    assert.equal(c.contexto().moduloAtivo("compras"), false);
    assert.equal(c.contexto().assinaturaAtual, null);
    assert.notEqual(c.tela(), c.filhos);
    await c.confirmar();
    assert.equal(c.tela(), c.filhos);
  }
});

test("renovacao de token no mesmo escopo preserva acesso durante a nova consulta", async () => {
  const c = preparar();
  await c.confirmar();
  await c.trocar({ accessToken: "token-renovado" });
  assert.equal(c.tela(), c.filhos);
  c.consultas.at(-1).reject(new Error("Network Error"));
  await c.h.settle();
  assert.equal(c.tela(), c.filhos);
});

test("resposta de outra empresa e sessao sem token nao liberam a tela", async () => {
  const c = preparar();
  await c.confirmar(["compras"], { tenant_id: "tenant-outra" });
  assert.equal(c.contexto().moduloAtivo("compras"), false);
  assert.match(elementText(c.tela()), /Não foi possível confirmar o acesso/);
  await c.atualizar();
  await c.confirmar();
  assert.equal(c.tela(), c.filhos);
  await c.trocar({ accessToken: null });
  assert.equal(c.contexto().moduloAtivo("compras"), false);
  assert.equal(c.contexto().assinaturaAtual, null);
});

test("resposta valida sem modulo mantem a vitrine; falha de consulta mostra repetir", async () => {
  const c = preparar();
  await c.confirmar([]);
  assert.match(elementText(c.tela()), /Solicitar acesso Beta/);
  await c.atualizar();
  c.consultas.at(-1).reject(new Error("Network Error"));
  await c.h.settle();
  assert.doesNotMatch(elementText(c.tela()), /Solicitar acesso Beta/);
  assert.match(elementText(c.tela()), /Tentar novamente/);
});

test("suspensao administrativa confirmada continua visivel durante indisponibilidade", async () => {
  const c = preparar();
  await c.confirmar([], { assinatura: { acesso_operacional_ativo: false } });
  await c.atualizar();
  c.consultas.at(-1).reject(new Error("Network Error"));
  await c.h.settle();
  assert.match(elementText(c.tela()), /Acesso suspenso pela administração/);
  assert.notEqual(c.tela(), c.filhos);
});
