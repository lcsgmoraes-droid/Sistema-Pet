import writeExcelFile from "write-excel-file/browser";

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
  { key: "taxa_cartao", label: "Taxa Pagto", value: (v) => Number(v.taxa_cartao || 0) },
  { key: "comissao", label: "Comissao", value: (v) => Number(v.comissao || 0) },
  { key: "imposto", label: "Imposto", value: (v) => Number(v.imposto || 0) },
  { key: "custo_campanha", label: "Custo Campanha", value: (v) => Number(v.custo_campanha || 0) },
  { key: "venda_liquida", label: "Venda Liquida", value: (v) => Number(v.venda_liquida || 0) },
  { key: "valor_recebido", label: "Valor Recebido", value: (v) => Number(v.valor_recebido || 0) },
  { key: "custo_produtos", label: "Custo Produtos", value: (v) => Number(v.custo_produtos || 0) },
  { key: "lucro", label: "Lucro", value: (v) => Number(v.lucro || 0) },
  {
    key: "margem_sobre_venda",
    label: "Margem sobre Venda %",
    value: (v) => Number(v.margem_sobre_venda || 0),
  },
  {
    key: "margem_sobre_custo",
    label: "Margem sobre Custo %",
    value: (v) => Number(v.margem_sobre_custo || 0),
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
