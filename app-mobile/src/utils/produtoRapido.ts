/** Virgula fixa: 5 -> 0,05; 5555 -> 55,55, preservando milhares brasileiros. */
export function valorMonetarioProduto(texto: string): number {
  return Number(texto.replace(/\D/g, "") || "0") / 100;
}

export function formatarCampoMonetarioProduto(texto: string): string {
  if (!texto.replace(/\D/g, "")) return "";
  return new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(valorMonetarioProduto(texto));
}

export function erroCadastroProduto(error: unknown, fallback: string): string {
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  return typeof detail === "string" ? detail : fallback;
}
