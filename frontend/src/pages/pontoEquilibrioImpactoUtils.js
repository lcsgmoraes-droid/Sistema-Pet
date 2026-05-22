function numeroSeguro(valor) {
  const numero = Number(valor);
  return Number.isFinite(numero) ? numero : 0;
}

function numeroOuPadrao(valor, padrao) {
  if (valor === "" || valor == null) return padrao;
  const numero = Number(valor);
  return Number.isFinite(numero) ? numero : padrao;
}

function arredondarCentavos(valor) {
  return Math.round((valor + Number.EPSILON) * 100) / 100;
}

function arredondarPercentual(valor) {
  return Math.round((valor + Number.EPSILON) * 100) / 100;
}

function normalizarTexto(texto) {
  return String(texto || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function calcularVendasImpacto(impactoPontoEquilibrio, ticketMedio) {
  if (!Number.isFinite(ticketMedio) || ticketMedio <= 0) return null;
  if (!Number.isFinite(impactoPontoEquilibrio) || impactoPontoEquilibrio === 0) return 0;

  const vendas = Math.ceil(Math.abs(impactoPontoEquilibrio) / ticketMedio);
  return impactoPontoEquilibrio > 0 ? vendas : -vendas;
}

const GRUPOS_CUSTOS_FIXOS = [
  {
    id: "aluguel",
    label: "Aluguel",
    termos: ["aluguel", "locacao", "imovel", "condominio", "ocupacao"],
  },
  {
    id: "folha",
    label: "Folha e pro-labore",
    termos: [
      "salario",
      "salarios",
      "folha",
      "pro labore",
      "pro-labore",
      "funcionario",
      "funcionarios",
      "encargo",
      "inss",
      "fgts",
      "ferias",
      "decimo",
    ],
  },
  {
    id: "utilidades",
    label: "Energia, agua e utilidades",
    termos: ["energia", "eletric", "agua", "sabesp", "luz", "gas", "utilidade"],
  },
  {
    id: "tecnologia",
    label: "Internet, telefone e sistemas",
    termos: ["internet", "telefone", "sistema", "software", "assinatura", "mensalidade"],
  },
  {
    id: "administrativo",
    label: "Escritorio e administrativo",
    termos: ["escritorio", "administrativo", "contabilidade", "contador", "material de uso interno", "limpeza"],
  },
  {
    id: "impacto_simulado",
    label: "Impacto simulado",
    termos: ["impacto simulado"],
  },
  {
    id: "outros",
    label: "Outros custos fixos",
    termos: [],
  },
];

const REFERENCIAS_GERENCIAIS = {
  aluguel: {
    titulo: "Aluguel sobre faturamento",
    referenciaPercentual: 13,
    limiteAtencaoPercentual: 15,
    descricao: "Referencia gerencial para ocupacao em varejo/servicos.",
  },
  folha: {
    titulo: "Folha e pro-labore",
    referenciaPercentual: 28,
    limiteAtencaoPercentual: 35,
    descricao: "Inclui salarios, encargos, pro-labore e complemento gerencial.",
  },
  utilidades: {
    titulo: "Energia, agua e utilidades",
    referenciaPercentual: 5,
    limiteAtencaoPercentual: 7,
    descricao: "Contas recorrentes que tendem a variar com operacao e consumo.",
  },
  tecnologia: {
    titulo: "Internet, telefone e sistemas",
    referenciaPercentual: 4,
    limiteAtencaoPercentual: 6,
    descricao: "Infraestrutura digital e assinaturas operacionais.",
  },
  administrativo: {
    titulo: "Escritorio e administrativo",
    referenciaPercentual: 6,
    limiteAtencaoPercentual: 8,
    descricao: "Custos de apoio e administracao da loja.",
  },
  total_fixo: {
    titulo: "Custo fixo total",
    referenciaPercentual: 30,
    limiteAtencaoPercentual: 35,
    descricao: "Quanto menor, mais folga a margem tem para gerar lucro.",
  },
};

function textoItemCusto(item) {
  return normalizarTexto([
    item?.descricao,
    item?.origem_classificacao,
    item?.tipo_despesa_nome,
    item?.categoria_nome,
    item?.dre_subcategoria_nome,
  ].filter(Boolean).join(" "));
}

function classificarGrupoCusto(item) {
  const texto = textoItemCusto(item);
  const grupo = GRUPOS_CUSTOS_FIXOS.find((opcao) =>
    opcao.termos.some((termo) => texto.includes(termo))
  );
  return grupo?.id || "outros";
}

function criarMapaGrupos() {
  return GRUPOS_CUSTOS_FIXOS.reduce((acc, grupo) => {
    acc[grupo.id] = {
      id: grupo.id,
      label: grupo.label,
      valor: 0,
      itens: [],
    };
    return acc;
  }, {});
}

function criarParecer({ id, valor, faturamento, referencia }) {
  const valorSeguro = Math.max(0, numeroSeguro(valor));
  const faturamentoSeguro = Math.max(0, numeroSeguro(faturamento));
  const percentualFaturamento = faturamentoSeguro > 0
    ? (valorSeguro / faturamentoSeguro) * 100
    : 0;
  const valorIdeal = faturamentoSeguro * (referencia.referenciaPercentual / 100);
  const diferencaValor = valorSeguro - valorIdeal;
  const diferencaPercentual = percentualFaturamento - referencia.referenciaPercentual;
  const status = percentualFaturamento <= referencia.referenciaPercentual
    ? "saudavel"
    : percentualFaturamento <= referencia.limiteAtencaoPercentual
      ? "atencao"
      : "acima";

  return {
    id,
    titulo: referencia.titulo,
    descricao: referencia.descricao,
    valor: arredondarCentavos(valorSeguro),
    percentualFaturamento: arredondarPercentual(percentualFaturamento),
    referenciaPercentual: referencia.referenciaPercentual,
    limiteAtencaoPercentual: referencia.limiteAtencaoPercentual,
    diferencaPercentual: arredondarPercentual(diferencaPercentual),
    diferencaValor: arredondarCentavos(diferencaValor),
    status,
  };
}

export function calcularImpactoPontoEquilibrio({
  despesasFixas,
  pontoEquilibrio,
  margemContribuicaoPercentual,
  faturamento,
  faturamentoProjetado,
  ticketMedio,
  impactoCustoFixo,
}) {
  const despesasFixasAtuais = numeroSeguro(despesasFixas);
  const margemPercentual = numeroSeguro(margemContribuicaoPercentual);
  const margemDecimal = margemPercentual / 100;
  const faturamentoAtual = numeroSeguro(faturamento);
  const faturamentoDaSimulacao = Math.max(0, numeroOuPadrao(faturamentoProjetado, faturamentoAtual));
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
      faturamentoProjetado: arredondarCentavos(faturamentoDaSimulacao),
      margemContribuicaoProjetada: null,
      resultadoProjetado: null,
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
  const margemContribuicaoProjetada = faturamentoDaSimulacao * margemDecimal;
  const resultadoProjetado = margemContribuicaoProjetada - novoCustoFixo;
  const novaFaltaFaturar = Math.max(0, novoPontoEquilibrio - faturamentoDaSimulacao);
  const saldoAposSimulacao = faturamentoDaSimulacao - novoPontoEquilibrio;

  return {
    calculavel: true,
    novoCustoFixo: arredondarCentavos(novoCustoFixo),
    impactoRealCustoFixo: arredondarCentavos(impactoRealCustoFixo),
    impactoPontoEquilibrio: arredondarCentavos(impactoPontoEquilibrio),
    novoPontoEquilibrio: arredondarCentavos(novoPontoEquilibrio),
    faturamentoProjetado: arredondarCentavos(faturamentoDaSimulacao),
    margemContribuicaoProjetada: arredondarCentavos(margemContribuicaoProjetada),
    resultadoProjetado: arredondarCentavos(resultadoProjetado),
    novaFaltaFaturar: arredondarCentavos(novaFaltaFaturar),
    saldoAposSimulacao: arredondarCentavos(saldoAposSimulacao),
    vendasImpacto: calcularVendasImpacto(impactoPontoEquilibrio, ticketMedioAtual),
  };
}

export function montarAnaliseCustosPontoEquilibrio({
  dados,
  faturamentoProjetado,
  impactoCustoFixo = 0,
  impactoDescricao = "",
}) {
  const faturamentoBase = numeroOuPadrao(faturamentoProjetado, dados?.faturamento || 0);
  const faturamentoSeguro = Math.max(0, faturamentoBase);
  const impacto = numeroSeguro(impactoCustoFixo);
  const gruposMapa = criarMapaGrupos();
  const fixas = dados?.detalhes_classificacao?.fixas || [];

  fixas.forEach((item) => {
    const grupoId = classificarGrupoCusto(item);
    const grupo = gruposMapa[grupoId] || gruposMapa.outros;
    const valor = Math.max(0, numeroSeguro(item?.valor));
    grupo.valor += valor;
    grupo.itens.push(item);
  });

  if (impacto !== 0) {
    const grupoId = impactoDescricao
      ? classificarGrupoCusto({ descricao: impactoDescricao })
      : "impacto_simulado";
    const grupo = gruposMapa[grupoId] || gruposMapa.impacto_simulado;
    grupo.valor = Math.max(0, grupo.valor + impacto);
    grupo.itens.push({
      id: "impacto-simulado",
      descricao: impactoDescricao || "Impacto simulado",
      valor: impacto,
      origem_classificacao: "Simulador",
    });
  }

  const grupos = Object.values(gruposMapa)
    .map((grupo) => ({
      ...grupo,
      valor: arredondarCentavos(grupo.valor),
      percentualFaturamento: faturamentoSeguro > 0
        ? arredondarPercentual((grupo.valor / faturamentoSeguro) * 100)
        : 0,
    }))
    .filter((grupo) => grupo.valor > 0)
    .sort((a, b) => b.valor - a.valor);

  const valorGrupo = (id) => gruposMapa[id]?.valor || 0;
  const custoFixoProjetado = Math.max(0, numeroSeguro(dados?.despesas_fixas) + impacto);
  const pareceres = [
    criarParecer({
      id: "aluguel",
      valor: valorGrupo("aluguel"),
      faturamento: faturamentoSeguro,
      referencia: REFERENCIAS_GERENCIAIS.aluguel,
    }),
    criarParecer({
      id: "folha",
      valor: valorGrupo("folha"),
      faturamento: faturamentoSeguro,
      referencia: REFERENCIAS_GERENCIAIS.folha,
    }),
    criarParecer({
      id: "utilidades",
      valor: valorGrupo("utilidades"),
      faturamento: faturamentoSeguro,
      referencia: REFERENCIAS_GERENCIAIS.utilidades,
    }),
    criarParecer({
      id: "tecnologia",
      valor: valorGrupo("tecnologia"),
      faturamento: faturamentoSeguro,
      referencia: REFERENCIAS_GERENCIAIS.tecnologia,
    }),
    criarParecer({
      id: "administrativo",
      valor: valorGrupo("administrativo"),
      faturamento: faturamentoSeguro,
      referencia: REFERENCIAS_GERENCIAIS.administrativo,
    }),
    criarParecer({
      id: "total_fixo",
      valor: custoFixoProjetado,
      faturamento: faturamentoSeguro,
      referencia: REFERENCIAS_GERENCIAIS.total_fixo,
    }),
  ];

  return {
    faturamento: arredondarCentavos(faturamentoSeguro),
    custoFixoProjetado: arredondarCentavos(custoFixoProjetado),
    grupos,
    pareceres,
    comparativoPercentual: pareceres.map((item) => ({
      nome: item.titulo,
      atual: item.percentualFaturamento,
      referencia: item.referenciaPercentual,
    })),
  };
}
