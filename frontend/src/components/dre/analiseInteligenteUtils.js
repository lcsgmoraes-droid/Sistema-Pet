const numero = (valor) => {
  const resultado = Number(valor);
  return Number.isFinite(resultado) ? resultado : 0;
};

export function extrairIndicadoresDRE(dados) {
  const totais = dados?.totais || {};
  const despesasAdmin = (dados?.linhas || [])
    .filter((linha) => linha.campo === "despesas_administrativas")
    .reduce((soma, linha) => soma + numero(linha.valor), 0);

  return {
    receitaBruta: numero(totais.receita_bruta),
    receitaLiquida: numero(totais.receita_liquida),
    cmv: numero(totais.cmv),
    custosDiretos: numero(totais.custos_diretos),
    lucroBruto: numero(totais.lucro_bruto),
    despesasOperacionais: numero(totais.despesas_operacionais),
    despesasAdmin,
    lucroLiquido: numero(totais.lucro_liquido),
    margemBruta: numero(totais.margem_bruta),
    margemLiquida: numero(totais.margem_liquida),
  };
}

export function obterParametrosMesAnterior(parametrosDRE) {
  const ano = Number(parametrosDRE?.ano);
  const mes = Number(parametrosDRE?.mes);
  const mesInicial = parametrosDRE?.mes_inicial;

  if (
    !Number.isInteger(ano) ||
    !Number.isInteger(mes) ||
    mes < 1 ||
    mes > 12 ||
    parametrosDRE?.data_final ||
    (mesInicial != null && Number(mesInicial) !== mes)
  ) {
    return null;
  }

  return {
    ano: mes === 1 ? ano - 1 : ano,
    mes: mes === 1 ? 12 : mes - 1,
    canais: parametrosDRE.canais,
  };
}

export function dadosCorrespondemParametrosDRE(dados, parametrosDRE) {
  if (!dados?.totais || !parametrosDRE) return false;

  const canais = parametrosDRE.canais?.split(",").filter(Boolean) || [];
  const canaisEsperados = canais.length ? canais : ["loja_fisica"];
  const canaisEncontrados = dados.canais_encontrados || [];

  return (
    Number(dados.ano) === Number(parametrosDRE.ano) &&
    Number(dados.mes) === Number(parametrosDRE.mes) &&
    Number(dados.mes_inicial) === Number(parametrosDRE.mes_inicial || parametrosDRE.mes) &&
    (dados.data_final || null) === (parametrosDRE.data_final || null) &&
    canaisEncontrados.length === canaisEsperados.length &&
    canaisEsperados.every((canal) => canaisEncontrados.includes(canal))
  );
}

export function compararPeriodosDRE(atual, anterior) {
  const indicadoresAtuais = extrairIndicadoresDRE(atual);
  const indicadoresAnteriores = extrairIndicadoresDRE(anterior);
  const variacao = (valorAtual, valorAnterior) =>
    valorAnterior === 0 ? null : ((valorAtual - valorAnterior) / Math.abs(valorAnterior)) * 100;
  const comparar = (campo) => ({
    atual: indicadoresAtuais[campo],
    anterior: indicadoresAnteriores[campo],
    variacao: variacao(indicadoresAtuais[campo], indicadoresAnteriores[campo]),
  });

  return {
    receita: comparar("receitaBruta"),
    lucro: comparar("lucroLiquido"),
    despesas: comparar("despesasOperacionais"),
    margem: {
      atual: indicadoresAtuais.margemLiquida,
      anterior: indicadoresAnteriores.margemLiquida,
      variacao: indicadoresAtuais.margemLiquida - indicadoresAnteriores.margemLiquida,
    },
  };
}
