import api from "./api";

export interface GestorVendasResumo {
  faturamento_bruto: number;
  faturamento_liquido: number;
  recebido: number;
  descontos: number;
  quantidade_vendas: number;
  unidades_vendidas: number;
  produtos_distintos: number;
  ticket_medio: number;
}

export interface GestorContaResumo {
  total_aberto: number;
  quantidade_abertas: number;
  vencido: number;
  quantidade_vencidas: number;
  vence_hoje: number;
  quantidade_vence_hoje: number;
  no_periodo: number;
  quantidade_no_periodo: number;
}

export interface GestorFluxoDiaResumo {
  data: string;
  disponivel: boolean;
  saldo_inicial: number;
  saldo_do_dia: number;
  saldo_previsto_do_dia: number;
  entradas_realizadas: number;
  saidas_realizadas: number;
  saldo_realizado: number;
  entradas_previstas: number;
  saidas_previstas: number;
  saldo_projetado: number;
}

export interface GestorDREResumo {
  disponivel: boolean;
  periodo: string;
  criterio: "periodo_selecionado" | "competencia_do_mes";
  receita_bruta: number;
  descontos: number;
  impostos: number;
  deducoes_total: number;
  receita_liquida: number;
  cmv: number;
  despesas_variaveis: number;
  despesas_operacionais: number;
  despesas_fixas_operacionais: number;
  lucro_bruto: number;
  resultado_operacional: number;
  lucro_liquido: number;
  margem_bruta: number;
  margem_liquida: number;
}

export interface GestorResumo {
  data_inicio: string;
  data_fim: string;
  atualizado_em: string;
  vendas: GestorVendasResumo;
  fluxo_hoje: GestorFluxoDiaResumo;
  contas_pagar: GestorContaResumo;
  contas_receber: GestorContaResumo;
  dre: GestorDREResumo;
  avisos: string[];
}

export async function obterResumoGestor(
  dataInicio: string,
  dataFim: string,
): Promise<GestorResumo> {
  const { data } = await api.get<GestorResumo>("/app/gestor/resumo", {
    params: { data_inicio: dataInicio, data_fim: dataFim },
    timeout: 30000,
  });
  return data;
}
