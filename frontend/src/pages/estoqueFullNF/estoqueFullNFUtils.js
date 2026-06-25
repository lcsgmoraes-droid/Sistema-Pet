let linhaSeq = 1;

export function criarLinha() {
  return { id: `linha-${linhaSeq++}`, sku: "", quantidade: "" };
}

export function toNumber(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

export const CANAIS_FULL = [
  {
    value: "amazon",
    label: "Amazon",
  },
  {
    value: "mercado_livre",
    label: "Mercado Livre",
  },
  {
    value: "shopee",
    label: "Shopee",
  },
  {
    value: "full",
    label: "FULL (geral)",
  },
];

export function contarBaixas(resultado) {
  if (!resultado) return 0;
  if (resultado.baixas_estoque !== undefined && resultado.baixas_estoque !== null) {
    return Number(resultado.baixas_estoque) || 0;
  }
  return resultado.estoque_ja_baixado ? 0 : Number(resultado.total_itens || 0);
}

export function contarLancamentosFinanceiros(resultado) {
  if (!resultado) return 0;
  if (
    resultado.lancamentos_financeiros !== undefined &&
    resultado.lancamentos_financeiros !== null
  ) {
    return Number(resultado.lancamentos_financeiros) || 0;
  }
  return resultado?.tarifa_envio?.conta_pagar_id ? 1 : 0;
}

export function formatarDataHora(valor) {
  if (!valor) return "-";
  const data = new Date(valor);
  if (Number.isNaN(data.getTime())) return "-";
  return data.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function normalizarSku(valor) {
  return String(valor || "")
    .trim()
    .toLowerCase();
}

export function formatarQuantidade(valor) {
  const numero = Number(valor || 0);
  if (!Number.isFinite(numero)) return "0";
  return numero.toLocaleString("pt-BR", { maximumFractionDigits: 3 });
}

export function extrairDetalheErro(error) {
  return error?.response?.data?.detail || error?.message || "Erro ao processar baixa por NF";
}

export function ehErroEstoqueFull(detalhe) {
  return Boolean(
    detalhe &&
    typeof detalhe === "object" &&
    detalhe.code === "estoque_insuficiente_full_nf" &&
    Array.isArray(detalhe.itens),
  );
}
