const dataBR = (valor) => (valor ? String(valor).slice(0, 10).split("-").reverse().join("/") : "");

const periodoBR = (bloco) => {
  const inicio = dataBR(bloco?.data_inicio);
  const fim = dataBR(bloco?.data_fim);
  return inicio === fim ? inicio : `${inicio} a ${fim}`;
};

// PDF e comprovantes usam a composição pronta do backend, sem recalcular vendas.
export function criarResumoImpressaoCaixa(resumo) {
  const vendas = resumo.vendas_periodo;
  const recebimentos = resumo.composicao_recebimentos;
  const linhasVendas = vendas
    ? [
        ["Faturamento bruto", vendas.faturamento_bruto],
        ["Descontos", vendas.descontos],
        ["Devoluções das vendas", vendas.devolucoes],
        ["Faturamento líquido", vendas.faturamento_liquido],
        ["Entrega", vendas.taxa_entrega],
        ["Total das vendas com entrega", vendas.total_vendas],
        ["Valor pago das vendas", vendas.valor_pago],
        ["Créditos e benefícios utilizados", vendas.creditos_utilizados],
        ["Crediário a receber", vendas.crediario_receber],
        ["Em aberto sem crediário", vendas.em_aberto],
      ]
    : [
        ["Vendas vinculadas ao caixa", resumo.total_vendido],
        ["Crediário das vendas vinculadas", resumo.total_vendas_crediario ?? 0],
      ];
  const linhasRecebimentos = recebimentos
    ? [
        ["De vendas do período", recebimentos.vendas_periodo],
        ["De vendas anteriores", recebimentos.vendas_anteriores],
        ["(-) Devoluções e estornos no caixa", recebimentos.devolucoes],
        ["Recebimentos neste caixa", recebimentos.total_recebido],
        ["Créditos e benefícios usados no caixa", recebimentos.creditos_utilizados],
      ]
    : [["Quitações registradas no caixa (legado)", resumo.total_recebido]];

  return {
    tituloVendas: vendas ? `Vendas de ${periodoBR(vendas)}` : "Vendas vinculadas ao caixa",
    periodoRecebimentos: recebimentos ? periodoBR(recebimentos) : "",
    linhasVendas,
    linhasRecebimentos,
    formas: Object.entries(
      recebimentos?.por_forma_pagamento ??
        resumo.recebimentos_por_forma_pagamento ??
        resumo.vendas_por_forma_pagamento ??
        {},
    ),
    novoContrato: Boolean(vendas && recebimentos),
  };
}
