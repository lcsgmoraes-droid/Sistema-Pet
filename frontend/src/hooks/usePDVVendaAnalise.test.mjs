import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createControllerHarness } from "../../scripts/helpers/reactControllerHarness.mjs";
import { recalcularItemPorSubtotal } from "../utils/pdvCarrinhoItensUtils.js";

function criarVenda(subtotal = 20) {
  return {
    itens: [
      recalcularItemPorSubtotal(
        { produto_id: 7, quantidade: 1, preco_unitario: 13, subtotal: 13, custo: 8 },
        subtotal,
      ),
    ],
    desconto_venda_valor: 0,
    funcionario_id: 9,
  };
}

function preparar(vendaAtual = criarVenda(), vendaPersistida = criarVenda()) {
  const posts = [];
  const gets = [];
  const resposta = { total_venda: 20, lucro: 7.7 };
  const harness = createControllerHarness(
    fileURLToPath(new URL("./usePDVVendaAnalise.js", import.meta.url)),
    {
      exportName: "usePDVVendaAnalise",
      mocks: new Map([
        [
          "../api",
          {
            __esModule: true,
            default: {
              async post(url, payload) {
                posts.push({ url, payload });
                return { data: resposta };
              },
              async get(url) {
                gets.push(url);
                return { data: vendaPersistida };
              },
            },
          },
        ],
        ["../utils/debug", { debugLog() {} }],
      ]),
      props: vendaAtual,
    },
  );
  return { harness, posts, gets, resposta };
}

function validarSubtotalEnviado(env) {
  assert.equal(env.posts.length, 1);
  assert.equal(env.posts[0].url, "/formas-pagamento/analisar-venda");
  assert.deepEqual(env.posts[0].payload.items, [
    {
      produto_id: 7,
      quantidade: 1.538,
      preco_venda: 13,
      desconto_item: 0,
      subtotal: 20,
      custo: 8,
    },
  ]);
  assert.equal(env.harness.tree.dadosAnalise, env.resposta);
  assert.equal(env.harness.tree.carregandoAnalise, false);
  assert.equal(env.harness.tree.mostrarAnaliseVenda, true);
}

test("análise do carrinho envia R$ 20,00 mesmo com quantidade arredondada em três casas", async () => {
  const env = preparar();
  await env.harness.act(() => env.harness.tree.buscarAnaliseVenda());
  validarSubtotalEnviado(env);
  assert.deepEqual(env.gets, []);
});

test("análise com múltiplas formas de pagamento também envia o subtotal digitado", async () => {
  const env = preparar();
  const formasPagamento = [
    { forma_pagamento_id: 1, valor: 10 },
    { forma_pagamento_id: 2, valor: 10 },
  ];
  await env.harness.act(() => env.harness.tree.analisarVendaComFormasPagamento(formasPagamento));
  validarSubtotalEnviado(env);
  assert.deepEqual(env.posts[0].payload.formas_pagamento, formasPagamento);
  assert.deepEqual(env.gets, []);
});

test("análise da venda salva usa o subtotal persistido de R$ 20,00", async () => {
  // O carrinho atual é diferente para comprovar que a análise usa a venda carregada.
  const env = preparar(criarVenda(30), criarVenda(20));
  await env.harness.act(() => env.harness.tree.analisarVenda(42));
  validarSubtotalEnviado(env);
  assert.deepEqual(env.gets, ["/vendas/42"]);
});
