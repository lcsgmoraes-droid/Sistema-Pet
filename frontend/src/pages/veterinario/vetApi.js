/**
 * Hook centralizado para chamadas à API veterinária.
 */
import { api } from "../../services/api";

const BASE = "/vet";

export const vetApi = {
  // Dashboard
  dashboard: () => api.get(`${BASE}/dashboard`),

  // Agendamentos
  listarAgendamentos: (params) => api.get(`${BASE}/agendamentos`, { params }),
  criarAgendamento: (data) => api.post(`${BASE}/agendamentos`, data),
  atualizarAgendamento: (id, data) => api.patch(`${BASE}/agendamentos/${id}`, data),

  // Consultas
  listarConsultas: (params) => api.get(`${BASE}/consultas`, { params }),
  obterConsulta: (id) => api.get(`${BASE}/consultas/${id}`),
  criarConsulta: (data) => api.post(`${BASE}/consultas`, data),
  atualizarConsulta: (id, data) => api.patch(`${BASE}/consultas/${id}`, data),
  finalizarConsulta: (id) => api.post(`${BASE}/consultas/${id}/finalizar`),

  // Prescrições
  listarPrescricoes: (consultaId) => api.get(`${BASE}/consultas/${consultaId}/prescricoes`),
  criarPrescricao: (data) => api.post(`${BASE}/prescricoes`, data),

  // Vacinas
  listarVacinasPet: (petId) => api.get(`${BASE}/pets/${petId}/vacinas`),
  registrarVacina: (data) => api.post(`${BASE}/vacinas`, data),
  vacinasVencendo: (dias = 30) => api.get(`${BASE}/vacinas/vencendo`, { params: { dias } }),

  // Exames
  listarExamesPet: (petId) => api.get(`${BASE}/pets/${petId}/exames`),
  criarExame: (data) => api.post(`${BASE}/exames`, data),
  atualizarExame: (id, data) => api.patch(`${BASE}/exames/${id}`, data),

  // Peso
  curvaPeso: (petId) => api.get(`${BASE}/pets/${petId}/peso`),
  registrarPeso: (petId, pesos, obs) =>
    api.post(`${BASE}/pets/${petId}/peso`, null, { params: { peso_kg: pesos, observacoes: obs } }),

  // Procedimentos
  listarProcedimentosConsulta: (consultaId) => api.get(`${BASE}/consultas/${consultaId}/procedimentos`),
  adicionarProcedimento: (data) => api.post(`${BASE}/procedimentos`, data),

  // Internações
  listarInternacoes: (status) => api.get(`${BASE}/internacoes`, { params: { status } }),
  criarInternacao: (data) => api.post(`${BASE}/internacoes`, data),
  registrarEvolucao: (internacaoId, data) => api.post(`${BASE}/internacoes/${internacaoId}/evolucao`, data),
  darAlta: (internacaoId, obs) =>
    api.patch(`${BASE}/internacoes/${internacaoId}/alta`, null, { params: { observacoes: obs } }),

  // Catálogos
  listarCatalogoProcedimentos: () => api.get(`${BASE}/catalogo/procedimentos`),
  criarCatalogoProcedimento: (data) => api.post(`${BASE}/catalogo/procedimentos`, data),
  listarMedicamentos: (busca) => api.get(`${BASE}/catalogo/medicamentos`, { params: { busca } }),
  criarMedicamento: (data) => api.post(`${BASE}/catalogo/medicamentos`, data),
  listarProtocolosVacinas: () => api.get(`${BASE}/catalogo/protocolos-vacinas`),

  // Perfil comportamental
  obterPerfilComportamental: (petId) => api.get(`${BASE}/pets/${petId}/perfil-comportamental`),
  salvarPerfilComportamental: (petId, data) => api.put(`${BASE}/pets/${petId}/perfil-comportamental`, data),
};
