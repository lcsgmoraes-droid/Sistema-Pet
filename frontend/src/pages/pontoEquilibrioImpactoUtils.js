function numeroSeguro(valor) {
  const numero = Number(valor);
  return Number.isFinite(numero) ? numero : 0;
}

function arredondarCentavos(valor) {
  return Math.round((valor + Number.EPSILON) * 100) / 100;
}

function calcularVendasImpacto(impactoPontoEquilibrio, ticketMedio) {
  if (!Number.isFinite(ticketMedio) || ticketMedio <= 0) return null;
  if (!Number.isFinite(impactoPontoEquilibrio) || impactoPontoEquilibrio === 0) return 0;

  const vendas = Math.ceil(Math.abs(impactoPontoEquilibrio) / ticketMedio);
  return impactoPontoEquilibrio > 0 ? vendas : -vendas;
}

export function calcularImpactoPontoEquilibrio({
  despesasFixas,
  pontoEquilibrio,
  margemContribuicaoPercentual,
  faturamento,
  ticketMedio,
  impactoCustoFixo,
}) {
  const despesasFixasAtuais = numeroSeguro(despesasFixas);
  const margemPercentual = numeroSeguro(margemContribuicaoPercentual);
  const margemDecimal = margemPercentual / 100;
  const faturamentoAtual = numeroSeguro(faturamento);
  const ticketMedioAtual = numeroSeguro(ticketMedio);
  const impactoInformado = numeroSeguro(impactoCustoFixo);
  const novoCustoFixo = Math.max(0, despesasFixasAtuais + impactoInformado);

  if (margemDecimal <= 0) {
    return {
      calculavel: false,
      novoCustoFixo: arredondarCentavos(novoCustoFixo),
      impactoRealCustoFixo: arredondarCentavos(novoCustoFixo - despesasFixasAtuais),
      impactoPontoEquilibrio: null,
      novoPontoEquilibrio: null,
      novaFaltaFaturar: null,
      saldoAposSimulacao: null,
      vendasImpacto: null,
    };
  }

  const pontoAtualCalculado = despesasFixasAtuais / margemDecimal;
  const pontoAtual = Number.isFinite(Number(pontoEquilibrio))
    ? Number(pontoEquilibrio)
    : pontoAtualCalculado;
  const impactoRealCustoFixo = novoCustoFixo - despesasFixasAtuais;
  const impactoPontoEquilibrio = impactoRealCustoFixo / margemDecimal;
  const novoPontoEquilibrio = Math.max(0, pontoAtual + impactoPontoEquilibrio);
  const novaFaltaFaturar = Math.max(0, novoPontoEquilibrio - faturamentoAtual);
  const saldoAposSimulacao = faturamentoAtual - novoPontoEquilibrio;

  return {
    calculavel: true,
    novoCustoFixo: arredondarCentavos(novoCustoFixo),
    impactoRealCustoFixo: arredondarCentavos(impactoRealCustoFixo),
    impactoPontoEquilibrio: arredondarCentavos(impactoPontoEquilibrio),
    novoPontoEquilibrio: arredondarCentavos(novoPontoEquilibrio),
    novaFaltaFaturar: arredondarCentavos(novaFaltaFaturar),
    saldoAposSimulacao: arredondarCentavos(saldoAposSimulacao),
    vendasImpacto: calcularVendasImpacto(impactoPontoEquilibrio, ticketMedioAtual),
  };
}
