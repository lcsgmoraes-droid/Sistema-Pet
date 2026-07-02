import type { FuncionarioPdvFormaPagamento, FuncionarioPdvProduto } from "../../../types";

export type ItemCarrinhoPdv = {
  produto: FuncionarioPdvProduto;
  quantidade: number;
};

const QUANTIDADE_MINIMA_PDV = 0.001;

export const FORMAS_PAGAMENTO: {
  key: FuncionarioPdvFormaPagamento;
  label: string;
  icon: string;
}[] = [
  { key: "dinheiro", label: "Dinheiro", icon: "cash-outline" },
  { key: "pix", label: "Pix", icon: "qr-code-outline" },
  { key: "credito", label: "Credito", icon: "card-outline" },
  { key: "debito", label: "Debito", icon: "card-outline" },
];

export function mensagemErroApi(error: any, fallback: string) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  return fallback;
}

export function parseNumero(valor: string): number | null {
  let texto = String(valor ?? "").trim().replace(/\s/g, "");
  if (!texto) return null;
  if (texto.includes(",") && texto.includes(".")) {
    texto =
      texto.lastIndexOf(",") > texto.lastIndexOf(".")
        ? texto.replace(/\./g, "").replace(",", ".")
        : texto.replace(/,/g, "");
  } else if (texto.includes(",")) {
    texto = texto.replace(",", ".");
  }
  const numero = Number(texto);
  return Number.isFinite(numero) ? numero : null;
}

export function arredondarQuantidadePdv(valor: number) {
  return Math.round(Math.max(QUANTIDADE_MINIMA_PDV, valor) * 1000) / 1000;
}

export function formatarQuantidade(valor: number | null | undefined) {
  return new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 3,
  }).format(Number(valor ?? 0));
}

export function formatarQuantidadeCampo(valor: number | null | undefined) {
  return formatarQuantidade(valor).replace(/\./g, "");
}

export function formatarValorCampo(valor: number | null | undefined) {
  return new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
    useGrouping: false,
  }).format(Number(valor ?? 0));
}
