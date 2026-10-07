export function getDreAlertMetrics(alerta) {
  switch (alerta.codigo) {
    case "cmv_produtos_sem_custo":
      return [
        { tipo: "quantidade", rotulo: "produto(s) sem custo", valor: alerta.quantidade_produtos },
        { tipo: "moeda", rotulo: "Vendas afetadas", valor: alerta.valor_vendas },
        { tipo: "moeda", rotulo: "CMV provisório", valor: alerta.valor_estimado },
      ];
    case "cmv_rateio_ambiguo":
      return [
        {
          tipo: "quantidade",
          rotulo: "itens com rateio a conferir",
          valor: alerta.quantidade_itens,
        },
        { tipo: "moeda", rotulo: "CMV rateado na DRE", valor: alerta.valor_estimado },
      ];
    case "cmv_agregado_sem_rateio":
      return [
        { tipo: "quantidade", rotulo: "vendas a conciliar", valor: alerta.quantidade_vendas },
        { tipo: "moeda", rotulo: "CMV sem rateio", valor: alerta.valor_sem_rateio },
      ];
    case "devolucao_custo_original_pendente":
      return [
        {
          tipo: "quantidade",
          rotulo: "itens devolvidos com custo a conferir",
          valor: alerta.quantidade_itens,
        },
        { tipo: "moeda", rotulo: "Devoluções afetadas", valor: alerta.valor_vendas },
      ];
    case "devolucao_imposto_a_conciliar":
      return [{ tipo: "moeda", rotulo: "Devoluções a conciliar", valor: alerta.valor_vendas }];
    default:
      return [];
  }
}

export function getDreAlertDetail(alerta) {
  if (alerta.codigo === "cmv_produtos_sem_custo") {
    return { campo: "cmv_estimado", rotulo: "Ver produtos e vendas" };
  }
  if (alerta.codigo?.startsWith("devolucao_")) {
    return { campo: "devolucoes", rotulo: "Ver devoluções" };
  }
  return null;
}
