export function formatNumber(value) {
  return Number(value || 0).toLocaleString("pt-BR");
}

export function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleString("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "America/Sao_Paulo",
  });
}

export function formatDateOnly(value) {
  const match = String(value || "").match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!match) return "-";
  return `${match[3]}/${match[2]}/${match[1]}`;
}

export function shortId(value) {
  const text = String(value || "");
  return text ? text.slice(0, 8) : "-";
}

export function extractError(err, fallback) {
  return err?.response?.data?.detail || err?.message || fallback;
}

export function statusBadge(status) {
  const normalized = String(status || "").toLowerCase();
  if (["active", "ativo"].includes(normalized)) {
    return "border-emerald-200 bg-emerald-50 text-emerald-700";
  }
  if (["suspended", "blocked", "bloqueado"].includes(normalized)) {
    return "border-rose-200 bg-rose-50 text-rose-700";
  }
  if (["trial"].includes(normalized)) {
    return "border-blue-200 bg-blue-50 text-blue-700";
  }
  return "border-slate-200 bg-slate-50 text-slate-700";
}

export function billingBadge(status) {
  const normalized = String(status || "").toLowerCase();
  if (["active", "paid", "ok", "em_dia"].includes(normalized)) {
    return "border-emerald-200 bg-emerald-50 text-emerald-700";
  }
  if (["past_due", "overdue", "late", "inadimplente"].includes(normalized)) {
    return "border-amber-200 bg-amber-50 text-amber-800";
  }
  return "border-slate-200 bg-slate-50 text-slate-700";
}

export const ATTENTION_LABELS = {
  critical: "Critico",
  high: "Atencao",
  normal: "Acompanhar",
  healthy: "Saudavel",
};

export function attentionBadge(level) {
  if (level === "critical") {
    return "border-rose-200 bg-rose-50 text-rose-700";
  }
  if (level === "high") {
    return "border-amber-200 bg-amber-50 text-amber-800";
  }
  if (level === "normal") {
    return "border-blue-200 bg-blue-50 text-blue-700";
  }
  return "border-emerald-200 bg-emerald-50 text-emerald-700";
}

