import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createControllerHarness } from "../../scripts/helpers/reactControllerHarness.mjs";
import { obterTotalRecebidoExistente } from "../components/modalPagamentoUtils.js";
import * as fiscalStatus from "../utils/pdvFiscalStatus.js";
import { montarPayloadVenda } from "../utils/pdvVendaPayload.js";

function preparar(vendaAtualizada, resumoPagamentos = {}) {
  const publicadas = [];
  const chamadas = [];
  const restauracoes = [];
  const erros = [];
  const visualizacoes = [];
  const alertas = [];
  const harness = createControllerHarness(
    fileURLToPath(new URL("./usePDVVendaFinalizacao.js", import.meta.url)),
    {
      exportName: "usePDVVendaFinalizacao",
      mocks: new Map([
        ["react-router-dom", { useNavigate: () => () => {} }],
        ["react-hot-toast", { __esModule: true, default: { error: (erro) => erros.push(erro) } }],
        [
          "../api",
          {
            __esModule: true,
            default: {
              post: async (url) => chamadas.push(url),
              patch: async (url, body) => restauracoes.push({ url, body }),
              get: async (url) => {
                chamadas.push(url);
                return { data: resumoPagamentos };
              },
            },
          },
        ],
        ["../api/clientes", { buscarClientePorId: async (id) => ({ id, nome: "Cliente teste" }) }],
        ["../api/vendas", { buscarVenda: async () => vendaAtualizada }],
        ["../utils/debug", { debugLog() {} }],
        ["../utils/nfeFiscalAssistida", {}],
        ["../utils/fiscalRejectionGuidance.mjs", {}],
        ["../services/corepetDialog", { confirmarCorePet: async () => true }],
        ["../components/modalPagamentoUtils", { obterTotalRecebidoExistente }],
        ["../utils/pdvDescontosUtils", { normalizarDescontosVenda: (venda) => venda }],
        ["../utils/pdvFiscalStatus", fiscalStatus],
      ]),
      props: {
        vendaAtual: { ...vendaAtualizada, status: "finalizada" },
        setVendaAtual: (venda) => publicadas.push(venda),
        setLoading() {},
        setModoVisualizacao: (value) => visualizacoes.push(value),
        limparVenda() {},
        carregarVendasRecentes() {},
        recarregarContextoClienteAtual: async () => {},
      },
      globals: {
        alert: (message) => alertas.push(message),
        console: { error: (...args) => erros.push(args) },
      },
    },
  );
  return { harness, publicadas, chamadas, restauracoes, erros, visualizacoes, alertas };
}

const vendaEntrega = {
  id: 12,
  numero_venda: "TESTE-ENTREGA",
  status: "aberta",
  cliente_id: 3,
  funcionario_id: 77,
  vendedor_funcionario_id: 77,
  entregador_id: 88,
  tem_entrega: true,
  status_entrega: "entregue",
  pagamento_entrega_previsto: { forma: "dinheiro", valor_para_troco: 300 },
  subtotal: 244.9,
  total: 259.9,
  taxa_entrega: 15,
  endereco_entrega: "Rua do teste, 100",
  entrega: {
    endereco_completo: "Rua do teste, 100",
    taxa_entrega_total: 15,
    taxa_loja: 5,
    taxa_entregador: 10,
    status_entrega: "entregue",
    distancia_km: 2.5,
    valor_por_km: 6,
    loja_origem: "Loja teste",
    observacoes_entrega: "Recebido pelo cliente",
  },
  itens: [
    { produto_id: 1, tipo: "produto", quantidade: 1, preco_unitario: 244.9, subtotal: 244.9 },
  ],
};

test("iFood nao abre modo de edicao de itens e valores recebidos", async () => {
  const env = preparar({ ...vendaEntrega, canal: "ifood", entregador_id: null });
  await env.harness.act(() => env.harness.tree.habilitarEdicao());
  assert.deepEqual(env.visualizacoes, []);
  assert.match(env.alertas[0], /Itens e valores vêm do pedido iFood/);
  assert.deepEqual(env.chamadas, []);
});

test("app e ecommerce continuam permitindo entrar no modo de edicao", async () => {
  for (const canal of ["app", "ecommerce"]) {
    const env = preparar({ ...vendaEntrega, canal });
    await env.harness.act(() => env.harness.tree.habilitarEdicao());
    assert.deepEqual(env.visualizacoes, [false]);
    assert.deepEqual(env.alertas, []);
  }
});

