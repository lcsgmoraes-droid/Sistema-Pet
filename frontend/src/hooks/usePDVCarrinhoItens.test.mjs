import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createControllerHarness } from "../../scripts/helpers/reactControllerHarness.mjs";
import { recalcularVendaComDescontos } from "../utils/pdvDescontosUtils.js";
import { montarPayloadVenda } from "../utils/pdvVendaPayload.js";

const criarItem = (dados = {}) => ({
  tipo: "produto",
  produto_id: 1,
  produto_nome: "Ração a granel",
  e_granel: true,
  unidade: "KG",
  quantidade: 1,
  preco_unitario: 13,
  desconto_valor: 0,
  subtotal: 13,
  ...dados,
});

function preparar(itens = [criarItem()]) {
  let vendaAtual = recalcularVendaComDescontos({ itens, desconto_venda_valor: 0 });
  const recalculos = [];
  const harness = createControllerHarness(
    fileURLToPath(new URL("./usePDVCarrinhoItens.js", import.meta.url)),
    {
      exportName: "usePDVCarrinhoItens",
      // Debug depende do ambiente Vite; os cálculos e os demais módulos são reais.
      mocks: new Map([["../utils/debug", { debugLog() {} }]]),
      props: {
        vendaAtual,
        temCaixaAberto: true,
        statusConsultaCaixa: "pronto",
        setVendaAtual: (update) => {
          vendaAtual = typeof update === "function" ? update(vendaAtual) : update;
        },
        recalcularTotais: (novosItens) => {
          vendaAtual = recalcularVendaComDescontos(vendaAtual, novosItens);
          recalculos.push(vendaAtual);
        },
      },
    },
  );
  return {
    harness,
    recalculos,
    get venda() {
      return vendaAtual;
    },
    async executar(acao, ...args) {
      await harness.act(() => harness.tree[acao](...args));
      await harness.update({ vendaAtual });
    },
  };
}

test("fluxo do vídeo preserva R$ 20,00 no carrinho, total e payload sem mudar preço", async () => {
  const env = preparar();
  await env.executar("atualizarSubtotalItem", 0, 20);

  assert.equal(env.venda.itens[0].quantidade, 1.538);
  assert.equal(env.venda.itens[0].preco_unitario, 13);
  assert.equal(env.venda.itens[0].subtotal, 20);
  assert.equal(env.venda.subtotal, 20);
  assert.equal(env.venda.total, 20);
  const payload = montarPayloadVenda(env.venda);
  assert.equal(payload.itens[0].quantidade, 1.538);
  assert.equal(payload.itens[0].preco_unitario, 13);
  assert.equal(payload.itens[0].subtotal, 20);
  assert.equal(payload.itens[0].desconto_item, 0);
});

test("focar e sair da mesma quantidade, inclusive com vírgula, preserva os R$ 20,00", async () => {
  const env = preparar();
  await env.executar("atualizarSubtotalItem", 0, 20);
  const itemPeloValor = env.venda.itens[0];

  for (const quantidade of [1.538, "1,538", 1.53800001, 1.538]) {
    await env.executar("atualizarQuantidadeItem", 0, quantidade);
    assert.equal(env.venda.itens[0], itemPeloValor);
    assert.equal(env.venda.itens[0].subtotal, 20);
    assert.equal(env.venda.total, 20);
  }
});

test("confirmar e editar o subtotal repetidamente não acumula diferença de centavos", async () => {
  const env = preparar();
  for (const subtotal of [20, 20, 30, 20, 20]) {
    await env.executar("atualizarSubtotalItem", 0, subtotal);
    assert.equal(env.venda.itens[0].subtotal, subtotal);
    assert.equal(env.venda.itens[0].preco_unitario, 13);
    assert.equal(env.venda.total, subtotal);
    assert.equal(montarPayloadVenda(env.venda).itens[0].subtotal, subtotal);
  }
  assert.equal(env.venda.itens[0].quantidade, 1.538);
});

test("quantidade diferente e botões de incremento voltam a calcular pelo peso informado", async () => {
  const env = preparar();
  await env.executar("atualizarSubtotalItem", 0, 20);
  await env.executar("atualizarQuantidadeItem", 0, 2);
  assert.equal(env.venda.itens[0].quantidade, 2);
  assert.equal(env.venda.itens[0].subtotal, 26);
  assert.equal(env.venda.total, 26);

  await env.executar("atualizarSubtotalItem", 0, 20);
  await env.executar("alterarQuantidade", 0, 1);
  assert.equal(env.venda.itens[0].quantidade, 2.538);
  assert.equal(env.venda.itens[0].preco_unitario, 13);
  assert.equal(env.venda.itens[0].subtotal, 32.99);
  assert.equal(env.venda.total, 32.99);
});

test("alterar subtotal de um item mantém o outro item e soma os dois corretamente", async () => {
  const outroItem = criarItem({ produto_id: 2, quantidade: 2, preco_unitario: 2.5, subtotal: 5 });
  const env = preparar([criarItem(), outroItem]);
  await env.executar("atualizarSubtotalItem", 0, 20);

  assert.equal(env.venda.itens.length, 2);
  assert.equal(env.venda.itens[1], outroItem);
  assert.equal(env.venda.itens[0].subtotal, 20);
  assert.equal(env.venda.subtotal, 25);
  assert.equal(env.venda.total, 25);
  assert.deepEqual(
    montarPayloadVenda(env.venda).itens.map((item) => [item.produto_id, item.subtotal]),
    [
      [1, 20],
      [2, 5],
    ],
  );
});

test("subtotal inválido não altera o item nem os totais", async () => {
  const env = preparar();
  const original = env.venda.itens[0];
  for (const subtotal of [0, -1, Number.NaN, Number.POSITIVE_INFINITY]) {
    await env.executar("atualizarSubtotalItem", 0, subtotal);
    assert.equal(env.venda.itens[0], original);
    assert.equal(env.venda.total, 13);
  }
});
