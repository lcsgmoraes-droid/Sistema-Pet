import type { FuncionarioProdutoEstoque } from "../../../types";

export type ContagemItemLocal = {
  id: string;
  produto: FuncionarioProdutoEstoque;
  quantidade: number;
  observacao?: string | null;
};

export function mensagemErroApi(error: any, fallback: string) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  const message = error?.response?.data?.message;
  if (typeof message === "string" && message.trim()) return message;
  return fallback;
}

export function parseNumero(valor: string): number | null {
  const normalizado = valor.replace(/\./g, "").replace(",", ".").trim();
  if (!normalizado) return null;
  const numero = Number(normalizado);
  return Number.isFinite(numero) ? numero : null;
}

export function formatarQuantidade(valor: number | null | undefined) {
  return new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 3,
  }).format(Number(valor ?? 0));
}
