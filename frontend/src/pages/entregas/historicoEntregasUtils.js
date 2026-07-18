export function formatarDuracao(minutos) {
  if (minutos == null || minutos === "") return "Não informado";
  const total = Number(minutos);
  if (!Number.isFinite(total) || total < 0) return "Não informado";
  if (total < 60) return `${Math.round(total)} min`;
  const horas = Math.floor(total / 60);
  const restante = Math.round(total % 60);
  return restante > 0 ? `${horas}h ${restante}min` : `${horas}h`;
}

export function obterQuantidadeEntregas(rota) {
  const informado = Number(rota?.total_entregas);
  if (Number.isFinite(informado) && informado > 0) return informado;
  if (Array.isArray(rota?.paradas) && rota.paradas.length > 0) return rota.paradas.length;
  return rota?.venda_id ? 1 : 0;
}

export function obterDistanciaRota(rota) {
  const opcoes = [rota?.distancia_real, rota?.distancia_total_km_real, rota?.distancia_prevista];
  const encontrada = opcoes.map(Number).find((valor) => Number.isFinite(valor) && valor > 0);
  if (encontrada) return encontrada;

  const inicial = Number(rota?.km_inicial);
  const final = Number(rota?.km_final);
  return Number.isFinite(inicial) && Number.isFinite(final) && final >= inicial
    ? final - inicial
    : 0;
}

export function calcularResumoHistorico(rotas = []) {
  const resumo = rotas.reduce(
    (acc, rota) => {
      acc.rotas += 1;
      acc.entregas += obterQuantidadeEntregas(rota);
      acc.distancia += obterDistanciaRota(rota);
      acc.custo += Number(rota.custo_real) || 0;
      acc.taxas += Number(rota.taxa_total_entregas ?? rota.taxa_entrega_cliente) || 0;
      acc.vendas += Number(rota.valor_total_vendas) || 0;
      return acc;
    },
    { rotas: 0, entregas: 0, distancia: 0, custo: 0, taxas: 0, vendas: 0 },
  );

  resumo.custoMedio = resumo.entregas > 0 ? resumo.custo / resumo.entregas : 0;
  resumo.resultadoEntrega = resumo.taxas - resumo.custo;
  return resumo;
}

export function montarParametrosHistorico(filtros = {}) {
  const params = {
    status: "concluida",
    ordenar_por: filtros.ordenarPor || "data_conclusao",
    direcao: filtros.direcao || "desc",
    limite: 500,
  };
  if (filtros.dataInicio) params.data_inicio = filtros.dataInicio;
  if (filtros.dataFim) params.data_fim = filtros.dataFim;
  if (filtros.entregadorId) params.entregador_id = filtros.entregadorId;
  if (filtros.busca?.trim()) params.busca = filtros.busca.trim();
  return params;
}
