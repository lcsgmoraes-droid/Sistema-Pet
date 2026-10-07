import { calcularTotaisOrcamento, roundMoney, toNumber } from "./orcamentoUtils.js";

const formatoMoeda = '"R$" #,##0.00';
const celulaMoeda = (valor, estilo = {}) => ({
  value: roundMoney(valor),
  format: formatoMoeda,
  ...estilo,
});
const cabecalho = (valor) => ({
  value: valor,
  fontWeight: "bold",
  backgroundColor: "#DCFCE7",
  color: "#14532D",
});

function tipoItem(origem) {
  if (origem === "catalogo") return "Procedimento";
  if (origem === "produto") return "Produto";
  if (origem === "diaria") return "Diária";
  return "Item";
}

export function montarLinhasOrcamentoExcel(orcamento) {
  const itens = Array.isArray(orcamento?.itens) ? orcamento.itens : [];
  const totais = calcularTotaisOrcamento(itens);
  const vinculo = orcamento?.internacao_id
    ? `Internação #${orcamento.internacao_id}`
    : `Consulta #${orcamento?.consulta_id || "—"}`;

  return [
    [{ value: orcamento?.titulo || "Orçamento veterinário", fontWeight: "bold", fontSize: 15 }],
    ["Vínculo", vinculo],
    ["Orçamento", `#${orcamento?.id || "—"}`],
    [],
    [
      "Item",
      "Tipo",
      "Qtd.",
      "Un.",
      "Custo un.",
      "Custo total",
      "Preço un.",
      "Preço total",
      "Margem",
    ].map(cabecalho),
    ...itens.map((item) => [
      item.nome || "Item sem nome",
      tipoItem(item.origem),
      toNumber(item.quantidade),
      item.unidade || "",
      celulaMoeda(item.custo_unitario_estimado),
      celulaMoeda(item.custo_total_estimado),
      celulaMoeda(item.preco_unitario),
      celulaMoeda(item.preco_total),
      celulaMoeda(item.margem_valor),
    ]),
    [
      { value: "TOTAL", fontWeight: "bold", backgroundColor: "#F1F5F9" },
      "",
      "",
      "",
      "",
      celulaMoeda(totais.custo_total_estimado, { fontWeight: "bold" }),
      "",
      celulaMoeda(totais.preco_total, { fontWeight: "bold" }),
      celulaMoeda(totais.margem_valor, { fontWeight: "bold" }),
    ],
  ];
}

export async function baixarOrcamentoExcel(orcamento) {
  const { default: writeExcelFile } = await import("write-excel-file/browser");
  const referencia = orcamento?.internacao_id
    ? `internacao_${orcamento.internacao_id}`
    : `consulta_${orcamento.consulta_id}`;
  const nomeArquivo = `orcamento_${referencia}_${orcamento.id}.xlsx`;

  await writeExcelFile(montarLinhasOrcamentoExcel(orcamento), {
    sheet: "Orçamento",
    stickyRowsCount: 5,
    columns: [
      { width: 38 },
      { width: 17 },
      { width: 10 },
      { width: 10 },
      { width: 16 },
      { width: 18 },
      { width: 16 },
      { width: 18 },
      { width: 18 },
    ],
  }).toFile(nomeArquivo);
}
