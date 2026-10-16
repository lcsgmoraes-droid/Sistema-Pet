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

export function formatarDataProduto(texto: string): string {
  const digitos = texto.replace(/\D/g, "").slice(0, 8);
  if (digitos.length <= 2) return digitos;
  if (digitos.length <= 4) return `${digitos.slice(0, 2)}/${digitos.slice(2)}`;
  return `${digitos.slice(0, 2)}/${digitos.slice(2, 4)}/${digitos.slice(4)}`;
}

export function dataIsoProduto(texto: string): string | undefined {
  if (!texto.trim()) return undefined;
  const partes = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(texto);
  if (!partes) return undefined;
  const [, dia, mes, ano] = partes;
  const data = new Date(Date.UTC(Number(ano), Number(mes) - 1, Number(dia)));
  if (data.getUTCFullYear() !== Number(ano) || data.getUTCMonth() + 1 !== Number(mes) || data.getUTCDate() !== Number(dia)) return undefined;
  return `${ano}-${mes}-${dia}`;
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
