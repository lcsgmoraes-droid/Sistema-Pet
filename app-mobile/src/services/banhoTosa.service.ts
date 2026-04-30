import api from "./api";
import { BanhoTosaCalendarioResponse, BanhoTosaStatusResponse } from "../types";

export async function listarStatusBanhoTosa(): Promise<BanhoTosaStatusResponse> {
  const { data } = await api.get<BanhoTosaStatusResponse>("/app/banho-tosa/status");
  return {
    total: Number(data?.total || 0),
    itens: Array.isArray(data?.itens) ? data.itens : [],
  };
}

export async function avaliarBanhoTosaAtendimento(
  atendimentoId: number,
  notaNps: number,
): Promise<void> {
  await api.post(`/app/banho-tosa/atendimentos/${atendimentoId}/avaliacao`, {
    nota_nps: notaNps,
  });
}

export async function listarCalendarioBanhoTosa(params?: {
  data_inicio?: string;
  dias?: number;
  servico_id?: number | null;
}): Promise<BanhoTosaCalendarioResponse> {
  const { data } = await api.get<BanhoTosaCalendarioResponse>("/app/banho-tosa/calendario", {
    params: {
      data_inicio: params?.data_inicio,
      dias: params?.dias ?? 7,
      servico_id: params?.servico_id || undefined,
    },
  });
  return {
    visivel: !!data?.visivel,
    whatsapp: data?.whatsapp ?? null,
    servicos: Array.isArray(data?.servicos) ? data.servicos : [],
    dias: Array.isArray(data?.dias) ? data.dias : [],
  };
}
