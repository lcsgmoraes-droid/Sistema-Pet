import { ITENS_POR_PAGINA_INICIAL } from "./produtosRelatorioConstants";
import { dataInicioPorDias, hojeIso } from "./produtosRelatorioFormatters";

export function criarFiltrosPadrao() {
  return {
    data_inicio: dataInicioPorDias(30),
    data_fim: hojeIso(),
    tipo_movimentacao: "",
    page_size: ITENS_POR_PAGINA_INICIAL,
    produto_id: "",
  };
}

export function montarParamsMovimentacoes(filtros, pagina, extra = {}) {
  const params = {
    page: pagina,
    page_size: Number(filtros.page_size) || ITENS_POR_PAGINA_INICIAL,
    ...extra,
  };

  if (filtros.data_inicio) params.data_inicio = filtros.data_inicio;
  if (filtros.data_fim) params.data_fim = filtros.data_fim;
  if (filtros.tipo_movimentacao) params.tipo_movimentacao = filtros.tipo_movimentacao;
  if (filtros.produto_id) params.produto_id = filtros.produto_id;

  return params;
}

export function criarDadosMovimentacoesVazios(pageSize = ITENS_POR_PAGINA_INICIAL) {
  return {
    movimentacoes: [],
    total_registros: 0,
    page: 1,
    page_size: Number(pageSize || ITENS_POR_PAGINA_INICIAL),
    pages: 0,
    totais: {
      total_entradas: 0,
      total_saidas: 0,
      valor_total: 0,
    },
  };
}

export function normalizarDadosMovimentacoes(payload, filtros, pagina) {
  return {
    movimentacoes: Array.isArray(payload.movimentacoes) ? payload.movimentacoes : [],
    total_registros: Number(payload.total_registros || 0),
    page: Number(payload.page || pagina),
    page_size: Number(payload.page_size || filtros.page_size || ITENS_POR_PAGINA_INICIAL),
    pages: Number(payload.pages || 0),
    totais: {
      total_entradas: Number(payload?.totais?.total_entradas || 0),
      total_saidas: Number(payload?.totais?.total_saidas || 0),
      valor_total: Number(payload?.totais?.valor_total || 0),
    },
  };
}
