import { compararRacoesPorPrecoKg, obterResumoPrecoPorKg } from "./racaoPrecoKg.js";

export function racaoPodeCompararPreco(racao) {
  return obterResumoPrecoPorKg(racao).disponivel;
}

export function normalizarRacaoComparador(racao) {
  const resumo = obterResumoPrecoPorKg(racao);

  if (!resumo.disponivel) {
    return null;
  }

  return {
    ...resumo,
    original: racao,
  };
}

export function montarComparativoManualRacoes(racaoA, racaoB) {
  const resumos = [racaoA, racaoB].map(normalizarRacaoComparador).filter(Boolean);
  const itens = compararRacoesPorPrecoKg([racaoA, racaoB]);

  if (resumos.length < 2 || itens.length < 2) {
    return {
      pronto: false,
      motivo: "Selecione duas racoes com peso e preco de venda para comparar.",
      itens,
      melhor: itens[0] || null,
      pior: itens[1] || null,
      diferencaPorKg: 0,
      diferencaPorKgFormatada: "",
    };
  }

  const melhor = itens[0];
  const pior = itens[itens.length - 1];

  return {
    pronto: true,
    motivo: "",
    itens,
    melhor,
    pior,
    diferencaPorKg: pior.diferencaMelhor,
    diferencaPorKgFormatada: pior.diferencaMelhorFormatada,
  };
}
