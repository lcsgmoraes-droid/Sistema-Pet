import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elements,
  elementText,
} from "../../../../scripts/helpers/reactControllerHarness.mjs";

function eventos(propriedades = {}) {
  const listeners = new Map();
  return {
    ...propriedades,
    addEventListener(nome, listener) {
      if (!listeners.has(nome)) listeners.set(nome, new Set());
      listeners.get(nome).add(listener);
    },
    removeEventListener(nome, listener) {
      listeners.get(nome)?.delete(listener);
    },
    disparar(nome) {
      listeners.get(nome)?.forEach((listener) => listener());
    },
    ouvintes(nome) {
      return listeners.get(nome)?.size || 0;
    },
  };
}

function preparar(listarCreditosPacote) {
  const padrao = (nome) => ({ __esModule: true, default: nome });
  const janela = eventos();
  const documento = eventos({ visibilityState: "visible" });
  const app = createControllerHarness(
    fileURLToPath(new URL("./BanhoTosaPacotesView.jsx", import.meta.url)),
    {
      props: {},
      globals: { window: janela, document: documento },
      mocks: new Map([
        [
          "lucide-react",
          Object.fromEntries(
            ["Coins", "PackageCheck", "Plus", "RefreshCw", "WalletCards"].map((nome) => [
              nome,
              nome,
            ]),
          ),
        ],
        ["react-hot-toast", { __esModule: true, default: { success() {}, error() {} } }],
        ["../../../components/v2/BotaoInteracao/BotaoInteracao", padrao("BotaoInteracao")],
        ...["LoadingState", "MetricCard", "MetricGrid", "Panel"].map((nome) => [
          `../../../components/ui/${nome}`,
          padrao(nome),
        ]),
        ...[
          "BanhoTosaCreditoForm",
          "BanhoTosaCreditosList",
          "BanhoTosaPacoteForm",
          "BanhoTosaPacotesList",
        ].map((nome) => [`./${nome}`, padrao(nome)]),
        [
          "../banhoTosaApi",
          {
            banhoTosaApi: {
              listarPacotes: async () => ({ data: [{ id: 1, ativo: true, preco: 200 }] }),
              listarCreditosPacote,
            },
          },
        ],
        [
          "../banhoTosaUtils",
          {
            formatCurrency: String,
            formatNumber: String,
            getApiErrorMessage: (_erro, mensagem) => mensagem,
          },
        ],
        ["../../../services/corepetDialog", { confirmarCorePet: async () => true }],
      ]),
    },
  );
  return { app, janela, documento };
}

const creditos = (app) =>
  elements(app.tree).find((item) => item.type === "BanhoTosaCreditosList")?.props.creditos;
const carregando = (app) => elements(app.tree).some((item) => item.type === "LoadingState");
const saldoInicial = {
  id: 8,
  disponivel: true,
  saldo_creditos: 4,
  valor_pago: 0,
  status_pagamento: "pendente",
};

test("voltar a aba atualiza saldo e pagamento sem esconder listas ou duplicar consultas", async () => {
  let chamadas = 0;
  let concluir;
  const { app, janela, documento } = preparar(async () => {
    chamadas += 1;
    if (chamadas === 1) return { data: [saldoInicial] };
    return new Promise((resolve) => {
      concluir = resolve;
    });
  });
  assert.equal(carregando(app), true);
  await app.settle();
  assert.equal(carregando(app), false);
  await app.act(() => {
    janela.disparar("focus");
    documento.disparar("visibilitychange");
  });
  assert.equal(chamadas, 2);
  assert.equal(carregando(app), false);
  assert.deepEqual(creditos(app), [saldoInicial]);

  const atualizado = {
    ...saldoInicial,
    saldo_creditos: 3,
    valor_pago: 80,
    status_pagamento: "parcial",
  };
  concluir({ data: [atualizado] });
  await app.settle();
  assert.deepEqual(creditos(app), [atualizado]);
  app.unmount();
});

test("aba oculta nao atualiza e visibilidade restaurada consulta os dados", async () => {
  let chamadas = 0;
  const { app, janela, documento } = preparar(async () => {
    chamadas += 1;
    return { data: [saldoInicial] };
  });
  await app.settle();
  documento.visibilityState = "hidden";
  await app.act(() => {
    documento.disparar("visibilitychange");
    janela.disparar("focus");
  });
  assert.equal(chamadas, 1);
  documento.visibilityState = "visible";
  await app.act(() => documento.disparar("visibilitychange"));
  assert.equal(chamadas, 2);
  app.unmount();
});

test("falha no refresh preserva dados e permite tentar novamente ao receber foco", async () => {
  let chamadas = 0;
  const { app, janela } = preparar(async () => {
    chamadas += 1;
    if (chamadas === 2) throw new Error("temporario");
    return { data: [{ ...saldoInicial, valor_pago: chamadas === 3 ? 200 : 0 }] };
  });
  await app.settle();
  await app.act(() => janela.disparar("focus"));
  assert.deepEqual(creditos(app), [saldoInicial]);
  assert.equal(carregando(app), false);
  assert.match(elementText(app.tree), /Não foi possível carregar os pacotes/);
  await app.act(() => janela.disparar("focus"));
  assert.equal(creditos(app)[0].valor_pago, 200);
  assert.doesNotMatch(elementText(app.tree), /Não foi possível carregar os pacotes/);
  app.unmount();
});

test("desmontagem remove eventos e ignora resposta tardia do refresh", async () => {
  let chamadas = 0;
  let concluir;
  const { app, janela, documento } = preparar(async () => {
    chamadas += 1;
    if (chamadas === 1) return { data: [saldoInicial] };
    return new Promise((resolve) => {
      concluir = resolve;
    });
  });
  await app.settle();
  await app.act(() => janela.disparar("focus"));
  app.unmount();
  assert.equal(janela.ouvintes("focus"), 0);
  assert.equal(documento.ouvintes("visibilitychange"), 0);
  concluir({ data: [{ ...saldoInicial, saldo_creditos: 1, valor_pago: 200 }] });
  await app.settle();
  assert.deepEqual(creditos(app), [saldoInicial]);
  await app.act(() => janela.disparar("focus"));
  assert.equal(chamadas, 2);
});

test("alteracao durante refresh aguarda a leitura e busca o resultado salvo", async () => {
  let chamadas = 0;
  let concluir;
  const { app, janela } = preparar(async () => {
    chamadas += 1;
    if (chamadas === 2) {
      return new Promise((resolve) => {
        concluir = resolve;
      });
    }
    return { data: [{ ...saldoInicial, valor_pago: chamadas === 3 ? 200 : 0 }] };
  });
  await app.settle();
  await app.act(() => janela.disparar("focus"));
  const lista = elements(app.tree).find((item) => item.type === "BanhoTosaCreditosList");
  const recarregar = lista.props.onChanged();
  await app.settle();
  assert.equal(chamadas, 2);
  concluir({ data: [saldoInicial] });
  await recarregar;
  await app.settle();
  assert.equal(chamadas, 3);
  assert.equal(creditos(app)[0].valor_pago, 200);
  app.unmount();
});
