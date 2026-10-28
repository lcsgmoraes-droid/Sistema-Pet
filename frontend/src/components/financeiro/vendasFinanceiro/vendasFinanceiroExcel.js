import writeExcelFile from "write-excel-file/browser";
import { campoRentabilidadePendente, PENDENCIA_IFOOD_LABEL } from "./rentabilidadePendente.js";
import { formatMoneyBRL } from "../../../utils/formatters.js";

function valorRentabilidade(venda, campo) {
  return campoRentabilidadePendente(venda, campo)
    ? PENDENCIA_IFOOD_LABEL
    : Number(venda[campo] || 0);
}

function valorObservado(cobranca) {
  return cobranca.signed_amount == null
    ? "Não informado"
    : `${formatMoneyBRL(Number(cobranca.signed_amount))} (valor observado)`;
}

export function descreverCobrancasIfoodExcel(venda) {
  const financeiro = venda.ifood_financial;
  if (!financeiro) return "";
  const prefixo = financeiro.simulated ? "SIMULAÇÃO DEV — " : "";
  return (
    prefixo +
    (financeiro.charges || [])
      .map(
        (cobranca) =>
          `${cobranca.label || cobranca.code}: ${cobranca.amount == null ? valorObservado(cobranca) : formatMoneyBRL(Number(cobranca.amount))}${cobranca.status === "unclassified" || cobranca.amount == null ? " (não classificado)" : ""}`,
      )
      .join("; ")
  );
}

export function montarLinhasCobrancasIfoodExcel(vendas = []) {
  const linhas = [];
  for (const venda of vendas) {
    const financeiro = venda.ifood_financial;
    if (!financeiro) continue;
    const origem = financeiro.simulated ? "Simulação DEV" : "Financial iFood";
    const referencia = venda.numero_venda || venda.id;
    for (const cobranca of financeiro.charges || []) {
      linhas.push([
        referencia,
        cobranca.label || cobranca.code,
        cobranca.amount == null ? valorObservado(cobranca) : Number(cobranca.amount),
        cobranca.status === "unclassified" || cobranca.amount == null
          ? "A classificar"
          : financeiro.simulated
            ? "Simulada"
            : "Recebida",
        origem,
        cobranca.revision ?? "",
      ]);
    }
    for (const pendencia of financeiro.pending_components || []) {
      linhas.push([
        referencia,
        pendencia.label || pendencia.code,
        ["ORDER_COMMISSION", "PAYMENT_TRANSACTION_FEE"].includes(pendencia.code)
          ? "Aguardando Financial"
          : "Conferência pendente",
        pendencia.reason || "Pendente",
        origem,
        "",
      ]);
    }
  }
  return linhas.length
    ? [
        ["Venda", "Cobrança", "Valor (despesa + / crédito -)", "Situação", "Fonte", "Revisão"],
        ...linhas,
      ]
    : [];
}

export const COLUNAS_RELATORIO_VENDAS = [
  { key: "data_venda", label: "Data", value: (v) => v.data_venda || "" },
  { key: "numero_venda", label: "Codigo", value: (v) => v.numero_venda || "" },
  { key: "cliente_nome", label: "Cliente", value: (v) => v.cliente_nome || "" },
  { key: "status", label: "Status", value: (v) => v.status || "" },
  { key: "venda_bruta", label: "Venda Bruta", value: (v) => Number(v.venda_bruta || 0) },
  { key: "taxa_loja", label: "Taxa Loja", value: (v) => Number(v.taxa_loja || 0) },
  { key: "desconto", label: "Desconto", value: (v) => Number(v.desconto || 0) },
  { key: "taxa_entrega", label: "Taxa Entrega", value: (v) => Number(v.taxa_entrega || 0) },
  { key: "taxa_operacional", label: "Taxa Operac.", value: (v) => Number(v.taxa_operacional || 0) },
  { key: "taxa_cartao", label: "Taxa Pagto", value: (v) => valorRentabilidade(v, "taxa_cartao") },
  {
    key: "taxa_ifood",
    label: "Taxas iFood",
    value: (v) => (v.ifood_financial ? valorRentabilidade(v, "taxa_ifood") : ""),
  },
  {
    key: "cobrancas_ifood",
    label: "Cobranças iFood discriminadas",
    value: descreverCobrancasIfoodExcel,
  },
  {
    key: "pendencias_ifood",
    label: "Pendências iFood",
    value: (v) =>
      (v.ifood_financial?.pending_components || [])
        .map((p) => `${p.label || p.code}: ${p.reason || "Aguardando Financial"}`)
        .join("; "),
  },
  { key: "comissao", label: "Comissao", value: (v) => Number(v.comissao || 0) },
  { key: "imposto", label: "Imposto", value: (v) => Number(v.imposto || 0) },
  { key: "custo_campanha", label: "Custo Campanha", value: (v) => Number(v.custo_campanha || 0) },
  {
    key: "venda_liquida",
    label: "Venda Liquida",
    value: (v) => valorRentabilidade(v, "venda_liquida"),
  },
  { key: "valor_recebido", label: "Valor Recebido", value: (v) => Number(v.valor_recebido || 0) },
  { key: "custo_produtos", label: "Custo Produtos", value: (v) => Number(v.custo_produtos || 0) },
  { key: "lucro", label: "Lucro", value: (v) => valorRentabilidade(v, "lucro") },
  {
    key: "margem_sobre_venda",
    label: "Margem sobre Venda %",
    value: (v) => valorRentabilidade(v, "margem_sobre_venda"),
  },
  {
    key: "margem_sobre_custo",
    label: "Margem sobre Custo %",
    value: (v) => valorRentabilidade(v, "margem_sobre_custo"),
  },
];

function normalizarValorExcel(valor) {
  if (valor === null || valor === undefined) return "";
  return valor;
}

function criarDadosExcel(linhas) {
  return linhas.map((linha, indice) =>
    linha.map((valor) => {
      const celula = { value: normalizarValorExcel(valor) };
      if (indice !== 0) return celula;

      return {
        ...celula,
        fontWeight: "bold",
        backgroundColor: "#DBEAFE",
      };
    }),
  );
}

function criarColunasExcel(linhas) {
  const totalColunas = Math.max(...linhas.map((linha) => linha.length), 0);
  return Array.from({ length: totalColunas }, (_, indice) => {
    const maiorTexto = linhas.reduce((maior, linha) => {
      const tamanho = String(normalizarValorExcel(linha[indice])).length;
      return Math.max(maior, tamanho);
    }, 0);
    return { width: Math.min(Math.max(maiorTexto + 2, 12), 42) };
  });
}

export async function exportarPlanilhasExcel(planilhas, nomeArquivo) {
  await writeExcelFile(
    planilhas.map(({ sheet, linhas }) => ({
      sheet,
      data: criarDadosExcel(linhas),
      columns: criarColunasExcel(linhas),
      stickyRowsCount: 1,
    })),
  ).toFile(nomeArquivo);
}
