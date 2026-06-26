export const formatarQuantidade = (valor) =>
  new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 3,
  }).format(Number(valor || 0));

export const formatarData = (valor) => {
  if (!valor) return "-";
  return new Date(valor).toLocaleDateString("pt-BR");
};

export const formatarDataHora = (valor) => {
  if (!valor) return "-";
  return new Date(valor).toLocaleString("pt-BR");
};

export const formatarDiaCurto = (valor) =>
  new Date(valor).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
  });

export function hojeIso() {
  return new Date().toISOString().split("T")[0];
}

export function dataInicioPorDias(dias) {
  const data = new Date();
  data.setHours(0, 0, 0, 0);
  data.setDate(data.getDate() - Math.max(dias - 1, 0));
  return data.toISOString().split("T")[0];
}

export function extrairListaProdutos(payload) {
  if (!payload) return [];
  if (Array.isArray(payload.items)) return payload.items;
  if (Array.isArray(payload.itens)) return payload.itens;
  if (Array.isArray(payload.produtos)) return payload.produtos;
  if (Array.isArray(payload.data)) return payload.data;
  if (Array.isArray(payload)) return payload;
  return [];
}
