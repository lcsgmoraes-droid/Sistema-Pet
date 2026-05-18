import api from "./api";

export interface VetPessoaResumo {
  id: number;
  nome: string;
  crmv?: string | null;
  email?: string | null;
}

export interface VetAgendamento {
  id: number;
  pet_id: number;
  pet_nome?: string | null;
  pet_codigo?: string | null;
  cliente_nome?: string | null;
  veterinario_nome?: string | null;
  consultorio_nome?: string | null;
  data_hora?: string | null;
  duracao_minutos?: number | null;
  tipo?: string | null;
  motivo?: string | null;
  status?: string | null;
  consulta_id?: number | null;
}

export interface VetPetResumo {
  id: number;
  codigo?: string | null;
  cliente_id: number;
  nome: string;
  especie?: string | null;
  raca?: string | null;
  peso?: number | null;
  foto_url?: string | null;
  cliente_nome?: string | null;
  cliente_telefone?: string | null;
  cliente_celular?: string | null;
}

export interface VetConsultorio {
  id: number;
  nome: string;
  descricao?: string | null;
}

export interface VetAgendamentoPayload {
  pet_id: number;
  data_hora: string;
  duracao_minutos?: number;
  tipo?: string;
  motivo?: string | null;
  consultorio_id?: number | null;
  is_emergencia?: boolean;
  observacoes?: string | null;
}

export interface VetInternacao {
  id: number;
  pet_id: number;
  pet_nome: string;
  pet_codigo?: string | null;
  pet_especie?: string | null;
  consulta_id?: number | null;
  veterinario_id?: number | null;
  data_entrada?: string | null;
  data_saida?: string | null;
  motivo?: string | null;
  baia?: string | null;
  status?: string | null;
  observacoes?: string | null;
}

export interface VetProcedimentoAgenda {
  id: number;
  internacao_id: number;
  pet_id: number;
  pet_nome: string;
  baia?: string | null;
  horario?: string | null;
  horario_agendado?: string | null;
  medicamento: string;
  dose?: string | null;
  via?: string | null;
  quantidade_prevista?: number | null;
  unidade_quantidade?: string | null;
  observacoes?: string | null;
  status?: string | null;
  feito?: boolean;
}

export interface VetProcedimentoAgendaPayload {
  horario_agendado: string;
  medicamento: string;
  dose?: string | null;
  via?: string | null;
  quantidade_prevista?: number | null;
  unidade_quantidade?: string | null;
  lembrete_min?: number | null;
  observacoes_agenda?: string | null;
}

export interface VetEvolucaoInternacao {
  id: number;
  data_hora?: string | null;
  temperatura?: number | null;
  freq_cardiaca?: number | null;
  freq_respiratoria?: number | null;
  nivel_dor?: number | null;
  pressao_sistolica?: number | null;
  glicemia?: number | null;
  peso?: number | null;
  observacoes?: string | null;
}

export interface VetProcedimentoRealizado {
  id: number;
  data_hora?: string | null;
  status?: string | null;
  tipo_registro?: string | null;
  horario_agendado?: string | null;
  medicamento?: string | null;
  dose?: string | null;
  via?: string | null;
  quantidade_prevista?: number | null;
  quantidade_executada?: number | null;
  unidade_quantidade?: string | null;
  executado_por?: string | null;
  horario_execucao?: string | null;
  observacao_execucao?: string | null;
  observacoes_agenda?: string | null;
}

export interface VetInternacaoDetalhe extends VetInternacao {
  tutor_id?: number | null;
  tutor_nome?: string | null;
  pet_raca?: string | null;
  evolucoes: VetEvolucaoInternacao[];
  procedimentos_realizados: VetProcedimentoRealizado[];
  procedimentos_agenda: VetProcedimentoAgenda[];
}

export interface VetMedicamento {
  id: number;
  nome: string;
  nome_comercial?: string | null;
  principio_ativo?: string | null;
  posologia_referencia?: string | null;
  dose_min_mgkg?: number | null;
  dose_max_mgkg?: number | null;
  especies_indicadas?: string[];
  concentracao?: string | null;
  forma_farmaceutica?: string | null;
  eh_antibiotico?: boolean;
  eh_controlado?: boolean;
}

export interface VetResumo {
  veterinario: VetPessoaResumo;
  data: string;
  agendamentos_hoje: VetAgendamento[];
  internacoes_ativas: VetInternacao[];
  procedimentos_pendentes: VetProcedimentoAgenda[];
}

export interface VetAgendaFiltros {
  data?: string;
  data_inicio?: string;
  data_fim?: string;
}

export async function obterResumoVet(data?: string): Promise<VetResumo> {
  const { data: response } = await api.get<VetResumo>("/app/vet/resumo", {
    params: data ? { data } : undefined,
  });
  return response;
}

export async function listarPetsVet(busca?: string): Promise<VetPetResumo[]> {
  const { data } = await api.get<VetPetResumo[]>("/app/vet/pets", {
    params: busca ? { busca } : undefined,
  });
  return data;
}

export async function listarConsultoriosVet(): Promise<VetConsultorio[]> {
  const { data } = await api.get<VetConsultorio[]>("/app/vet/consultorios");
  return data;
}

export async function listarAgendamentosVet(filtros?: string | VetAgendaFiltros): Promise<VetAgendamento[]> {
  const params = typeof filtros === "string" ? { data: filtros } : filtros;
  const { data: response } = await api.get<VetAgendamento[]>("/app/vet/agendamentos", {
    params,
  });
  return response;
}

export async function criarAgendamentoVet(payload: VetAgendamentoPayload): Promise<VetAgendamento> {
  const { data } = await api.post<VetAgendamento>("/app/vet/agendamentos", payload);
  return data;
}

export async function listarInternacoesVet(): Promise<VetInternacao[]> {
  const { data } = await api.get<VetInternacao[]>("/app/vet/internacoes");
  return data;
}

export async function obterInternacaoVet(id: number): Promise<VetInternacaoDetalhe> {
  const { data } = await api.get<VetInternacaoDetalhe>(`/app/vet/internacoes/${id}`);
  return data;
}

export async function listarProcedimentosVet(): Promise<VetProcedimentoAgenda[]> {
  const { data } = await api.get<VetProcedimentoAgenda[]>("/app/vet/procedimentos-agenda");
  return data;
}

export async function concluirProcedimentoVet(id: number): Promise<VetProcedimentoAgenda> {
  const { data } = await api.patch<VetProcedimentoAgenda>(`/app/vet/procedimentos-agenda/${id}/concluir`, {});
  return data;
}

export async function criarProcedimentoAgendaVet(
  internacaoId: number,
  payload: VetProcedimentoAgendaPayload,
): Promise<VetProcedimentoAgenda> {
  const { data } = await api.post<VetProcedimentoAgenda>(
    `/app/vet/internacoes/${internacaoId}/procedimentos-agenda`,
    payload,
  );
  return data;
}

export async function listarMedicamentosVet(busca?: string): Promise<VetMedicamento[]> {
  const { data } = await api.get<VetMedicamento[]>("/app/vet/catalogo/medicamentos", {
    params: busca ? { busca } : undefined,
  });
  return data;
}
