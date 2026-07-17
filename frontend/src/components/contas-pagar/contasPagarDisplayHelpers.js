import { formatarDataISO } from "./contasPagarFilterHelpers.js";

export function formatarDataContasPagar(data) {
  if (!data) return "-";
  const partes = data.split("T")[0].split("-");
  const dataLocal = new Date(parseInt(partes[0]), parseInt(partes[1]) - 1, parseInt(partes[2]));
  return dataLocal.toLocaleDateString("pt-BR");
}

export function ehVencimentoHojeContasPagar(dataVencimento, dataReferencia = new Date()) {
  if (!dataVencimento) return false;

  const vencimentoISO = String(dataVencimento).split("T")[0];
  return vencimentoISO === formatarDataISO(dataReferencia);
}

export function getStatusVisualContasPagar(conta, dataReferencia = new Date()) {
  const status = String(conta?.status || "pendente").toLowerCase();

  if (status === "cancelado") return "cancelado";
  if (status === "pago") return "pago";

  const vencimentoISO = conta?.data_vencimento ? String(conta.data_vencimento).split("T")[0] : "";
  const hojeISO = formatarDataISO(dataReferencia);

  if (vencimentoISO && vencimentoISO < hojeISO) return "vencida";
  if (vencimentoISO === hojeISO) return "vence_hoje";
  if (status === "parcial") return "parcial";
  return "pendente";
}

export function getOrigemLabelContasPagar(conta) {
  const origem = conta.origem_lancamento || "manual";

  if (origem === "caixa_pdv") {
    return conta.caixa_referencia ? `Caixa/PDV (${conta.caixa_referencia})` : "Caixa/PDV";
  }

  if (origem === "nota_entrada") {
    return "Nota entrada";
  }

  return "Manual";
}

export function getDescricaoPrincipalContasPagar(conta) {
  const descricao = String(conta.descricao || "-").trim();
  const nfMatch = descricao.match(/\bNF-e?\s+\d+/i);
  if (nfMatch) return nfMatch[0].replace(/\s+/g, " ");
  return descricao;
}

export function getContaTooltipContasPagar(conta) {
  const linhas = [
    `Descricao: ${conta.descricao || "-"}`,
    conta.documento ? `Documento/NF: ${conta.documento}` : null,
    `Origem: ${getOrigemLabelContasPagar(conta)}`,
    conta.tipo_despesa_nome ? `Tipo de despesa: ${conta.tipo_despesa_nome}` : null,
    conta.eh_parcelado ? `Parcela: ${conta.numero_parcela}/${conta.total_parcelas}` : null,
    conta.e_custo_fixo === true ? "Tipo de custo: Fixo" : null,
    conta.e_custo_fixo === false ? "Tipo de custo: Variavel" : null,
  ].filter(Boolean);

  return linhas.join("\n");
}

export function ordenarTiposDespesaContasPagar(tiposDespesa, safeArray) {
  return [...safeArray(tiposDespesa)].sort((a, b) =>
    String(a.nome || "").localeCompare(String(b.nome || ""), "pt-BR", { sensitivity: "base" }),
  );
}

export function encontrarFornecedorFiltroContasPagar(fornecedores, fornecedorId, safeArray) {
  return safeArray(fornecedores).find(
    (fornecedor) => String(fornecedor.id) === String(fornecedorId),
  );
}
