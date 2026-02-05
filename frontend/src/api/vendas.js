/**
 * API Client para o módulo de Vendas (PDV)
 */

import api from '../api';

/**
 * Listar vendas com filtros
 */
export const listarVendas = async (params = {}) => {
  const response = await api.get('/vendas', { params });
  return response.data;
};

/**
 * Buscar uma venda específica
 */
export const buscarVenda = async (vendaId) => {
  const response = await api.get(`/vendas/${vendaId}`);
  return response.data;
};

/**
 * Criar nova venda
 */
export const criarVenda = async (dados) => {
  const response = await api.post('/vendas', dados);
  return response.data;
};

/**
 * Atualizar venda
 */
export const atualizarVenda = async (vendaId, dados) => {
  const response = await api.put(`/vendas/${vendaId}`, dados);
  return response.data;
};

/**
 * Finalizar venda (com pagamentos)
 */
export const finalizarVenda = async (vendaId, pagamentos) => {
  const response = await api.post(`/vendas/${vendaId}/finalizar`, {
    pagamentos
  });
  return response.data;
};

/**
 * Cancelar venda
 */
export const cancelarVenda = async (vendaId, motivo) => {
  const response = await api.post(`/vendas/${vendaId}/cancelar`, {
    motivo
  });
  return response.data;
};

/**
 * Buscar configurações de entrega
 */
export const buscarConfigEntrega = async () => {
  const response = await api.get('/vendas/configuracoes-entrega');
  return response.data;
};

/**
 * Salvar configurações de entrega
 */
export const salvarConfigEntrega = async (config) => {
  const response = await api.post('/vendas/configuracoes-entrega', config);
  return response.data;
};

/**
 * Relatório resumo de vendas
 */
export const relatorioResumo = async (dataInicio, dataFim) => {
  const params = {};
  if (dataInicio) params.data_inicio = dataInicio;
  if (dataFim) params.data_fim = dataFim;
  
  const response = await api.get('/vendas/relatorios/resumo', { params });
  return response.data;
};
