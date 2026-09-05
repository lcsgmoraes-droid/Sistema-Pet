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
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object" && "mensagem" in detail && typeof detail.mensagem === "string") return detail.mensagem;
  return fallback;
}

/** Identifica uma tentativa de cadastro; nao e um token de acesso. */
export function gerarChaveCadastroProduto(): string {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (caractere) => {
    const aleatorio = Math.floor(Math.random() * 16);
    return (caractere === "x" ? aleatorio : (aleatorio & 3) | 8).toString(16);
  });
}
