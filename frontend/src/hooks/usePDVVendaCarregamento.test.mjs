import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import * as fiscalStatus from "../utils/pdvFiscalStatus.js";
import { recalcularVendaComDescontos } from "../utils/pdvDescontosUtils.js";
import { montarPayloadVenda } from "../utils/pdvVendaPayload.js";
import { montarPayloadAnaliseMargem } from "../components/modalPagamentoUtils.js";
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
    return (extra = {}) =>
      resposta.resolver({
        id,
        cliente_id: id + 100,
        funcionario_id: id + 200,
        entregador_id: id + 300,
        status: "pago_nf",
        nfe_status: "cancelada",
        total: 10,
        ...extra,
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

test("abrir pedido DELIVERY iFood conserva modalidade, canal e ausencia de entregador local", async () => {
  const env = preparar();
  const resolve = env.prepararVenda(42);
  const loading = env.harness.tree.carregarVendaEspecifica(42);
  resolve({
    canal: "ifood",
    tem_entrega: true,
    entregador_id: null,
    entrega: { taxa_entrega_total: 0 },
  });
  await loading;
  assert.equal(env.publicadas[0].canal, "ifood");
  assert.equal(env.publicadas[0].tem_entrega, true);
  assert.equal(env.publicadas[0].entregador_id, null);
  assert.deepEqual(env.entregadores, [null]);
});

test("pedido iFood preserva frete positivo e total ao abrir pelo vinculo ou pela lista", async () => {
  for (const abrir of ["carregarVendaEspecifica", "reabrirVenda"]) {
    const env = preparar();
    const resolve = env.prepararVenda(42);
    const origem = {
      canal: "ifood",
      status: "aberta",
      cliente_id: null,
      tem_entrega: true,
      entregador_id: null,
      taxa_entrega: 8.9,
      entrega: { taxa_entrega_total: 8.9, taxa_loja: 0, taxa_entregador: 0 },
      subtotal: 65,
      total: 73.9,
      desconto_valor: 0,
      desconto_venda_valor: 0,
      itens: [{ produto_id: 1, quantidade: 1, preco_unitario: 65, subtotal: 65 }],
    };
    const antes = structuredClone(origem);
    const loading = env.harness.tree[abrir](abrir === "reabrirVenda" ? { id: 42 } : 42);
    resolve(origem);
    await loading;

    const venda = env.publicadas[0];
    assert.equal(venda.canal, "ifood");
    assert.equal(venda.tem_entrega, true);
    assert.equal(venda.entregador_id, null);
    assert.equal(venda.subtotal, 65);
    assert.equal(venda.entrega.taxa_entrega_total, 8.9);
    assert.equal(venda.total, 73.9);
    assert.equal(recalcularVendaComDescontos(venda).total, 73.9);
    assert.equal(montarPayloadVenda(venda).taxa_entrega, 8.9);
    assert.equal(montarPayloadAnaliseMargem({ venda }).taxa_entrega, 8.9);
    assert.deepEqual(venda.itens, origem.itens);
    assert.deepEqual(origem, antes);
    assert.equal(env.publicadas.length, 1);
    assert.deepEqual(env.alertas, []);
  }
});
