/**
 * API Client para o módulo de Clientes
 */

import api from '../api';

/**
 * Buscar clientes
 */
export const buscarClientes = async (params = {}) => {
  const response = await api.get('/clientes/', { params });
  // API retorna objeto paginado {items: [], total, skip, limit}
  // Retornar apenas o array de clientes
  return response.data.items || response.data.clientes || response.data || [];
};

/**
 * Buscar cliente por ID
 */
export const buscarClientePorId = async (clienteId) => {
  const response = await api.get(`/clientes/${clienteId}`);
  return response.data;
};

/**
 * Criar novo cliente
 */
export const criarCliente = async (dados) => {
  const response = await api.post('/clientes/', dados);
  return response.data;
};

/**
 * Atualizar cliente
 */
export const atualizarCliente = async (clienteId, dados) => {
  const response = await api.put(`/clientes/${clienteId}`, dados);
  return response.data;
};

/**
 * Deletar cliente
 */
export const deletarCliente = async (clienteId) => {
  const response = await api.delete(`/clientes/${clienteId}`);
  return response.data;
};

/**
 * Buscar raças por espécie
 */
export const buscarRacas = async (especie) => {
  const response = await api.get(`/clientes/racas?especie=${especie}`);
  return response.data;
};

/**
 * Verificar duplicata
 */
export const verificarDuplicata = async (campo, valor) => {
  const params = new URLSearchParams({ [campo]: valor });
  const response = await api.get(`/clientes/verificar-duplicata/campo?${params.toString()}`);
  return response.data;
};
