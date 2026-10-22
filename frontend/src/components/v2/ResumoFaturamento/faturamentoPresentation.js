export function formatarDataFaturamento(valor) {
  const data = String(valor || "").slice(0, 10);
  return /^\d{4}-\d{2}-\d{2}$/.test(data) ? data.split("-").reverse().join("/") : "—";
}

export function periodoFaturamento(composicao, fallback = "Período selecionado") {
  if (!composicao?.data_inicio || !composicao?.data_fim) return fallback;
  const inicio = formatarDataFaturamento(composicao.data_inicio);
  const fim = formatarDataFaturamento(composicao.data_fim);
  return inicio === fim ? inicio : `${inicio} a ${fim}`;
}

export function formulaFaturamento(composicao) {
  return Number(composicao?.devolucoes || 0) !== 0
    ? "Vendas − descontos − devoluções"
    : "Vendas − descontos";
}

export function linhasFaturamento(composicao) {
  if (!composicao) return [];
  const linhas = [
    ["Faturamento bruto", composicao.faturamento_bruto],
    ["Descontos", composicao.descontos],
  ];
  if (Number(composicao.devolucoes || 0) !== 0) linhas.push(["Devoluções", composicao.devolucoes]);
  linhas.push(["Faturamento líquido", composicao.faturamento_liquido]);
  if (Number(composicao.taxa_entrega || 0) !== 0) {
    linhas.push(["Entrega cobrada à parte", composicao.taxa_entrega]);
    linhas.push(["Total das vendas com entrega", composicao.total_vendas]);
  }
  return linhas;
}

export function linhasQuitacao(composicao) {
  if (!composicao) return [];
  return [
    ["Pago", composicao.valor_pago],
    ["Créditos e cashback utilizados", composicao.creditos_utilizados],
    ["Crediário a receber", composicao.crediario_receber],
    ["Aguardando pagamento, sem crediário", composicao.em_aberto],
  ];
}
