export type Coordenada = {
  latitude: number;
  longitude: number;
};

export type GpsPosicao = {
  lat: number;
  lon: number;
  atualizada_em?: string | null;
  fonte?: string | null;
};

export type RotaRastreio = {
  numero: string;
  status: string;
  token_rastreio?: string;
  entregador_nome: string;
  total_paradas: number;
  entregues: number;
  posicao_cliente?: number;
  paradas_antes: number;
  status_parada: string;
  endereco_entrega?: string;
  data_entrega?: string;
  ultima_posicao_gps?: GpsPosicao;
};

export type RastreioData = {
  status_pedido: string;
  tem_entrega: boolean;
  mensagem: string;
  tipo_retirada?: string;
  palavra_chave_retirada?: string;
  rota?: RotaRastreio;
};

export const STATUS_ROTA: Record<string, { label: string; cor: string }> = {
  pendente: { label: "Preparando", cor: "#F59E0B" },
  em_andamento: { label: "Em rota", cor: "#3B82F6" },
  em_rota: { label: "A caminho", cor: "#3B82F6" },
  concluida: { label: "Entregue", cor: "#10B981" },
  entregue: { label: "Entregue", cor: "#10B981" },
};

export const STATUS_PARADA: Record<
  string,
  { emoji: string; label: string; cor: string; corFundo: string }
> = {
  pendente: {
    emoji: "⏳",
    label: "Aguardando",
    cor: "#92400E",
    corFundo: "#FEF3C7",
  },
  entregue: {
    emoji: "✅",
    label: "Entregue",
    cor: "#065F46",
    corFundo: "#D1FAE5",
  },
  em_rota: {
    emoji: "🛵",
    label: "A caminho",
    cor: "#1E40AF",
    corFundo: "#DBEAFE",
  },
};

export function easeInOut(progress: number) {
  if (progress < 0.5) {
    return 2 * progress * progress;
  }
  return 1 - Math.pow(-2 * progress + 2, 2) / 2;
}

export function samePoint(a: Coordenada | null, b: Coordenada) {
  if (!a) return false;
  return (
    Math.abs(a.latitude - b.latitude) < 0.000001 &&
    Math.abs(a.longitude - b.longitude) < 0.000001
  );
}

export function computeBearing(from: Coordenada, to: Coordenada) {
  const toRad = (value: number) => (value * Math.PI) / 180;
  const toDeg = (value: number) => (value * 180) / Math.PI;
  const lat1 = toRad(from.latitude);
  const lat2 = toRad(to.latitude);
  const diffLong = toRad(to.longitude - from.longitude);
  const y = Math.sin(diffLong) * Math.cos(lat2);
  const x =
    Math.cos(lat1) * Math.sin(lat2) -
    Math.sin(lat1) * Math.cos(lat2) * Math.cos(diffLong);

  return (toDeg(Math.atan2(y, x)) + 360) % 360;
}

export function appendTrailPoint(points: Coordenada[], next: Coordenada) {
  const last = points[points.length - 1];
  if (last && samePoint(last, next)) {
    return points;
  }
  return [...points, next].slice(-40);
}

export function buildGoogleMapsUrl(
  gps?: GpsPosicao | null,
  endereco?: string | null,
) {
  if (gps) {
    return `https://www.google.com/maps?q=${gps.lat},${gps.lon}`;
  }
  if (endereco) {
    return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(endereco)}`;
  }
  return "";
}

export function getTrackingIntervalMs(paradasAntes?: number | null) {
  return (paradasAntes ?? 99) <= 1 ? 3_000 : 6_000;
}

export function formatGpsAtualizadoEm(value?: string | null) {
  if (!value) return null;
  return new Date(value).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatHoraAtualizacao(value: Date) {
  return value.toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatDataEntrega(value: string) {
  return new Date(value).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
