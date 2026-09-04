export const MARGENS_PRECO_PADRAO = [30, 34];

const numeroValido = (valor) => {
  const numero = Number(valor);
  return Number.isFinite(numero) ? numero : null;
};

export function calcularMargemSobreVenda(precoCusto, precoVenda) {
  const custo = numeroValido(precoCusto);
  const venda = numeroValido(precoVenda);

  if (custo === null || venda === null || custo <= 0 || venda <= 0) {
    return null;
  }

  return ((venda - custo) / venda) * 100;
}

export function calcularPrecoVendaPorMargem(precoCusto, margemPercentual) {
  const custo = numeroValido(precoCusto);
  const margem = numeroValido(margemPercentual);

  if (custo === null || margem === null || custo <= 0 || margem >= 100) {
    return null;
  }

  return custo / (1 - margem / 100);
}

export function normalizarMargensPreco(config = {}) {
  const valores = [config.margem_preco_sugestao_1, config.margem_preco_sugestao_2];

  return valores.map((valor, indice) => {
    const numero = numeroValido(valor);
    if (numero === null || numero < 0 || numero >= 100) {
      return MARGENS_PRECO_PADRAO[indice];
    }
    return Math.round(numero * 100) / 100;
  });
}

export function formatarDivisorMargem(margemPercentual) {
  const margem = numeroValido(margemPercentual) ?? 0;
  return (1 - margem / 100).toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  });
}
