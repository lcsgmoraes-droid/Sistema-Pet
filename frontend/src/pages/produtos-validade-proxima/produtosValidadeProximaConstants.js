export const ITENS_POR_PAGINA_INICIAL = 20;

export const QUICK_DAYS = [30, 60, 90, 120];

export const filtrosIniciais = {
  busca: "",
  dias: 60,
  status_validade: "proximos",
  categoria_id: "",
  marca_id: "",
  departamento_id: "",
  fornecedor_id: "",
  fornecedor_busca: "",
  apenas_com_estoque: true,
  ordenacao: "validade_asc",
  page_size: ITENS_POR_PAGINA_INICIAL,
};

export function criarDadosValidadeVazios(pageSize = ITENS_POR_PAGINA_INICIAL) {
  return {
    items: [],
    total: 0,
    page: 1,
    page_size: pageSize,
    pages: 0,
    totais: {
      total_lotes: 0,
      total_produtos: 0,
      total_quantidade: 0,
      lotes_vencidos: 0,
      lotes_ate_7_dias: 0,
      lotes_ate_30_dias: 0,
      lotes_ate_60_dias: 0,
      valor_custo_em_risco: 0,
      valor_venda_em_risco: 0,
    },
  };
}

export function montarParametros(filtros, pagina, pageSizeOverride) {
  const params = {
    page: pagina,
    page_size: Number(pageSizeOverride || filtros.page_size) || ITENS_POR_PAGINA_INICIAL,
    dias: Number(filtros.dias) || 60,
    status_validade: filtros.status_validade || "proximos",
    apenas_com_estoque: Boolean(filtros.apenas_com_estoque),
    ordenacao: filtros.ordenacao || "validade_asc",
  };

  if (filtros.busca?.trim()) params.busca = filtros.busca.trim();
  if (filtros.categoria_id) params.categoria_id = filtros.categoria_id;
  if (filtros.marca_id) params.marca_id = filtros.marca_id;
  if (filtros.departamento_id) params.departamento_id = filtros.departamento_id;
  if (filtros.fornecedor_id) params.fornecedor_id = filtros.fornecedor_id;

  return params;
}
