import { VetAgendamento } from "../../../services/vet.service";

export const MIN_CARACTERES_BUSCA_PET = 2;
export const DIAS_SEMANA = ["D", "S", "T", "Q", "Q", "S", "S"];

export type AgendaModo = "dia" | "semana" | "mes";

export type VetAgendaForm = {
  pet_id: string;
  data: string;
  hora: string;
  consultorio_id: string;
  motivo: string;
  duracao_minutos: string;
};

export type VetAgendaField = keyof VetAgendaForm;

export type VetAgendaCalendarDay = {
  key: string;
  data: string;
  dia: number;
  foraMes: boolean;
  selecionado: boolean;
  hoje: boolean;
};

export type VetAgendaGroup = {
  data: string;
  agenda: VetAgendamento[];
};

export function formatHora(value?: string | null) {
  if (!value) return "--:--";
  return new Date(value).toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatData(value?: string | null) {
  if (!value) return "Sem data";
  return new Date(value).toLocaleDateString("pt-BR", {
    weekday: "long",
    day: "2-digit",
    month: "2-digit",
  });
}

export function isoDate(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function dateFromIso(value?: string | null) {
  const [yearRaw, monthRaw, dayRaw] = String(value || "")
    .split("-")
    .map(Number);
  const year = Number.isFinite(yearRaw) ? yearRaw : NaN;
  const month = Number.isFinite(monthRaw) ? monthRaw - 1 : NaN;
  const day = Number.isFinite(dayRaw) ? dayRaw : NaN;
  const parsed = new Date(year, month, day);

  if (
    !Number.isFinite(year) ||
    !Number.isFinite(month) ||
    !Number.isFinite(day) ||
    parsed.getFullYear() !== year ||
    parsed.getMonth() !== month ||
    parsed.getDate() !== day
  ) {
    return new Date();
  }

  return parsed;
}

export function formatarDataIsoParaBr(value?: string | null) {
  const date = dateFromIso(value);
  return date.toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

export function addDays(date: Date, days: number) {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
}

export function addMonths(date: Date, months: number) {
  const next = new Date(date);
  next.setMonth(next.getMonth() + months);
  return next;
}

function startOfWeek(date: Date) {
  return addDays(date, -date.getDay());
}

function endOfMonth(date: Date) {
  return new Date(date.getFullYear(), date.getMonth() + 1, 0);
}

export function gerarCalendarioDias(
  mesReferenciaIso: string,
  selecionadaIso: string,
): VetAgendaCalendarDay[] {
  const mesReferencia = dateFromIso(mesReferenciaIso);
  const selecionada = dateFromIso(selecionadaIso);
  const hojeIso = isoDate(new Date());
  const inicioMes = new Date(
    mesReferencia.getFullYear(),
    mesReferencia.getMonth(),
    1,
  );
  const inicioGrade = addDays(inicioMes, -inicioMes.getDay());

  return Array.from({ length: 42 }, (_, index) => {
    const data = addDays(inicioGrade, index);
    const dataIso = isoDate(data);
    return {
      key: dataIso,
      data: dataIso,
      dia: data.getDate(),
      foraMes: data.getMonth() !== mesReferencia.getMonth(),
      selecionado: data.toDateString() === selecionada.toDateString(),
      hoje: dataIso === hojeIso,
    };
  });
}

export function mesAnoCalendario(value: string) {
  return dateFromIso(value).toLocaleDateString("pt-BR", {
    month: "long",
    year: "numeric",
  });
}

export function gerarHorariosBase() {
  const horarios: string[] = [];
  for (let hora = 8; hora <= 18; hora += 1) {
    for (let minuto = 0; minuto < 60; minuto += 30) {
      if (hora === 18 && minuto > 0) continue;
      horarios.push(
        `${String(hora).padStart(2, "0")}:${String(minuto).padStart(2, "0")}`,
      );
    }
  }
  return horarios;
}

export function dataDoAgendamento(item: VetAgendamento) {
  if (!item.data_hora) return "";
  return isoDate(new Date(item.data_hora));
}

export function horaDoAgendamento(item: VetAgendamento) {
  return formatHora(item.data_hora);
}

export function mensagemErroApi(error: any, fallback: string) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  return fallback;
}

export function formInicialAgendamento(
  data = isoDate(new Date()),
  hora = "08:00",
): VetAgendaForm {
  return {
    pet_id: "",
    data,
    hora,
    consultorio_id: "",
    motivo: "",
    duracao_minutos: "30",
  };
}

export function dataReferenciaModal(date: Date) {
  return isoDate(date);
}

export function periodoAgenda(modo: AgendaModo, referencia: Date) {
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
    const inicio = startOfWeek(referencia);
    const fim = addDays(inicio, 6);
    return {
      params: { data_inicio: isoDate(inicio), data_fim: isoDate(fim) },
      titulo: `${inicio.toLocaleDateString("pt-BR", {
        day: "2-digit",
        month: "short",
      })} - ${fim.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" })}`,
    };
  }

  const inicio = new Date(referencia.getFullYear(), referencia.getMonth(), 1);
  const fim = endOfMonth(referencia);
  return {
    params: { data_inicio: isoDate(inicio), data_fim: isoDate(fim) },
    titulo: referencia.toLocaleDateString("pt-BR", {
      month: "long",
      year: "numeric",
    }),
  };
}
