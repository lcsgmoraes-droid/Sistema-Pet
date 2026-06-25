import { PREFERENCES } from "./lgpdConstants";

export function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function onlyDefinedParams(params) {
  return Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== "" && value != null),
  );
}

export function getRequests(payload) {
  if (Array.isArray(payload?.requests)) return payload.requests;
  if (Array.isArray(payload?.next_items)) return payload.next_items;
  return [];
}

export function getPreferenceState(preferencias) {
  return Object.fromEntries(
    PREFERENCES.map(([key]) => [key, Boolean(preferencias?.[key]?.enabled)]),
  );
}

export function getDossieSummary(dossie) {
  if (!dossie) return [];
  return [
    ["Pets", dossie.pets?.length || 0],
    ["Vendas", dossie.vendas?.length || 0],
    ["Pedidos app/e-commerce", dossie.ecommerce_pedidos?.length || 0],
    ["Consentimentos", dossie.consentimentos?.length || 0],
    ["Solicitacoes", dossie.solicitacoes?.length || 0],
    ["Logs de acesso", dossie.logs_acesso?.length || 0],
  ];
}

export function mergeUpdatedRequest(current, updated) {
  return current.map((item) => (item.id === updated?.id ? updated : item));
}

export function exportDossieJson(dossie) {
  const clienteId = dossie?.cliente?.codigo || dossie?.cliente?.id || "cliente";
  const blob = new Blob([JSON.stringify(dossie, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `dossie-lgpd-${clienteId}.json`;
  link.click();
  URL.revokeObjectURL(url);
}
