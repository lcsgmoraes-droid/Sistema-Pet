export function copiarFiltrosAnalise(filtros) {
  return {
    ...filtros,
    fornecedor_ids: [...(filtros.fornecedor_ids || [])],
  };
}

export function montarParamsAnalise(filtros) {
  const params = new URLSearchParams();
  params.append("_t", Date.now());
  params.append("fornecedor_modo", filtros.fornecedor_modo);
  params.append("ocultar_taxas_cartao", filtros.ocultar_taxas_cartao ? "true" : "false");
  params.append("apenas_taxas_cartao", filtros.apenas_taxas_cartao ? "true" : "false");

  filtros.fornecedor_ids.forEach((id) => params.append("fornecedor_ids", id));
  if (filtros.origem !== "todos") params.append("origem", filtros.origem);
  if (filtros.tipo_despesa_id) params.append("tipo_despesa_id", filtros.tipo_despesa_id);
  if (filtros.tipo_custo !== "todos") params.append("tipo_custo", filtros.tipo_custo);

  return params;
}

export function montarParamsDetalhes(filtros, detalhe, page) {
  const params = montarParamsAnalise(filtros);
  params.append("grupo", detalhe.grupo);
  if (detalhe.grupo_id !== undefined && detalhe.grupo_id !== null) {
    params.append("grupo_id", detalhe.grupo_id);
  }
  params.append("page", page);
  params.append("page_size", 30);
  return params;
}
