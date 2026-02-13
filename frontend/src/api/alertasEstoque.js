/**
 * API de Alertas de Estoque Negativo
 * Integração com backend de monitoramento de estoque crítico
 */
import api from '../api';

/**
 * Listar alertas pendentes (não resolvidos)
 */
export const getAlertasPendentes = () => {
  return api.get('/estoque/alertas/pendentes');
};

/**
 * Listar todos os alertas (histórico completo)
 */
export const getTodosAlertas = (params = {}) => {
  return api.get('/estoque/alertas/todos', { params });
};

/**
 * Obter dashboard com métricas de alertas
 */
export const getDashboardAlertas = () => {
  return api.get('/estoque/alertas/dashboard');
};

/**
 * Resolver ou ignorar um alerta
 * @param {number} alertaId - ID do alerta
 * @param {string} acao - 'resolvido' ou 'ignorado'
 * @param {string} observacao - Observação opcional
 */
export const resolverAlerta = (alertaId, acao, observacao = null) => {
  return api.put(`/estoque/alertas/${alertaId}/resolver`, {
    acao,
    observacao
  });
};

/**
 * Excluir alerta
 * @param {number} alertaId - ID do alerta
 */
export const deletarAlerta = (alertaId) => {
  return api.delete(`/estoque/alertas/${alertaId}`);
};
