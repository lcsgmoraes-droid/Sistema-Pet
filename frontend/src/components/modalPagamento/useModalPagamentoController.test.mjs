import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createControllerHarness } from "../../../scripts/helpers/reactControllerHarness.mjs";

const venda = {
  id: 12,
  total: 119.9,
  status: "aberta",
  itens: [],
  desconto_valor: 0,
  desconto_venda_valor: 0,
};
function preparar() {
  const leituras = [],
    opcoes = [];
  const api = {
    get(url) {
      if (!url.endsWith("/pagamentos")) return Promise.resolve({ data: [] });
      let resolve, reject;
      const promise = new Promise((sim, nao) => {
        resolve = sim;
        reject = nao;
      });
      leituras.push({ url, resolve, reject });
      return promise;
    },
  };
  const h = createControllerHarness(
    fileURLToPath(new URL("./useModalPagamentoController.js", import.meta.url)),
    {
      props: { venda, onClose() {}, onConfirmar() {} },
      globals: { setTimeout: () => 1, clearTimeout() {}, console: { log() {}, error() {} } },
      mocks: new Map([
        ["../../api", { __esModule: true, default: api }],
        ["../../hooks/useRevealFloatingPanel", { __esModule: true, default() {} }],
        ["../../contexts/ModulosContext", { useModulos: () => ({ moduloAtivo: () => false }) }],
        [
          "./useModalPagamentoActions",
          {
            useModalPagamentoActions: (valor) => {
              opcoes.push(valor);
              return {};
            },
          },
        ],
      ]),
    },
  );
  return { h, leituras, opcoes };
}

test("consulta de pagamentos existente bloqueia registrar e adicionar ate leitura valida", async () => {
  const c = preparar();
  await c.h.settle();
  assert.equal(c.h.tree.viewProps.loading, true);
  assert.equal(c.opcoes.at(-1).bloqueado, true);
  assert.equal(c.h.tree.viewProps.podeConfirmarFinalizacao, false);
  c.leituras[0].resolve({ data: { total_recebido: 40, pagamentos: [{ id: 1, valor: 40 }] } });
  await c.h.settle();
  assert.equal(c.h.tree.viewProps.valorRestante, 79.9);
  assert.equal(c.h.tree.viewProps.loading, false);
  assert.equal(c.opcoes.at(-1).bloqueado, false);
});

test("falha e resposta antiga nao viram recebido zero liberado para duplicar pagamento", async () => {
  const c = preparar();
  await c.h.settle();
  c.leituras[0].reject({ response: { status: 404 } });
  await c.h.settle();
  assert.equal(c.h.tree.viewProps.loading, false);
  assert.equal(c.opcoes.at(-1).bloqueado, true);
  assert.match(c.h.tree.viewProps.erro, /conferir os pagamentos já registrados/);
  await c.h.update({ venda: { ...venda, id: 13 } });
  assert.equal(c.opcoes.at(-1).bloqueado, true);
  c.leituras[1].resolve({ data: { total_recebido: 20, pagamentos: [] } });
  await c.h.settle();
  assert.equal(c.h.tree.viewProps.valorRestante, 99.9);
});

test("novo desconto do PDV nao e sobrescrito por total persistido anteriormente no modal", async () => {
  const c = preparar();
  await c.h.settle();
  c.leituras[0].resolve({ data: { total_recebido: 0, pagamentos: [] } });
  await c.h.settle();
  await c.h.act(() => c.opcoes.at(-1).setVendaPersistida({ total: 119.9 }));
  await c.h.update({
    venda: { ...venda, total: 109.9, desconto_valor: 10, desconto_venda_valor: 10 },
  });
  assert.equal(c.h.tree.viewProps.valorTotal, 109.9);
  assert.equal(c.h.tree.viewProps.valorRestante, 109.9);
  assert.equal(c.h.tree.viewProps.venda.desconto_valor, 10);
});

test("saldo coberto ignora novo candidato mas preserva revisao do excesso ja registrado ou no lote", async () => {
  const c = preparar();
  await c.h.settle();
  c.leituras[0].resolve({ data: { total_recebido: 119.9, pagamentos: [{ valor: 119.9 }] } });
  await c.h.settle();
  await c.h.act(() => {
    c.h.tree.viewProps.setFormaPagamentoSelecionada({ id: 4, nome: "Pix", tipo: "pix" });
    c.h.tree.viewProps.setValorRecebido(10);
  });
  assert.equal(c.h.tree.viewProps.valorRestante, 0);
  assert.equal(c.h.tree.viewProps.composicaoExcedente.novosPagamentos, 0);
  assert.equal(c.h.tree.viewProps.composicaoExcedente.excedente, 0);
  await c.h.update({ venda: { ...venda, total: 109.9, desconto_valor: 10 } });
  assert.equal(c.h.tree.viewProps.composicaoExcedente.novosPagamentos, 0);
  assert.equal(c.h.tree.viewProps.composicaoExcedente.excedente, 10);

  await c.h.act(() => {
    c.opcoes.at(-1).setTotalPagoExistente(0);
    c.opcoes.at(-1).setPagamentos([{ forma_pagamento_tipo: "pix", valor: 119.9 }]);
  });
  assert.equal(c.h.tree.viewProps.valorRestante, 0);
  assert.equal(c.h.tree.viewProps.composicaoExcedente.novosPagamentos, 119.9);
  assert.equal(c.h.tree.viewProps.composicaoExcedente.excedente, 10);
});
