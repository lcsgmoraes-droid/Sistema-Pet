import toast from "react-hot-toast";

import api from "../../../api";
import { montarFeedbackReprocessamentoVendas } from "../vendasReprocessamentoFeedback";
import {
  COLUNAS_RELATORIO_VENDAS,
  exportarPlanilhasExcel,
  filtrarVendasRelatorio,
  ordenarVendasRelatorio,
} from "../vendasFinanceiroUtils";

export function useVendasFinanceiroActions({
  carregarDados,
  colunasRelatorio,
  dataFim,
  dataInicio,
  filtroCanalVenda,
  filtroCategoria,
  filtroFormaPagamento,
  filtroFuncionario,
  filtroStatusLista,
  formasRecebimentoFiltradas,
  formatarData,
  linhasVendasRefs,
  listaVendasComImpostoAjustado,
  listaVendasFiltrada,
  listaVendasPorCanal,
  ordenacaoRelatorio,
  resumo,
  setFeedbackReprocessamento,
  setReprocessandoRentabilidade,
  setVendasSelecionadasIds,
  vendasPorDataCalendario,
}) {
  const filtrarVendasParaRelatorio = (escopo) =>
    filtrarVendasRelatorio(listaVendasComImpostoAjustado, {
      escopo,
      filtroFuncionario,
      filtroFormaPagamento,
      filtroCategoria,
      filtroStatusLista,
    });

  const exportarRelatorioListaVendas = async ({ escopo }) => {
    const dadosFiltrados = filtrarVendasParaRelatorio(escopo);

    if (!dadosFiltrados.length) {
      toast.error("Nao ha vendas para exportar neste relatorio.");
      return;
    }

    const dadosOrdenados = ordenarVendasRelatorio(dadosFiltrados, ordenacaoRelatorio);
    const chaves = colunasRelatorio;
    const colunas = COLUNAS_RELATORIO_VENDAS.filter((coluna) => chaves.includes(coluna.key));

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
  };

  const exportarParaPDF = async () => {
    if (!dataInicio || !dataFim) {
      toast.error("Selecione um periodo para gerar o relatorio");
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
      if (filtroCanalVenda) params.append("canal_venda", filtroCanalVenda);

      const response = await api.get(`/relatorios/vendas/export/pdf?${params.toString()}`, {
        responseType: "blob",
      });

      const url = globalThis.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `relatorio_vendas_${dataInicio}_${dataFim}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();

      toast.success("PDF exportado com sucesso!", { id: "pdf" });
    } catch (error) {
      console.error("Erro ao exportar PDF:", error);
      toast.error("Erro ao exportar PDF", { id: "pdf" });
    }
  };

  const exportarParaExcel = async () => {
    const resumoData = [
      ["RELATORIO DE VENDAS"],
      ["Periodo:", `${formatarData(dataInicio)} ate ${formatarData(dataFim)}`],
      [""],
      ["Metrica", "Valor"],
      ["Venda Bruta", resumo.venda_bruta],
      ["Taxa de Entrega", resumo.taxa_entrega],
      ["Desconto", resumo.desconto],
      ["Venda Liquida", resumo.venda_liquida],
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
          "Tkt. Medio",
          "Vl. bruto",
          "Taxa entrega",
          "Desconto",
          "(%)",
          "Vl. liquido",
          "Vl. recebido",
          "Saldo aberto",
        ],
        ...vendasPorDataCalendario.map((v) => [
          formatarData(v.data),
          v.feriado_nome || v.dia_semana,
          v.quantidade,
          v.ticket_medio,
          v.valor_bruto,
          v.taxa_entrega,
          v.desconto,
          v.percentual_desconto,
          v.valor_liquido,
          v.valor_recebido,
          v.saldo_aberto,
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
        ...formasRecebimentoFiltradas.map((f) => [f.forma_pagamento, f.valor_total]),
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
  };

  const toggleSelecaoVenda = (vendaId, selecionada) => {
    setVendasSelecionadasIds((prev) => {
      const proximo = new Set(prev);
      if (selecionada) {
        proximo.add(vendaId);
      } else {
        proximo.delete(vendaId);
      }
      return proximo;
    });
  };

  const toggleSelecaoTodasVendas = (selecionar) => {
    setVendasSelecionadasIds((prev) => {
      const proximo = new Set(prev);
      listaVendasFiltrada.forEach((venda) => {
        if (selecionar) {
          proximo.add(venda.id);
        } else {
          proximo.delete(venda.id);
        }
      });
      return proximo;
    });
  };

  const registrarLinhaVendaReprocessada = (vendaId, element) => {
    const idNormalizado = Number(vendaId);
    if (!Number.isFinite(idNormalizado) || idNormalizado <= 0) return;

    if (element) {
      linhasVendasRefs.current.set(idNormalizado, element);
    } else {
      linhasVendasRefs.current.delete(idNormalizado);
    }
  };

  const aplicarFeedbackReprocessamento = (vendaIds) => {
    const feedback = montarFeedbackReprocessamentoVendas({
      vendaIds,
      vendasVisiveis: listaVendasFiltrada,
    });

    if (!feedback.ids.length) return;

    setFeedbackReprocessamento((prev) => ({
      ids: new Set(feedback.ids),
      focoId: feedback.focoId,
      token: prev.token + 1,
    }));
  };

  const reprocessarRentabilidadeVendas = async ({ vendaIds = null, periodo = false } = {}) => {
    const ids = Array.isArray(vendaIds)
      ? vendaIds.map((id) => Number(id)).filter((id) => Number.isFinite(id) && id > 0)
      : [];
    const quantidade = periodo ? listaVendasPorCanal.length : ids.length;

    if (periodo && (!dataInicio || !dataFim)) {
      toast.error("Selecione um periodo para reprocessar.");
      return;
    }

    if (quantidade <= 0) {
      toast.error(periodo ? "Nao ha vendas no periodo atual." : "Selecione pelo menos uma venda.");
      return;
    }

    const descricaoEscopo = periodo
      ? `do periodo ${formatarData(dataInicio)} ate ${formatarData(dataFim)}`
      : "selecionada(s)";
    const confirmou = globalThis.confirm(
      `Reprocessar ${quantidade} venda(s) ${descricaoEscopo}?\n\n` +
        "Isso atualiza o custo das movimentacoes de estoque da venda para o custo atual do produto e recalcula custo, lucro e margem.",
    );

    if (!confirmou) return;

    const toastId = "reprocessar-rentabilidade-vendas";
    setReprocessandoRentabilidade(true);
    toast.loading("Reprocessando rentabilidade das vendas...", { id: toastId });

    try {
      const payload = periodo
        ? {
            data_inicio: dataInicio,
            data_fim: dataFim,
            ...(filtroCanalVenda ? { canal_venda: filtroCanalVenda } : {}),
          }
        : { venda_ids: ids };

      const { data } = await api.post("/relatorios/vendas/reprocessar-rentabilidade", payload);
      const total = Number(data?.total_reprocessado || 0);
      const vendasReprocessadasIds = Array.isArray(data?.vendas)
        ? data.vendas.map((venda) => venda?.venda_id)
        : ids;
      toast.success(`${total} venda(s) reprocessada(s).`, { id: toastId });
      setVendasSelecionadasIds(new Set());
      await carregarDados();
      aplicarFeedbackReprocessamento(vendasReprocessadasIds);
    } catch (error) {
      console.error("Erro ao reprocessar rentabilidade:", error);
      toast.error(error?.response?.data?.detail || "Nao foi possivel reprocessar as vendas.", {
        id: toastId,
      });
    } finally {
      setReprocessandoRentabilidade(false);
    }
  };

  return {
    exportarParaExcel,
    exportarParaPDF,
    exportarRelatorioListaVendas,
    registrarLinhaVendaReprocessada,
    reprocessarRentabilidadeVendas,
    toggleSelecaoTodasVendas,
    toggleSelecaoVenda,
  };
}
