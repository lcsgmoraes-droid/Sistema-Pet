import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import * as fiscalStatus from "../utils/pdvFiscalStatus.js";
import { createControllerHarness } from "../../scripts/helpers/reactControllerHarness.mjs";

function pendente() {
  let resolver;
  const promise = new Promise((resolve) => {
    resolver = resolve;
  });
  return { promise, resolver };
}

function preparar() {
  const respostas = new Map();
  const consultas = [];
  const publicadas = [];
  const loadings = [];
  const comissoes = [];
  const contextos = [];
  const entregadores = [];
  const modais = [];
  const timers = [];
  const alertas = [];
  const harness = createControllerHarness(
    fileURLToPath(new URL("./usePDVVendaCarregamento.js", import.meta.url)),
    {
      exportName: "usePDVVendaCarregamento",
      mocks: new Map([
        [
          "../api",
          { __esModule: true, default: { get: async () => ({ data: { pagamentos: [] } }) } },
        ],
        ["../api/clientes", { buscarClientePorId: async (id) => ({ id }) }],
        [
          "../api/vendas",
          {
            buscarVendaComSituacaoFiscal: (id) => {
              consultas.push(id);
              return respostas.get(id).promise;
            },
          },
        ],
        ["../utils/debug", { debugLog() {} }],
        ["../utils/pdvFiscalStatus", fiscalStatus],
        ["../services/corepetDialog", { perguntarCorePet: async () => null }],
        ["../components/modalPagamentoUtils", { obterTotalRecebidoExistente: () => 0 }],
        ["../utils/pdvDescontosUtils", { normalizarDescontosVenda: (venda) => venda }],
      ]),
      props: {
        setVendaAtual: (venda) => publicadas.push(venda),
        setLoading: (loading) => loadings.push(loading),
        setModoVisualizacao() {},
        setMostrarModalPagamento: (aberto) => modais.push(aberto),
        sincronizarComissaoDaVenda: async (id) => comissoes.push(id),
        sincronizarEntregadorDaVenda: async (id) => entregadores.push(id),
        recarregarContextoClientePorId: async (id) => contextos.push(id),
      },
      globals: {
        alert: (mensagem) => alertas.push(mensagem),
        setTimeout: (callback) => timers.push(callback),
        window: { scrollTo() {} },
        console: { error() {} },
      },
    },
  );
  const prepararVenda = (id) => {
    const resposta = pendente();
    respostas.set(id, resposta);
    return () =>
      resposta.resolver({
        id,
        cliente_id: id + 100,
        funcionario_id: id + 200,
        entregador_id: id + 300,
        status: "pago_nf",
        nfe_status: "cancelada",
        total: 10,
      });
  };
  return {
    harness,
    prepararVenda,
    consultas,
    publicadas,
    loadings,
    comissoes,
    contextos,
    entregadores,
    modais,
    timers,
    alertas,
  };
}

test("carga antiga não publica venda nem encerra loading da seleção mais recente", async () => {
  const env = preparar();
  const resolverA = env.prepararVenda(1);
  const resolverB = env.prepararVenda(2);
  const anterior = env.harness.tree.reabrirVenda({ id: 1 });
  const atual = env.harness.tree.carregarVendaEspecifica(2);

  resolverA();
  await anterior;
  assert.deepEqual(env.publicadas, []);
  assert.deepEqual(env.comissoes, []);
  assert.equal(env.loadings.at(-1), true);

  resolverB();
  await atual;
  assert.deepEqual(
    env.publicadas.map((venda) => venda.id),
    [2],
  );
  assert.deepEqual(env.comissoes, [202]);
  assert.deepEqual(env.contextos, [102]);
  assert.deepEqual(env.entregadores, [302]);
  assert.equal(env.loadings.at(-1), false);
});

test("resposta antiga não substitui venda escolhida depois pela lista lateral", async () => {
  const env = preparar();
  const resolverA = env.prepararVenda(1);
  const resolverB = env.prepararVenda(2);
  const anterior = env.harness.tree.carregarVendaEspecifica(1);
  const atual = env.harness.tree.reabrirVenda({ id: 2 });
  resolverB();
  await atual;
  const loadingsAtuais = [...env.loadings];

  resolverA();
  await anterior;
  assert.deepEqual(
    env.publicadas.map((venda) => venda.id),
    [2],
  );
  assert.deepEqual(env.contextos, [102]);
  assert.deepEqual(env.loadings, loadingsAtuais);
  assert.deepEqual(env.alertas, []);
});

test("pedidos simultâneos da mesma venda compartilham consulta e publicação", async () => {
  const env = preparar();
  const resolver = env.prepararVenda(1);
  const primeira = env.harness.tree.carregarVendaEspecifica(1, true);
  const segunda = env.harness.tree.carregarVendaEspecifica(1);
  assert.deepEqual(env.consultas, [1]);

  resolver();
  await Promise.all([primeira, segunda]);
  assert.deepEqual(
    env.publicadas.map((venda) => venda.id),
    [1],
  );
  assert.deepEqual(env.comissoes, [201]);
  assert.equal(env.loadings.at(-1), false);

  const resolverB = env.prepararVenda(2);
  const atual = env.harness.tree.reabrirVenda({ id: 2 });
  resolverB();
  await atual;
  env.timers.forEach((callback) => callback());
  assert.deepEqual(env.modais, []);
});
