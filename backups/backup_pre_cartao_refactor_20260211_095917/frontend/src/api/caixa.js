/**
 * API Client para o módulo de Controle de Caixa
 */

import api from '../api';

/**
 * Abrir novo caixa
 */
export const abrirCaixa = async (dados) => {
  const response = await api.post('/caixas/abrir', dados);
  return response.data;
};

/**
 * Obter caixa aberto do usuário atual
 */
export const obterCaixaAberto = async () => {
  const response = await api.get('/caixas/aberto');
  return response.data;
};

/**
 * Listar caixas
 */
export const listarCaixas = async (params = {}) => {
  const response = await api.get('/caixas', { params });
  return response.data;
};

/**
 * Obter detalhes de um caixa
 */
export const obterCaixa = async (caixaId) => {
  const response = await api.get(`/caixas/${caixaId}`);
  return response.data;
};

/**
 * Adicionar movimentação ao caixa
 */
export const adicionarMovimentacao = async (caixaId, dados) => {
  const response = await api.post(`/caixas/${caixaId}/movimentacao`, dados);
  return response.data;
};

/**
 * Fechar caixa
 */
export const fecharCaixa = async (caixaId, dados) => {
  const response = await api.post(`/caixas/${caixaId}/fechar`, dados);
  return response.data;
};

/**
 * Reabrir caixa
 */
export const reabrirCaixa = async (caixaId) => {
  const response = await api.post(`/caixas/${caixaId}/reabrir`);
  return response.data;
};

/**
 * Obter resumo do caixa
 */
export const obterResumoCaixa = async (caixaId) => {
  const response = await api.get(`/caixas/${caixaId}/resumo`);
  return response.data;
};