test("reabrir entrega concluída mantém vendedor e rateio no próximo recebimento", async () => {
  const pagamento = { id: 45, forma_pagamento: "dinheiro", valor: 259.9 };
  const env = preparar(vendaEntrega, { pagamentos: [pagamento], total_recebido: 259.9 });
  await env.harness.act(() => env.harness.tree.mudarStatusParaAberta());

  assert.deepEqual(env.erros, []);
  assert.deepEqual(env.chamadas, ["/vendas/12/reabrir", "/vendas/12/pagamentos"]);
  assert.equal(env.publicadas.length, 1);
  const reaberta = env.publicadas[0];
  const payload = montarPayloadVenda(reaberta);
  assert.equal(payload.funcionario_id, 77);
  assert.equal(payload.vendedor_funcionario_id, 77);
  assert.equal(payload.entregador_id, 88);
  assert.deepEqual(payload.pagamento_entrega_previsto, vendaEntrega.pagamento_entrega_previsto);
  assert.equal(payload.taxa_entrega, 15);
  assert.equal(payload.percentual_taxa_loja, 33.33);
  assert.equal(payload.percentual_taxa_entregador, 66.67);
  assert.equal(payload.distancia_km, 2.5);
  assert.equal(payload.observacoes_entrega, "Recebido pelo cliente");
  assert.equal(reaberta.status_entrega, "entregue");
  assert.equal(reaberta.entrega.status_entrega, "entregue");
  assert.equal(reaberta.total_pago, 259.9);
  assert.deepEqual(reaberta.pagamentos, [pagamento]);
});

test("reabertura preserva vendedor sem comissão e valores zero da entrega aninhada", async () => {
  const env = preparar({
    ...vendaEntrega,
    funcionario_id: null,
    entregador_id: undefined,
    status_entrega: undefined,
    pagamento_entrega_previsto: { forma: "pix" },
    taxa_loja: 15,
    entrega: { ...vendaEntrega.entrega, entregador_id: 88, taxa_loja: 0, taxa_entregador: 15 },
  });
  await env.harness.act(() => env.harness.tree.mudarStatusParaAberta());

  assert.deepEqual(env.erros, []);
  const reaberta = env.publicadas[0];
  const payload = montarPayloadVenda(reaberta);
  assert.equal(payload.funcionario_id, null);
  assert.equal(payload.vendedor_funcionario_id, 77);
  assert.equal(payload.entregador_id, 88);
  assert.deepEqual(payload.pagamento_entrega_previsto, { forma: "pix" });
  assert.equal(payload.percentual_taxa_loja, 0);
  assert.equal(payload.percentual_taxa_entregador, 100);
  assert.equal(reaberta.entrega.status_entrega, "entregue");
});

test("reabertura continua aceitando taxas antigas fora do objeto entrega", async () => {
  const env = preparar({ ...vendaEntrega, entrega: null, taxa_loja: 5, taxa_entregador: 10 });
  await env.harness.act(() => env.harness.tree.mudarStatusParaAberta());

  assert.deepEqual(env.erros, []);
  const payload = montarPayloadVenda(env.publicadas[0]);
  assert.equal(payload.endereco_entrega, "Rua do teste, 100");
  assert.equal(payload.taxa_entrega, 15);
  assert.equal(payload.percentual_taxa_loja, 33.33);
  assert.equal(payload.percentual_taxa_entregador, 66.67);
});

test("reabrir para trocar pagamento mantém o bloqueio de benefícios já registrado", async () => {
  const bloqueio = {
    nao_gerar_beneficios: true,
    justificativa_nao_gerar_beneficios: "Venda de teste sem geração de benefícios",
    beneficios_bloqueados_em: "2026-10-23T14:30:00",
    beneficios_bloqueados_por_id: 41,
  };
  const env = preparar({ ...vendaEntrega, ...bloqueio });
  await env.harness.act(() => env.harness.tree.mudarStatusParaAberta());

  assert.deepEqual(env.erros, []);
  const reaberta = env.publicadas[0];
  for (const [campo, valor] of Object.entries(bloqueio)) {
    assert.equal(reaberta[campo], valor);
  }
  assert.equal(reaberta.status, "aberta");
});

test("Cancelar Edição identifica restauração sem registrar um pagamento novo", async () => {
  const env = preparar(vendaEntrega);
  await env.harness.act(() => env.harness.tree.mudarStatusParaAberta());
  await env.harness.update({ vendaAtual: env.publicadas[0] });
  await env.harness.act(() => env.harness.tree.cancelarEdicao());

  assert.deepEqual(env.erros, []);
  assert.deepEqual(env.restauracoes, [
    { url: "/vendas/12/status", body: { status: "finalizada", cancelar_reabertura: true } },
  ]);
  assert.deepEqual(env.chamadas, ["/vendas/12/reabrir", "/vendas/12/pagamentos"]);
});
