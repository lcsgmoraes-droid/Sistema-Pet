/**
 * Hook centralizado para chamadas à API veterinária.
 */
import { api } from "../../services/api";

const BASE = "/vet";

export const vetApi = {
  // Dashboard
  dashboard: () => api.get(`${BASE}/dashboard`),
  relatorioClinico: (params) => api.get(`${BASE}/relatorios/clinicos`, { params }),
  exportarRelatorioClinicoCsv: (params) =>
    api.get(`${BASE}/relatorios/clinicos/export.csv`, { params, responseType: "blob" }),

  // Agendamentos
  listarAgendamentos: (params) => api.get(`${BASE}/agendamentos`, { params }),
  criarAgendamento: (data) => api.post(`${BASE}/agendamentos`, data),
  atualizarAgendamento: (id, data) => api.patch(`${BASE}/agendamentos/${id}`, data),
  removerAgendamento: (id) => api.delete(`${BASE}/agendamentos/${id}`),
  desfazerInicioAgendamento: (id) => api.post(`${BASE}/agendamentos/${id}/desfazer-inicio`),
  obterCalendarioAgendaMeta: () => api.get(`${BASE}/agenda/calendario`),
  regenerarCalendarioAgendaToken: () => api.post(`${BASE}/agenda/calendario/token`),
  baixarCalendarioAgendaIcs: () =>
    api.get(`${BASE}/agenda/calendario.ics`, { responseType: "blob" }),

  // Consultas
  listarConsultas: (params) => api.get(`${BASE}/consultas`, { params }),
  obterConsulta: (id) => api.get(`${BASE}/consultas/${id}`),
  obterTimelineConsulta: (id) => api.get(`${BASE}/consultas/${id}/timeline`),
  criarConsulta: (data) => api.post(`${BASE}/consultas`, data),
  atualizarConsulta: (id, data) => api.patch(`${BASE}/consultas/${id}`, data),
  finalizarConsulta: (id) => api.post(`${BASE}/consultas/${id}/finalizar`),
  validarAssinaturaConsulta: (id) => api.get(`${BASE}/consultas/${id}/assinatura`),
  baixarProntuarioPdf: (id) =>
    api.get(`${BASE}/consultas/${id}/prontuario.pdf`, { responseType: "blob" }),

  // Prescrições
  listarPrescricoes: (consultaId) => api.get(`${BASE}/consultas/${consultaId}/prescricoes`),
  criarPrescricao: (data) => api.post(`${BASE}/prescricoes`, data),
  baixarPrescricaoPdf: (prescricaoId) =>
    api.get(`${BASE}/prescricoes/${prescricaoId}/pdf`, { responseType: "blob" }),

  // Veterinários
  listarVeterinarios: () => api.get(`${BASE}/veterinarios`),
  listarConsultorios: (params) => api.get(`${BASE}/consultorios`, { params }),
  criarConsultorio: (data) => api.post(`${BASE}/consultorios`, data),
  atualizarConsultorio: (id, data) => api.patch(`${BASE}/consultorios/${id}`, data),
  removerConsultorio: (id) => api.delete(`${BASE}/consultorios/${id}`),

  // Vacinas
  listarVacinasPet: (petId) => api.get(`${BASE}/pets/${petId}/vacinas`),
  registrarVacina: (data) => api.post(`${BASE}/vacinas`, data),
  vacinasVencendo: (dias = 30) => api.get(`${BASE}/vacinas/vencendo`, { params: { dias } }),
  obterCarteirinhaPet: (petId) => api.get(`${BASE}/pets/${petId}/carteirinha`),
  listarAlertasPet: (petId) => api.get(`${BASE}/pets/${petId}/alertas`),

  // Exames
  listarExamesPet: (petId) => api.get(`${BASE}/pets/${petId}/exames`),
  listarExamesAnexados: (params) => api.get(`${BASE}/exames`, { params }),
  criarExame: (data) => api.post(`${BASE}/exames`, data),
  atualizarExame: (id, data) => api.patch(`${BASE}/exames/${id}`, data),
  interpretarExameIA: (id) => api.post(`${BASE}/exames/${id}/interpretar-ia`),
  processarArquivoExameIA: (id) => api.post(`${BASE}/exames/${id}/processar-arquivo-ia`),
  uploadArquivoExame: (id, file) => {
    const formData = new FormData();
    formData.append("arquivo", file);
    return api.post(`${BASE}/exames/${id}/arquivo`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  // Peso
  curvaPeso: (petId) => api.get(`${BASE}/pets/${petId}/peso`),
  registrarPeso: (petId, pesos, obs) =>
    api.post(`${BASE}/pets/${petId}/peso`, null, { params: { peso_kg: pesos, observacoes: obs } }),

  // Procedimentos
  listarProcedimentosConsulta: (consultaId) => api.get(`${BASE}/consultas/${consultaId}/procedimentos`),
  adicionarProcedimento: (data) => api.post(`${BASE}/procedimentos`, data),
  diagnosticoPushAgendamento: (agendamentoId) => api.get(`${BASE}/agendamentos/${agendamentoId}/push-diagnostico`),

  // Internações
  listarInternacoes: (statusOrParams) => {
    const params = (statusOrParams && typeof statusOrParams === "object")
      ? statusOrParams
      : { status: statusOrParams };
    return api.get(`${BASE}/internacoes`, { params });
  },
  obterInternacao: (internacaoId) => api.get(`${BASE}/internacoes/${internacaoId}`),
  criarInternacao: (data) => api.post(`${BASE}/internacoes`, data),
  registrarEvolucao: (internacaoId, data) => api.post(`${BASE}/internacoes/${internacaoId}/evolucao`, data),
  registrarProcedimentoInternacao: (internacaoId, data) => api.post(`${BASE}/internacoes/${internacaoId}/procedimento`, data),
  obterConfigInternacao: () => api.get(`${BASE}/internacoes/config`),
  atualizarConfigInternacao: (data) => api.put(`${BASE}/internacoes/config`, data),
  listarProcedimentosAgendaInternacao: (params) => api.get(`${BASE}/internacoes/procedimentos-agenda`, { params }),
  criarProcedimentoAgendaInternacao: (internacaoId, data) =>
    api.post(`${BASE}/internacoes/${internacaoId}/procedimentos-agenda`, data),
  concluirProcedimentoAgendaInternacao: (agendaId, data) =>
    api.patch(`${BASE}/internacoes/procedimentos-agenda/${agendaId}/concluir`, data),
  removerProcedimentoAgendaInternacao: (agendaId) =>
    api.delete(`${BASE}/internacoes/procedimentos-agenda/${agendaId}`),
  historicoInternacoesPet: async (petId) => {
    const base = await api.get(`${BASE}/internacoes`, {
      params: {
        status: "",
        pet_id: petId,
      },
    });

    const lista = Array.isArray(base.data)
      ? base.data
      : (base.data?.items ?? []);

    const historicoDetalhado = await Promise.all(
      lista.map(async (internacao) => {
        try {
          const detalhe = await api.get(`${BASE}/internacoes/${internacao.id}`);
          return {
            internacao_id: internacao.id,
            status: detalhe.data?.status ?? internacao.status,
            motivo: detalhe.data?.motivo ?? internacao.motivo,
            box: detalhe.data?.box ?? internacao.box,
            data_entrada: detalhe.data?.data_entrada ?? internacao.data_entrada,
            data_saida: detalhe.data?.data_saida ?? internacao.data_saida,
            observacoes_alta: detalhe.data?.observacoes_alta ?? internacao.observacoes_alta,
            evolucoes: detalhe.data?.evolucoes ?? [],
            procedimentos: detalhe.data?.procedimentos ?? [],
          };
        } catch {
          return {
            internacao_id: internacao.id,
            status: internacao.status,
            motivo: internacao.motivo,
            box: internacao.box,
            data_entrada: internacao.data_entrada,
            data_saida: internacao.data_saida,
            observacoes_alta: internacao.observacoes_alta,
            evolucoes: [],
            procedimentos: [],
          };
        }
      })
    );

    return {
      ...base,
      data: {
        pet_id: petId,
        historico: historicoDetalhado,
      },
    };
  },
  darAlta: (internacaoId, obs) =>
    api.patch(`${BASE}/internacoes/${internacaoId}/alta`, null, { params: { observacoes: obs } }),

  // Catálogos
  listarCatalogoProcedimentos: () => api.get(`${BASE}/catalogo/procedimentos`),
  criarCatalogoProcedimento: (data) => api.post(`${BASE}/catalogo/procedimentos`, data),
  atualizarCatalogoProcedimento: (id, data) => api.patch(`${BASE}/catalogo/procedimentos/${id}`, data),
  removerCatalogoProcedimento: (id) => api.delete(`${BASE}/catalogo/procedimentos/${id}`),
  listarProdutosEstoque: (busca) => api.get(`${BASE}/catalogo/produtos-estoque`, { params: { busca } }),
  listarMedicamentos: (busca) => api.get(`${BASE}/catalogo/medicamentos`, { params: { busca } }),
  criarMedicamento: (data) => api.post(`${BASE}/catalogo/medicamentos`, data),
  atualizarMedicamento: (id, data) => api.patch(`${BASE}/catalogo/medicamentos/${id}`, data),
  removerMedicamento: (id) => api.delete(`${BASE}/catalogo/medicamentos/${id}`),
  listarProtocolosVacinas: () => api.get(`${BASE}/catalogo/protocolos-vacinas`),
  criarProtocoloVacina: (params) => api.post(`${BASE}/catalogo/protocolos-vacinas`, null, { params }),
  atualizarProtocoloVacina: (id, data) => api.patch(`${BASE}/catalogo/protocolos-vacinas/${id}`, data),
  removerProtocoloVacina: (id) => api.delete(`${BASE}/catalogo/protocolos-vacinas/${id}`),

  // Perfil comportamental
  obterPerfilComportamental: (petId) => api.get(`${BASE}/pets/${petId}/perfil-comportamental`),
  salvarPerfilComportamental: (petId, data) => api.put(`${BASE}/pets/${petId}/perfil-comportamental`, data),

  // Parceiros (Multi-Tenant)
  listarParceiros: () => api.get(`${BASE}/parceiros`),
  criarParceiro: (data) => api.post(`${BASE}/parceiros`, data),
  atualizarParceiro: (id, data) => api.patch(`${BASE}/parceiros/${id}`, data),
  removerParceiro: (id) => api.delete(`${BASE}/parceiros/${id}`),
  listarTenantsVeterinarios: () => api.get(`${BASE}/tenants-veterinarios`),

  // Relatório de repasse
  relatorioRepasse: (params) => api.get(`${BASE}/relatorios/repasse`, { params }),
  baixarRepasse: (contaId, dataRecebimento) =>
    api.post(`${BASE}/relatorios/repasse/${contaId}/baixar`, null, {
      params: dataRecebimento ? { data_recebimento: dataRecebimento } : {},
    }),

  // Chat IA de exames
  chatExameIA: (exameId, pergunta) =>
    api.post(`${BASE}/exames/${exameId}/chat`, { pergunta }),

  // Assistente IA clínico (livre ou vinculado ao atendimento)
  assistenteIA: (payload) => api.post(`${BASE}/ia/assistente`, payload),
  memoriaStatusAssistenteIA: () => api.get(`${BASE}/ia/memoria-status`),
  listarConversasAssistenteIA: (params) => api.get(`${BASE}/ia/conversas`, { params }),
  listarMensagensConversaAssistenteIA: (conversaId) => api.get(`${BASE}/ia/conversas/${conversaId}/mensagens`),
  feedbackMensagemAssistenteIA: (mensagemId, payload) =>
    api.post(`${BASE}/ia/mensagens/${mensagemId}/feedback`, payload),

  // Calendário preventivo
  calendarioPreventivo: (especie) =>
    api.get(`${BASE}/catalogo/calendario-preventivo`, { params: especie ? { especie } : {} }),
};
