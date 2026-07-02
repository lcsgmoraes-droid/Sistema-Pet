import * as Location from "expo-location";
import { Alert, Linking } from "react-native";

import { limparEnderecoParaMaps } from "@/utils/mapsAddress";

export interface Parada {
  id: number;
  venda_id: number;
  ordem: number;
  endereco: string;
  status: string;
  cliente_nome?: string;
  cliente_telefone?: string;
  cliente_celular?: string;
  observacoes?: string;
  data_entrega?: string;
}

export interface Rota {
  id: number;
  numero: string;
  status: string;
  paradas: Parada[];
}

export interface VendaDetalhes {
  id: number;
  cliente?: {
    nome?: string;
    telefone?: string;
    celular?: string;
  };
  data_venda?: string;
  forma_pagamento?: string;
  status_pagamento?: string;
  endereco_entrega?: string;
  observacoes_entrega?: string;
  total?: number;
  valor_total?: number;
  itens?: Array<{
    produto_nome?: string;
    servico_descricao?: string;
    quantidade?: number;
    subtotal?: number;
    preco_unitario?: number;
  }>;
}

export type FormaRecebimento = "pix" | "cartao_debito" | "cartao_credito";

export function reordenarParadasPorPosicao(
  paradas: Parada[],
  paradaId: number,
  novaPosicao: number,
) {
  const ordenadas = [...paradas].sort((a, b) => a.ordem - b.ordem);
  const indiceAtual = ordenadas.findIndex((parada) => parada.id === paradaId);

  if (indiceAtual < 0) {
    return null;
  }

  const posicaoClamped = Math.max(1, Math.min(novaPosicao, ordenadas.length));
  const [paradaMovida] = ordenadas.splice(indiceAtual, 1);
  ordenadas.splice(posicaoClamped - 1, 0, paradaMovida);

  return ordenadas;
}

export function rotaPermiteReordenacao(status?: string | null) {
  return !!status && !["concluida", "cancelada"].includes(status);
}

export function extrairPosicaoOrdem(texto: string) {
  const match = texto.match(/\d+/);
  return match ? Number.parseInt(match[0], 10) : Number.NaN;
}

export function obterMensagemErro(error: unknown, fallback: string) {
  if (
    error &&
    typeof error === "object" &&
    "response" in error &&
    error.response &&
    typeof error.response === "object" &&
    "data" in error.response
  ) {
    const data = error.response.data;
    if (data && typeof data === "object" && "detail" in data) {
      const detail = data.detail;
      if (typeof detail === "string" && detail.trim()) {
        return detail;
      }
    }
  }
  return fallback;
}

export function abrirMapa(endereco: string) {
  const enderecoMaps = limparEnderecoParaMaps(endereco) || endereco;
  const url = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(enderecoMaps)}`;
  Linking.openURL(url).catch(() =>
    Alert.alert("Erro", "NÃ£o foi possÃ­vel abrir o mapa."),
  );
}

export function ligar(telefone?: string | null) {
  if (!telefone) return;
  const digits = telefone.replaceAll(/\D/g, "");
  Linking.openURL(`tel:${digits}`).catch(() =>
    Alert.alert("Erro", "NÃ£o foi possÃ­vel ligar."),
  );
}

export async function obterLocalizacaoOpcional(): Promise<{
  latitude?: number;
  longitude?: number;
}> {
  try {
    const { status } = await Location.requestForegroundPermissionsAsync();
    if (status !== "granted") {
      return {};
    }

    const posicao = await Promise.race([
      Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.Balanced,
      }),
      new Promise<null>((resolve) => {
        setTimeout(() => resolve(null), 3500);
      }),
    ]);

    if (!posicao) {
      return {};
    }

    return {
      latitude: posicao.coords.latitude,
      longitude: posicao.coords.longitude,
    };
  } catch {
    return {};
  }
}

export const STATUS_BADGE: Record<
  string,
  { label: string; color: string; bg: string }
> = {
  pendente: { label: "Pendente", color: "#92400e", bg: "#fef3c7" },
  entregue: { label: "Entregue ?", color: "#065f46", bg: "#d1fae5" },
  nao_entregue: { label: "NÃ£o entregue ?", color: "#7f1d1d", bg: "#fee2e2" },
};
