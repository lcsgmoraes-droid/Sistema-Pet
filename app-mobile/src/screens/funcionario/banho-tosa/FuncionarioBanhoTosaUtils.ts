import {
  FuncionarioBanhoTosaAgendamento,
  FuncionarioBanhoTosaAtendimento,
} from "../../../services/funcionarioBanhoTosa.service";

export type BanhoTosaAgendaModo = "dia" | "semana" | "mes";

export type AgendaGrupo = {
  data: string;
  itens: FuncionarioBanhoTosaAgendamento[];
};

export const ETAPAS_COM_TIMER = new Set([
  "banho",
  "secagem",
  "tosa",
  "higiene",
  "preparo",
]);

const ETAPAS_LABELS: Record<string, string> = {
  chegou: "Chegou",
  banho: "Banho",
  secagem: "Secagem",
  tosa: "Tosa",
  higiene: "Higiene",
  preparo: "Preparo",
  pronto: "Pronto",
  entregue: "Entregue",
};

export function isoDate(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function dateFromIso(value: string): Date {
  const [year, month, day] = String(value || "").split("-").map(Number);
  const parsed = new Date(year, month - 1, day);
  return Number.isNaN(parsed.getTime()) ? new Date() : parsed;
}

export function addDays(date: Date, amount: number): Date {
  const next = new Date(date);
  next.setDate(next.getDate() + amount);
  return next;
}

export function addMonths(date: Date, amount: number): Date {
  const next = new Date(date);
  next.setMonth(next.getMonth() + amount);
  return next;
}

export function periodoAgenda(modo: BanhoTosaAgendaModo, referencia: Date) {
  if (modo === "dia") {
    return {
      params: { data: isoDate(referencia) },
      titulo: referencia.toLocaleDateString("pt-BR", {
        weekday: "long",
        day: "2-digit",
        month: "long",
      }),
    };
  }
  if (modo === "semana") {
    const inicio = addDays(referencia, -referencia.getDay());
    const fim = addDays(inicio, 6);
    return {
      params: { data_inicio: isoDate(inicio), data_fim: isoDate(fim) },
      titulo: `${formatarDiaMes(inicio)} a ${formatarDiaMes(fim)}`,
    };
  }
  const inicio = new Date(referencia.getFullYear(), referencia.getMonth(), 1);
  const fim = new Date(referencia.getFullYear(), referencia.getMonth() + 1, 0);
  return {
    params: { data_inicio: isoDate(inicio), data_fim: isoDate(fim) },
    titulo: referencia.toLocaleDateString("pt-BR", { month: "long", year: "numeric" }),
  };
}

function formatarDiaMes(date: Date): string {
  return date.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });
}

export function agruparAgenda(
  itens: FuncionarioBanhoTosaAgendamento[],
): AgendaGrupo[] {
  const grupos = new Map<string, FuncionarioBanhoTosaAgendamento[]>();
  itens.forEach((item) => {
    const data = item.data_hora_inicio ? isoDate(new Date(item.data_hora_inicio)) : "sem-data";
    grupos.set(data, [...(grupos.get(data) || []), item]);
  });
  return Array.from(grupos.entries()).map(([data, agenda]) => ({ data, itens: agenda }));
}

export function formatarData(value?: string | null): string {
  if (!value) return "Sem data";
  return new Date(value).toLocaleDateString("pt-BR", {
    weekday: "long",
    day: "2-digit",
    month: "2-digit",
  });
}

export function formatarHora(value?: string | null): string {
  if (!value) return "--:--";
  return new Date(value).toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatarTempo(segundos?: number | null): string {
  const total = Math.max(0, Number(segundos || 0));
  const horas = Math.floor(total / 3600);
  const minutos = Math.floor((total % 3600) / 60);
  return horas ? `${horas}h ${minutos}min` : `${minutos} min`;
}

export function labelEtapa(etapa?: string | null): string {
  const key = String(etapa || "").toLowerCase();
  return ETAPAS_LABELS[key] || key.replaceAll("_", " ") || "Etapa";
}

export function itensDaEtapa(
  itens: FuncionarioBanhoTosaAtendimento[],
  etapa: string,
): FuncionarioBanhoTosaAtendimento[] {
  return itens.filter((item) => item.etapa_atual_codigo === etapa);
}

export function mensagemErroApi(error: any, fallback: string): string {
  const detail = error?.response?.data?.detail;
  return typeof detail === "string" && detail.trim() ? detail : fallback;
}

export function statusAgendamentoLabel(status?: string | null): string {
  return (
    {
      agendado: "Agendado",
      confirmado: "Confirmado",
      em_atendimento: "Na fila",
      pronto: "Pronto",
      entregue: "Entregue",
      cancelado: "Cancelado",
      no_show: "Nao compareceu",
    }[String(status || "")] || String(status || "Agendado")
  );
}
