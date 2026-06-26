export function formatarDataValidade(data) {
  if (!data) return "sem data";
  return new Date(data).toLocaleDateString("pt-BR");
}

export function formatarMoeda(valor) {
  return Number(valor || 0).toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  });
}

export function formatarDataHora(data) {
  if (!data) return "agora";
  return new Date(data).toLocaleString("pt-BR");
}

export function formatarDataCurta(data) {
  if (!data) return "";
  return new Date(data).toLocaleDateString("pt-BR");
}
