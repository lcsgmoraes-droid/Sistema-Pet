import type { FuncionarioPdvProduto } from "../../../types";

export type ItemCarrinhoPdv = {
  produto: FuncionarioPdvProduto;
  quantidade: number;
};

const QUANTIDADE_MINIMA_PDV = 0.001;

export function mensagemErroApi(error: any, fallback: string) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  return fallback;
}

export function parseNumero(valor: string): number | null {
  let texto = String(valor ?? "")
    .trim()
    .replace(/\s/g, "");
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

export function vencimentoPadraoBr() {
  const data = new Date();
  data.setDate(data.getDate() + 30);
  const dia = String(data.getDate()).padStart(2, "0");
  const mes = String(data.getMonth() + 1).padStart(2, "0");
  return `${dia}-${mes}-${data.getFullYear()}`;
}

export function mascararDataBr(valor: string) {
  const digitos = String(valor ?? "")
    .replace(/\D/g, "")
    .slice(0, 8);
  if (digitos.length <= 2) return digitos;
  if (digitos.length <= 4) return `${digitos.slice(0, 2)}-${digitos.slice(2)}`;
  return `${digitos.slice(0, 2)}-${digitos.slice(2, 4)}-${digitos.slice(4)}`;
}

export function dataBrParaIso(valor: string) {
  const correspondencia = String(valor ?? "").match(/^(\d{2})-(\d{2})-(\d{4})$/);
  if (!correspondencia) return null;
  const [, dia, mes, ano] = correspondencia;
  const data = new Date(Number(ano), Number(mes) - 1, Number(dia));
  if (
    data.getFullYear() !== Number(ano) ||
    data.getMonth() !== Number(mes) - 1 ||
    data.getDate() !== Number(dia)
  ) {
    return null;
  }
  return `${ano}-${mes}-${dia}`;
}

export type IntervaloCrediario = "7_dias" | "15_dias" | "mensal";

export function gerarPlanoCrediario({
  valorTotal,
  numeroParcelas,
  primeiraData,
  intervalo,
}: {
  valorTotal: number;
  numeroParcelas: number;
  primeiraData: string;
  intervalo: IntervaloCrediario;
}) {
  const dataIso = dataBrParaIso(primeiraData);
  const quantidade = Math.trunc(Number(numeroParcelas || 0));
  if (!dataIso || quantidade < 1 || quantidade > 60) return [];

  const [ano, mes, dia] = dataIso.split("-").map(Number);
  const primeira = new Date(ano, mes - 1, dia, 12);
  const totalCentavos = Math.round(Number(valorTotal || 0) * 100);
  const valorBaseCentavos = Math.round(totalCentavos / quantidade);

  return Array.from({ length: quantidade }, (_, indice) => {
    let vencimento: Date;
    if (intervalo === "7_dias" || intervalo === "15_dias") {
      vencimento = new Date(primeira);
      vencimento.setDate(primeira.getDate() + (intervalo === "7_dias" ? 7 : 15) * indice);
    } else {
      const indiceMes = ano * 12 + (mes - 1) + indice;
      const anoParcela = Math.floor(indiceMes / 12);
      const mesParcela = indiceMes % 12;
      const ultimoDia = new Date(anoParcela, mesParcela + 1, 0, 12).getDate();
      vencimento = new Date(anoParcela, mesParcela, Math.min(dia, ultimoDia), 12);
    }

    const valorCentavos =
      indice === quantidade - 1
        ? totalCentavos - valorBaseCentavos * (quantidade - 1)
        : valorBaseCentavos;
    return {
      numero: indice + 1,
      totalParcelas: quantidade,
      valor: valorCentavos / 100,
      dataVencimento: `${String(vencimento.getDate()).padStart(2, "0")}-${String(
        vencimento.getMonth() + 1,
      ).padStart(2, "0")}-${vencimento.getFullYear()}`,
    };
  });
}
