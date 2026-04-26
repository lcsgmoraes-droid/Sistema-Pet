import { api } from "../../services/api";

const BASE = "/banho-tosa";

export const banhoTosaApi = {
  listarFuncionariosApoio: (params) =>
    api.get(`${BASE}/apoios/funcionarios`, { params }),
  listarProdutosEstoque: (busca) =>
    api.get(`${BASE}/apoios/produtos-estoque`, { params: { busca } }),
  dashboard: (params) => api.get(`${BASE}/dashboard`, { params }),
  obterConfiguracao: () => api.get(`${BASE}/configuracao`),
  atualizarConfiguracao: (data) => api.patch(`${BASE}/configuracao`, data),
  aplicarDefaults: () => api.post(`${BASE}/defaults/aplicar`),
  listarRecursos: (params) => api.get(`${BASE}/recursos`, { params }),
  criarRecurso: (data) => api.post(`${BASE}/recursos`, data),
  atualizarRecurso: (id, data) => api.patch(`${BASE}/recursos/${id}`, data),
  listarServicos: (params) => api.get(`${BASE}/servicos`, { params }),
  criarServico: (data) => api.post(`${BASE}/servicos`, data),
  atualizarServico: (id, data) => api.patch(`${BASE}/servicos/${id}`, data),
  removerServico: (id) => api.delete(`${BASE}/servicos/${id}`),
  listarParametrosPorte: (params) =>
    api.get(`${BASE}/parametros-porte`, { params }),
  criarParametroPorte: (data) => api.post(`${BASE}/parametros-porte`, data),
  atualizarParametroPorte: (id, data) =>
    api.patch(`${BASE}/parametros-porte/${id}`, data),
  listarAgendamentos: (params) => api.get(`${BASE}/agendamentos`, { params }),
  obterCapacidadeAgenda: (dataReferencia) =>
    api.get(`${BASE}/agendamentos/capacidade`, {
      params: { data_referencia: dataReferencia },
    }),
  listarSugestoesSlots: (params) =>
    api.get(`${BASE}/agendamentos/sugestoes-slots`, { params }),
  criarAgendamento: (data) => api.post(`${BASE}/agendamentos`, data),
  atualizarStatusAgendamento: (id, data) =>
    api.patch(`${BASE}/agendamentos/${id}/status`, data),
  checkInAgendamento: (id) => api.post(`${BASE}/agendamentos/${id}/check-in`),
  listarAtendimentos: (params) => api.get(`${BASE}/atendimentos`, { params }),
  obterAtendimento: (id) => api.get(`${BASE}/atendimentos/${id}`),
  listarPendenciasFechamento: (params) =>
    api.get(`${BASE}/fechamentos/pendencias`, { params }),
  sincronizarPendenciasFechamento: (params) =>
    api.post(`${BASE}/fechamentos/pendencias/sincronizar`, null, { params }),
  atualizarStatusAtendimento: (id, data) =>
    api.patch(`${BASE}/atendimentos/${id}/status`, data),
  gerarVendaAtendimento: (id) =>
    api.post(`${BASE}/atendimentos/${id}/venda`),
  sincronizarFechamentoAtendimento: (id) =>
    api.post(`${BASE}/atendimentos/${id}/fechamento/sincronizar`),
  listarInsumosAtendimento: (atendimentoId) =>
    api.get(`${BASE}/atendimentos/${atendimentoId}/insumos`),
  registrarInsumoAtendimento: (atendimentoId, data) =>
    api.post(`${BASE}/atendimentos/${atendimentoId}/insumos`, data),
  atualizarInsumoAtendimento: (atendimentoId, insumoId, data) =>
    api.patch(`${BASE}/atendimentos/${atendimentoId}/insumos/${insumoId}`, data),
  estornarEstoqueInsumo: (atendimentoId, insumoId) =>
    api.post(`${BASE}/atendimentos/${atendimentoId}/insumos/${insumoId}/estornar-estoque`),
  removerInsumoAtendimento: (atendimentoId, insumoId) =>
    api.delete(`${BASE}/atendimentos/${atendimentoId}/insumos/${insumoId}`),
  listarOcorrenciasAtendimento: (atendimentoId) =>
    api.get(`${BASE}/atendimentos/${atendimentoId}/ocorrencias`),
  registrarOcorrenciaAtendimento: (atendimentoId, data) =>
    api.post(`${BASE}/atendimentos/${atendimentoId}/ocorrencias`, data),
  removerOcorrenciaAtendimento: (atendimentoId, ocorrenciaId) =>
    api.delete(`${BASE}/atendimentos/${atendimentoId}/ocorrencias/${ocorrenciaId}`),
  listarFotosAtendimento: (atendimentoId) =>
    api.get(`${BASE}/atendimentos/${atendimentoId}/fotos`),
  registrarFotoAtendimento: (atendimentoId, data) =>
    api.post(`${BASE}/atendimentos/${atendimentoId}/fotos`, data),
  uploadFotoAtendimento: (atendimentoId, data) =>
    api.post(`${BASE}/atendimentos/${atendimentoId}/fotos/upload`, data),
  removerFotoAtendimento: (atendimentoId, fotoId) =>
    api.delete(`${BASE}/atendimentos/${atendimentoId}/fotos/${fotoId}`),
  iniciarEtapa: (atendimentoId, data) =>
    api.post(`${BASE}/atendimentos/${atendimentoId}/etapas`, data),
  atualizarEtapa: (atendimentoId, etapaId, data) =>
    api.patch(`${BASE}/atendimentos/${atendimentoId}/etapas/${etapaId}`, data),
  finalizarEtapa: (atendimentoId, etapaId, data) =>
    api.post(`${BASE}/atendimentos/${atendimentoId}/etapas/${etapaId}/finalizar`, data),
  obterCustoAtendimento: (id) => api.get(`${BASE}/custos/atendimentos/${id}`),
  recalcularCustoAtendimento: (id) =>
    api.post(`${BASE}/custos/atendimentos/${id}/recalcular`),
  simularCusto: (data) => api.post(`${BASE}/custos/simular`, data),
  listarTaxiDog: (params) => api.get(`${BASE}/taxi-dog`, { params }),
  criarTaxiDog: (data) => api.post(`${BASE}/taxi-dog`, data),
  atualizarTaxiDog: (id, data) => api.patch(`${BASE}/taxi-dog/${id}`, data),
  atualizarStatusTaxiDog: (id, data) =>
    api.patch(`${BASE}/taxi-dog/${id}/status`, data),
  listarPacotes: (params) => api.get(`${BASE}/pacotes`, { params }),
  criarPacote: (data) => api.post(`${BASE}/pacotes`, data),
  atualizarPacote: (id, data) => api.patch(`${BASE}/pacotes/${id}`, data),
  listarCreditosPacote: (params) =>
    api.get(`${BASE}/pacotes/creditos`, { params }),
  criarCreditoPacote: (data) => api.post(`${BASE}/pacotes/creditos`, data),
  consumirCreditoPacote: (creditoId, data) =>
    api.post(`${BASE}/pacotes/creditos/${creditoId}/consumir`, data),
  estornarCreditoPacote: (creditoId, data) =>
    api.post(`${BASE}/pacotes/creditos/${creditoId}/estornar`, data),
  listarRecorrenciasPacote: (params) =>
    api.get(`${BASE}/pacotes/recorrencias`, { params }),
  criarRecorrenciaPacote: (data) =>
    api.post(`${BASE}/pacotes/recorrencias`, data),
  atualizarRecorrenciaPacote: (id, data) =>
    api.patch(`${BASE}/pacotes/recorrencias/${id}`, data),
  listarRetornosSugestoes: (params) =>
    api.get(`${BASE}/retornos/sugestoes`, { params }),
  avancarRetornoRecorrencia: (id, data) =>
    api.post(`${BASE}/retornos/recorrencias/${id}/avancar`, data),
  enfileirarNotificacoesRetorno: (data) =>
    api.post(`${BASE}/retornos/notificacoes/enfileirar`, data),
  listarRetornoTemplates: (params) =>
    api.get(`${BASE}/retornos/templates`, { params }),
  criarRetornoTemplate: (data) =>
    api.post(`${BASE}/retornos/templates`, data),
  atualizarRetornoTemplate: (id, data) =>
    api.patch(`${BASE}/retornos/templates/${id}`, data),
  relatorioOperacional: (params) =>
    api.get(`${BASE}/relatorios/operacional`, { params }),
};
