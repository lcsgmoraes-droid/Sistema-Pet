export function criarFiltrosPadraoContasReceber() {
  return {
    status: "todos",
    cliente_id: null,
    data_inicio: "",
    data_fim: "",
    apenas_vencidas: false,
    apenas_vencer: false,
  };
}

export function criarFiltrosContasReceberDaUrl(searchParams) {
  const filtros = criarFiltrosPadraoContasReceber();
  const filtro = searchParams?.get?.("filtro");
  const clienteId = searchParams?.get?.("cliente_id");

  if (filtro === "em_aberto") filtros.status = "em_aberto";
  if (filtro === "vencidas") filtros.apenas_vencidas = true;
  if (clienteId && /^\d+$/.test(clienteId)) filtros.cliente_id = clienteId;

  return filtros;
}

export function normalizarListaClientes(payload) {
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload?.items)) return payload.items;
  if (Array.isArray(payload?.clientes)) return payload.clientes;
  return [];
}

export function aplicarPeriodoRapidoContasReceber(filtros, periodo) {
  const novosFiltros = {
    ...filtros,
    data_inicio: "",
    data_fim: "",
    apenas_vencidas: false,
    apenas_vencer: false,
  };
  if (periodo === "vencidas") novosFiltros.apenas_vencidas = true;
  if (periodo === "a_vencer") novosFiltros.apenas_vencer = true;
  return novosFiltros;
}

export function montarParamsFiltrosContasReceber(filtros = {}, numeroVenda = "") {
  const params = new URLSearchParams();
  if (filtros.status && filtros.status !== "todos") params.append("status", filtros.status);
  if (filtros.cliente_id) params.append("cliente_id", filtros.cliente_id);
  if (filtros.data_inicio) params.append("data_inicio", filtros.data_inicio);
  if (filtros.data_fim) params.append("data_fim", filtros.data_fim);
  if (filtros.apenas_vencidas) params.append("apenas_vencidas", "true");
  if (filtros.apenas_vencer) params.append("apenas_vencer", "true");
  if (numeroVenda) params.append("numero_venda", numeroVenda);
  return params;
}
