import api from "./api";

export interface BanhoTosaServicoResumo {
  id: number;
  nome: string;
  categoria?: string | null;
  duracao_padrao_minutos: number;
  preco_base: number;
}

export interface BanhoTosaRecursoResumo {
  id: number;
  nome: string;
  tipo: string;
  capacidade_simultanea: number;
}

export interface BanhoTosaFuncionarioResumo {
  id: number;
  nome: string;
  tipo_cadastro?: string | null;
}

export interface BanhoTosaPetResumo {
  id: number;
  nome: string;
  codigo?: string | null;
  especie?: string | null;
  raca?: string | null;
  porte?: string | null;
  cliente_id: number;
  cliente_nome?: string | null;
  cliente_telefone?: string | null;
}

export interface BanhoTosaAgendamentoServico {
  id?: number;
  servico_id?: number | null;
  nome_servico_snapshot: string;
  quantidade: number;
  valor_unitario: number;
  desconto?: number;
  tempo_previsto_minutos?: number;
}

export interface FuncionarioBanhoTosaAgendamento {
  id: number;
  cliente_id: number;
  cliente_nome?: string | null;
  pet_id: number;
  pet_nome?: string | null;
  pet_foto_url?: string | null;
  pet_especie?: string | null;
  pet_porte?: string | null;
  recurso_id?: number | null;
  recurso_nome?: string | null;
  data_hora_inicio: string;
  data_hora_fim_prevista?: string | null;
  status: string;
  origem?: string | null;
  observacoes?: string | null;
  valor_previsto: number;
  taxi_dog_id?: number | null;
  servicos: BanhoTosaAgendamentoServico[];
}

export interface BanhoTosaEtapaResumo {
  id: number;
  tipo: string;
  responsavel_id?: number | null;
  responsavel_nome?: string | null;
  recurso_id?: number | null;
  recurso_nome?: string | null;
  inicio_em?: string | null;
  fim_em?: string | null;
  tempo_previsto_minutos?: number | null;
  tempo_decorrido_segundos?: number | null;
  atraso_segundos?: number | null;
  atrasado?: boolean;
  observacoes?: string | null;
}

export interface FuncionarioBanhoTosaAtendimento {
  id: number;
  agendamento_id?: number | null;
  cliente_id: number;
  cliente_nome?: string | null;
  pet_id: number;
  pet_nome?: string | null;
  pet_foto_url?: string | null;
  pet_especie?: string | null;
  pet_porte?: string | null;
  status: string;
  checkin_em?: string | null;
  observacoes_entrada?: string | null;
  restricoes_veterinarias_snapshot?: Record<string, unknown>;
  etapa_atual_codigo: string;
  etapa_atual_label: string;
  proxima_etapa_codigo?: string | null;
  proxima_etapa_label?: string | null;
  tempo_previsto_minutos?: number | null;
  tempo_decorrido_segundos?: number | null;
  tempo_restante_segundos?: number | null;
  atraso_segundos?: number | null;
  atrasado?: boolean;
  etapas: BanhoTosaEtapaResumo[];
}

export interface FuncionarioBanhoTosaApoios {
  fluxo_etapas: string[];
  funcionario_id: number;
  funcionarios: BanhoTosaFuncionarioResumo[];
  recursos: BanhoTosaRecursoResumo[];
  servicos: BanhoTosaServicoResumo[];
  pets: BanhoTosaPetResumo[];
}

export interface CriarAgendamentoBanhoTosaPayload {
  cliente_id: number;
  pet_id: number;
  data_hora_inicio: string;
  recurso_id?: number | null;
  origem: string;
  observacoes?: string | null;
  valor_previsto?: number | null;
  servicos: Array<{
    servico_id?: number | null;
    nome_servico?: string | null;
    quantidade: number;
    valor_unitario: number;
    tempo_previsto_minutos?: number | null;
  }>;
}

export interface MoverEtapaBanhoTosaPayload {
  tipo: string;
  responsavel_id?: number | null;
  recurso_id?: number | null;
  observacoes?: string | null;
  iniciar_timer: boolean;
  finalizar_etapa_atual?: boolean;
}

const BASE = "/app/funcionario/banho-tosa";

export async function listarAgendaBanhoTosaFuncionario(params: {
  data?: string;
  data_inicio?: string;
  data_fim?: string;
}): Promise<FuncionarioBanhoTosaAgendamento[]> {
  const { data } = await api.get<FuncionarioBanhoTosaAgendamento[]>(`${BASE}/agenda`, {
    params,
  });
  return Array.isArray(data) ? data : [];
}

export async function criarAgendamentoBanhoTosaFuncionario(
  payload: CriarAgendamentoBanhoTosaPayload,
): Promise<FuncionarioBanhoTosaAgendamento> {
  const { data } = await api.post<FuncionarioBanhoTosaAgendamento>(`${BASE}/agenda`, payload);
  return data;
}

export async function realizarCheckinBanhoTosaFuncionario(
  agendamentoId: number,
): Promise<FuncionarioBanhoTosaAtendimento> {
  const { data } = await api.post<FuncionarioBanhoTosaAtendimento>(
    `${BASE}/agenda/${agendamentoId}/check-in`,
  );
  return data;
}

export async function listarFilaBanhoTosaFuncionario(): Promise<
  FuncionarioBanhoTosaAtendimento[]
> {
  const { data } = await api.get<FuncionarioBanhoTosaAtendimento[]>(`${BASE}/fila`);
  return Array.isArray(data) ? data : [];
}

export async function moverEtapaBanhoTosaFuncionario(
  atendimentoId: number,
  payload: MoverEtapaBanhoTosaPayload,
): Promise<FuncionarioBanhoTosaAtendimento> {
  const { data } = await api.post<FuncionarioBanhoTosaAtendimento>(
    `${BASE}/fila/${atendimentoId}/mover-etapa`,
    payload,
  );
  return data;
}

export async function listarApoiosBanhoTosaFuncionario(): Promise<FuncionarioBanhoTosaApoios> {
  const { data } = await api.get<FuncionarioBanhoTosaApoios>(`${BASE}/apoios`);
  return {
    fluxo_etapas: Array.isArray(data?.fluxo_etapas) ? data.fluxo_etapas : [],
    funcionario_id: Number(data?.funcionario_id || 0),
    funcionarios: Array.isArray(data?.funcionarios) ? data.funcionarios : [],
    recursos: Array.isArray(data?.recursos) ? data.recursos : [],
    servicos: Array.isArray(data?.servicos) ? data.servicos : [],
    pets: Array.isArray(data?.pets) ? data.pets : [],
  };
}
