function numeroFinanceiroSeguro(valor) {
  const numero = Number(valor);
  return Number.isFinite(numero) && numero > 0 ? numero : 0;
}

function inteiroSeguro(valor) {
  return Math.trunc(numeroFinanceiroSeguro(valor));
}

function arredondarMoeda(valor) {
  return Math.round((valor + Number.EPSILON) * 100) / 100;
}

export function calcularResumoEmAbertoCliente(resumo = {}) {
  const totalVendas = inteiroSeguro(resumo.total_vendas);
  const totalParcelasCrediario = inteiroSeguro(resumo.total_parcelas_crediario);
  const totalVendasEmAberto = numeroFinanceiroSeguro(resumo.total_em_aberto);
  const totalCrediarioEmAberto = numeroFinanceiroSeguro(resumo.total_crediario_em_aberto);
  const totalCrediarioVencido = numeroFinanceiroSeguro(resumo.total_crediario_vencido);

  return {
    total_vendas: totalVendas,
    total_parcelas_crediario: totalParcelasCrediario,
    total_vendas_em_aberto: arredondarMoeda(totalVendasEmAberto),
    total_crediario_em_aberto: arredondarMoeda(totalCrediarioEmAberto),
    total_crediario_vencido: arredondarMoeda(totalCrediarioVencido),
    total_geral_em_aberto: arredondarMoeda(totalVendasEmAberto + totalCrediarioEmAberto),
  };
}
