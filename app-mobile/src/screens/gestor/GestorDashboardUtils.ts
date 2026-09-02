export type GestorPeriodKey =
  | "hoje"
  | "ontem"
  | "sete_dias"
  | "este_mes"
  | "mes_anterior"
  | "personalizado";

export interface GestorPeriod {
  key: GestorPeriodKey;
  label: string;
  start: string;
  end: string;
}

export const GESTOR_QUICK_PERIODS: Array<{
  key: Exclude<GestorPeriodKey, "personalizado">;
  label: string;
}> = [
  { key: "hoje", label: "Hoje" },
  { key: "ontem", label: "Ontem" },
  { key: "sete_dias", label: "7 dias" },
  { key: "este_mes", label: "Este mes" },
  { key: "mes_anterior", label: "Mes anterior" },
];

export function toLocalIsoDate(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function resolveGestorPeriod(
  key: Exclude<GestorPeriodKey, "personalizado">,
  now = new Date(),
): GestorPeriod {
  const end = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const start = new Date(end);

  if (key === "ontem") {
    start.setDate(start.getDate() - 1);
    end.setDate(end.getDate() - 1);
  } else if (key === "sete_dias") {
    start.setDate(start.getDate() - 6);
  } else if (key === "este_mes") {
    start.setDate(1);
  } else if (key === "mes_anterior") {
    start.setMonth(start.getMonth() - 1, 1);
    end.setDate(0);
  }

  const label =
    GESTOR_QUICK_PERIODS.find((item) => item.key === key)?.label ?? key;
  return { key, label, start: toLocalIsoDate(start), end: toLocalIsoDate(end) };
}

export function formatIsoDateBR(value: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return value;
  return `${match[3]}/${match[2]}/${match[1]}`;
}

export function parseBRDate(value: string): string | null {
  const digits = value.replace(/\D/g, "");
  if (digits.length !== 8) return null;
  const day = Number(digits.slice(0, 2));
  const month = Number(digits.slice(2, 4));
  const year = Number(digits.slice(4, 8));
  const parsed = new Date(year, month - 1, day);
  if (
    parsed.getFullYear() !== year ||
    parsed.getMonth() !== month - 1 ||
    parsed.getDate() !== day
  ) {
    return null;
  }
  return toLocalIsoDate(parsed);
}

export function maskBRDate(value: string): string {
  const digits = value.replace(/\D/g, "").slice(0, 8);
  if (digits.length <= 2) return digits;
  if (digits.length <= 4) return `${digits.slice(0, 2)}/${digits.slice(2)}`;
  return `${digits.slice(0, 2)}/${digits.slice(2, 4)}/${digits.slice(4)}`;
}

export function formatQuantity(value: number): string {
  return new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 3 }).format(
    Number(value || 0),
  );
}
