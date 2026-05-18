import toast from "react-hot-toast";
import api from "../../api";
import {
  COLUNAS_RELATORIO_VENDAS,
  exportarPlanilhasExcel,
  filtrarVendasParaRelatorio,
  formatarData,
  ordenarVendasRelatorio,
} from "./vendasFinanceiroUtils";

export async function exportarRelatorioListaVendasFinanceiro({
  colunasRelatorio,
  escopo,
  filtroCategoria,
  filtroFormaPagamento,
  filtroFuncionario,
  filtroStatusLista,
  listaVendas,
  ordenacaoRelatorio,
}) {
  const dadosFiltrados = filtrarVendasParaRelatorio({
    escopo,
    vendas: listaVendas,
    filtroFuncionario,
    filtroFormaPagamento,
    filtroCategoria,
    filtroStatusLista,
  });

  if (!dadosFiltrados.length) {
    toast.error("Nao ha vendas para exportar neste relatorio.");
    return;
  }

  const dadosOrdenados = ordenarVendasRelatorio(dadosFiltrados, ordenacaoRelatorio);
  const colunas = COLUNAS_RELATORIO_VENDAS.filter((coluna) =>
    colunasRelatorio.includes(coluna.key),
  );

  if (!colunas.length) {
    toast.error("Selecione pelo menos uma coluna para exportar.");
    return;
  }

  const linhas = dadosOrdenados.map((venda) =>
    colunas.map((coluna) => {
      const bruto = coluna.value(venda);
      return coluna.key === "data_venda" ? formatarData(bruto) : bruto;
    }),
  );

  const dataArquivo = new Date().toISOString().slice(0, 10);
  const sufixo = escopo === "geral" ? "geral" : "filtrado";

  try {
    await exportarPlanilhasExcel(
      [
        {
          sheet: "Lista de Vendas",
          linhas: [colunas.map((coluna) => coluna.label), ...linhas],
        },
      ],
      `vendas_${sufixo}_${dataArquivo}.xlsx`,
    );
    toast.success(`Relatorio gerado com ${linhas.length} venda(s).`);
  } catch (error) {
    console.error("Erro ao exportar relatorio de vendas:", error);
    toast.error("Nao foi possivel gerar o arquivo Excel.");
  }
}

export async function exportarVendasFinanceiroPdf({
  dataFim,
  dataInicio,
  filtroCategoria,
  filtroFormaPagamento,
  filtroFuncionario,
}) {
  if (!dataInicio || !dataFim) {
    toast.error("Selecione um período para gerar o relatório");
    return;
  }

  try {
    toast.loading("Gerando PDF...", { id: "pdf" });

    const params = new URLSearchParams({
      data_inicio: dataInicio,
      data_fim: dataFim,
    });

    if (filtroFuncionario) params.append("funcionario", filtroFuncionario);
    if (filtroFormaPagamento) params.append("forma_pagamento", filtroFormaPagamento);
    if (filtroCategoria) params.append("categoria", filtroCategoria);

    const response = await api.get(
      `/relatorios/vendas/export/pdf?${params.toString()}`,
      {
        responseType: "blob",
      },
    );

    const url = globalThis.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute(
      "download",
      `relatorio_vendas_${dataInicio}_${dataFim}.pdf`,
    );
    document.body.appendChild(link);
    link.click();
    link.remove();

    toast.success("📄 PDF exportado com sucesso!", { id: "pdf" });
  } catch (error) {
    console.error("Erro ao exportar PDF:", error);
    toast.error("Erro ao exportar PDF", { id: "pdf" });
  }
}

export async function exportarVendasFinanceiroExcel({
  dataFim,
  dataInicio,
  formasRecebimentoFiltradas,
  resumo,
  vendasPorDataCalendario,
}) {
  const resumoData = [
    ["RELATÓRIO DE VENDAS"],
    ["Período:", `${formatarData(dataInicio)} até ${formatarData(dataFim)}`],
    [""],
    ["Métrica", "Valor"],
    ["Venda Bruta", resumo.venda_bruta],
    ["Taxa de Entrega", resumo.taxa_entrega],
    ["Desconto", resumo.desconto],
    ["Venda Líquida", resumo.venda_liquida],
    ["Em Aberto", resumo.em_aberto],
    ["Quantidade de Vendas", resumo.quantidade_vendas],
  ];
  const planilhas = [
    {
      sheet: "Resumo",
      linhas: resumoData,
    },
  ];

  if (vendasPorDataCalendario.length > 0) {
    const vendasData = [
      [
        "Data",
        "Dia",
        "Qtd",
        "Tkt. Médio",
        "Vl. bruto",
        "Taxa entrega",
        "Desconto",
        "(%)",
        "Vl. líquido",
        "Vl. recebido",
        "Saldo aberto",
      ],
      ...vendasPorDataCalendario.map((venda) => [
        formatarData(venda.data),
        venda.feriado_nome || venda.dia_semana,
        venda.quantidade,
        venda.ticket_medio,
        venda.valor_bruto,
        venda.taxa_entrega,
        venda.desconto,
        venda.percentual_desconto,
        venda.valor_liquido,
        venda.valor_recebido,
        venda.saldo_aberto,
      ]),
    ];
    planilhas.push({
      sheet: "Vendas por Data",
      linhas: vendasData,
    });
  }

  if (formasRecebimentoFiltradas.length > 0) {
    const formasData = [
      ["Forma", "Valor pago"],
      ...formasRecebimentoFiltradas.map((forma) => [
        forma.forma_pagamento,
        forma.valor_total,
      ]),
    ];
    planilhas.push({
      sheet: "Formas Pagamento",
      linhas: formasData,
    });
  }

  const fileName = `relatorio_vendas_${dataInicio}_${dataFim}.xlsx`;
  try {
    await exportarPlanilhasExcel(planilhas, fileName);
    toast.success("Excel exportado com sucesso!");
  } catch (error) {
    console.error("Erro ao exportar Excel:", error);
    toast.error("Erro ao exportar Excel");
  }
}
