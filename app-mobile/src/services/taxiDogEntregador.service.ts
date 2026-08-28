import api from "./api";

export interface TaxiDogEntregadorItem {
  id: number;
  cliente_id: number;
  cliente_nome?: string | null;
  pet_id: number;
  pet_nome?: string | null;
  pet_foto_url?: string | null;
  agendamento_id?: number | null;
  agendamento_inicio?: string | null;
  tipo: "ida" | "volta" | "ida_volta" | string;
  status: string;
  status_label: string;
  proximo_status?: string | null;
  motorista_id?: number | null;
  endereco_origem?: string | null;
  endereco_destino?: string | null;
  janela_inicio?: string | null;
  janela_fim?: string | null;
  km_estimado?: number | null;
}

export async function listarTaxiDogDoEntregador(
  data?: string,
): Promise<TaxiDogEntregadorItem[]> {
  const response = await api.get<TaxiDogEntregadorItem[]>("/app/entregador/taxi-dog", {
    params: { data },
  });
  return Array.isArray(response.data) ? response.data : [];
}

export async function avancarTaxiDogDoEntregador(
  taxiId: number,
  status: string,
): Promise<TaxiDogEntregadorItem> {
  const response = await api.patch<TaxiDogEntregadorItem>(
    `/app/entregador/taxi-dog/${taxiId}/status`,
    { status },
  );
  return response.data;
}
