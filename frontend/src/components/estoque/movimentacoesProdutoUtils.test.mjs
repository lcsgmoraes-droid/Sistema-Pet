import assert from 'node:assert/strict';
import test from 'node:test';

import {
  resolverEstoqueAtualMovimentacoes,
  resolverSaldoDisponivelMovimentacoes,
} from './movimentacoesProdutoUtils.js';

test('movimentacoes usa estoque virtual calculado para kit virtual', () => {
  const produto = {
    tipo_produto: 'KIT',
    tipo_kit: 'VIRTUAL',
    estoque_atual: -1,
    estoque_virtual: 31,
    estoque_disponivel: 31,
    estoque_reservado: 0,
  };

  assert.equal(resolverEstoqueAtualMovimentacoes(produto), 31);
  assert.equal(resolverSaldoDisponivelMovimentacoes(produto), 31);
});

test('movimentacoes mantem estoque fisico para produto simples', () => {
  const produto = {
    tipo_produto: 'SIMPLES',
    tipo_kit: null,
    estoque_atual: 12,
    estoque_virtual: 31,
    estoque_disponivel: 31,
    estoque_reservado: 2,
  };

  assert.equal(resolverEstoqueAtualMovimentacoes(produto), 12);
  assert.equal(resolverSaldoDisponivelMovimentacoes(produto), 10);
});
