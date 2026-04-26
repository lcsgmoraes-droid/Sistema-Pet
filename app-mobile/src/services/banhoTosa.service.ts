import api from "./api";
import { BanhoTosaStatusResponse } from "../types";

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
