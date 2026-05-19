import assert from "node:assert/strict";
import { test } from "node:test";
import {
  ajustarVendaImposto,
  calcularAnaliseInteligenteVendas,
  calcularAnalisePromocoesFinanceiro,
  calcularDistribuicaoTemporalVendasFinanceiro,
  calcularFiltroRapidoPeriodoVendas,
  calcularResumoDiasPeriodoFinanceiro,
  calcularTotalizadoresListaVendasFinanceiro,
  calcularPeriodoComparacaoFinanceiro,
  calcularVariacaoFinanceira,
  calcularValorRecebidoVenda,
  consolidarFormasRecebimentoFinanceiro,
  dataKeyLocal,
  filtrarVendasRelatorio,
  filtrarDadosFinanceiroVendas,
  formatarDataVendaFinanceiro,
  getStatusVendaMeta,
  getTextoComparacaoPeriodo,
  montarFeriadosPeriodoFinanceiro,
  montarFeriadosPadrao,
  montarVendasPorDataCalendarioFinanceiro,
  normalizarFormaPagamentoLabel,
  ordenarVendasRelatorio,
  parseDataLocal,
  sanitizarNumero,
  vendaEstaEmAberto,
} from "./vendasFinanceiroUtils.js";

test("parseDataLocal preserva o dia local de strings ISO e yyyy-mm-dd", () => {
  assert.equal(dataKeyLocal("2026-05-19"), "2026-05-19");
  assert.equal(dataKeyLocal("2026-05-19T23:14:22-03:00"), "2026-05-19");
  assert.equal(parseDataLocal("invalida"), null);
});

test("normaliza formas de pagamento consolidadas", () => {
  assert.equal(normalizarFormaPagamentoLabel("pix"), "Pix");
  assert.equal(normalizarFormaPagamentoLabel("cartao_credito"), "Cartao Credito");
  assert.equal(normalizarFormaPagamentoLabel("5"), "Cartao Credito");
  assert.equal(normalizarFormaPagamentoLabel(""), "Nao informado");
});

test("consolida e filtra dados financeiros de vendas", () => {
  const formas = consolidarFormasRecebimentoFinanceiro([
    { forma_pagamento: "pix", valor_total: 10 },
    { forma_pagamento: "2", valor_total: 5 },
    { forma_pagamento: "dinheiro", valor_total: 7 },
  ]);

  assert.deepEqual(
    formas.map((item) => [item.forma_pagamento, item.valor_total]),
    [
      ["Pix", 15],
      ["Dinheiro", 7],
    ],
  );

  const dados = [
    { funcionario: "Ana", forma_pagamento: "Pix", categoria: "Racao" },
    { funcionario: "Bia", forma_pagamento: "Dinheiro", categoria: "Medicamento" },
  ];

  assert.deepEqual(
    filtrarDadosFinanceiroVendas(dados, "funcionario", { filtroFuncionario: "Bia" }),
    [dados[1]],
  );
  assert.deepEqual(
    filtrarDadosFinanceiroVendas(dados, "formaPagamento", { filtroFormaPagamento: "Pix" }),
    [dados[0]],
  );
  assert.deepEqual(
    filtrarDadosFinanceiroVendas(dados, "categoria", { filtroCategoria: "Medicamento" }),
    [dados[1]],
  );
  assert.deepEqual(filtrarDadosFinanceiroVendas(dados, "categoria", {}), dados);
});

test("identifica status de venda para filtros e badges", () => {
  assert.equal(vendaEstaEmAberto({ status: "baixa_parcial" }), true);
  assert.equal(vendaEstaEmAberto({ status: "finalizada" }), false);
  assert.deepEqual(getStatusVendaMeta("pago_nf"), { label: "Pago NF", intent: "success" });
  assert.deepEqual(getStatusVendaMeta("cancelada"), { label: "Cancelada", intent: "danger" });
});

test("monta feriados padrao com datas fixas e moveis", () => {
  const feriados = montarFeriadosPadrao([2026]);

  assert.equal(feriados["2026-01-01"], "Confraternização Universal");
  assert.equal(feriados["2026-02-16"], "Carnaval");
  assert.equal(feriados["2026-04-03"], "Sexta-feira Santa");
  assert.equal(feriados["2026-06-04"], "Corpus Christi");
});

test("monta calendario financeiro com feriados e resumo de dias uteis", () => {
  const feriados = montarFeriadosPeriodoFinanceiro({
    dataInicio: "2026-05-18",
    dataFim: "2026-05-24",
    feriadosCustomizados: [{ data: "2026-05-20", nome: "Feriado local" }],
  });

  assert.equal(feriados["2026-05-20"], "Feriado local");

  const calendario = montarVendasPorDataCalendarioFinanceiro({
    dataInicio: "2026-05-18",
    dataFim: "2026-05-24",
    vendasPorData: [
      {
        data: "2026-05-18",
        quantidade: 2,
        valor_bruto: 120,
        valor_liquido: 100,
        valor_recebido: 80,
        saldo_aberto: 20,
      },
      {
        data: "2026-05-20",
        quantidade: 1,
        valor_bruto: 60,
        valor_liquido: 50,
      },
      {
        data: "2026-05-23",
        quantidade: 1,
        valor_bruto: 40,
        valor_liquido: 40,
      },
    ],
    feriadosPorData: feriados,
    considerarSabadoDiaUtil: false,
  });

  assert.equal(calendario.length, 7);
  assert.deepEqual(
    calendario.map((dia) => ({
      data: dia.data,
      dia_util: dia.dia_util,
      fim_de_semana: dia.fim_de_semana,
      feriado_nome: dia.feriado_nome,
      feriado_aberto: dia.feriado_aberto,
      sem_movimento: dia.sem_movimento,
    })),
    [
      {
        data: "2026-05-18",
        dia_util: true,
        fim_de_semana: false,
        feriado_nome: "",
        feriado_aberto: false,
        sem_movimento: false,
      },
      {
        data: "2026-05-19",
        dia_util: true,
        fim_de_semana: false,
        feriado_nome: "",
        feriado_aberto: false,
        sem_movimento: true,
      },
      {
        data: "2026-05-20",
        dia_util: true,
        fim_de_semana: false,
        feriado_nome: "Feriado local",
        feriado_aberto: true,
        sem_movimento: false,
      },
      {
        data: "2026-05-21",
        dia_util: true,
        fim_de_semana: false,
        feriado_nome: "",
        feriado_aberto: false,
        sem_movimento: true,
      },
      {
        data: "2026-05-22",
        dia_util: true,
        fim_de_semana: false,
        feriado_nome: "",
        feriado_aberto: false,
        sem_movimento: true,
      },
      {
        data: "2026-05-23",
        dia_util: false,
        fim_de_semana: true,
        feriado_nome: "",
        feriado_aberto: false,
        sem_movimento: false,
      },
      {
        data: "2026-05-24",
        dia_util: false,
        fim_de_semana: true,
        feriado_nome: "",
        feriado_aberto: false,
        sem_movimento: true,
      },
    ],
  );

  assert.equal(calendario[0].ticket_medio, 60);
  assert.equal(calendario[2].dia_semana, "quarta-feira");

  assert.deepEqual(calcularResumoDiasPeriodoFinanceiro(calendario), {
    totalDias: 7,
    diasUteis: 5,
    diasTrabalhados: 2,
    diasUteisSemVenda: 3,
    finsDeSemana: 2,
    feriados: 1,
    mediaDiaUtil: 30,
    mediaDiaTrabalhado: 75,
  });

  const calendarioComSabadoUtil = montarVendasPorDataCalendarioFinanceiro({
    dataInicio: "2026-05-23",
    dataFim: "2026-05-23",
    vendasPorData: [],
    feriadosPorData: {},
    considerarSabadoDiaUtil: true,
  });
  assert.equal(calendarioComSabadoUtil[0].dia_util, true);
  assert.equal(calendarioComSabadoUtil[0].fim_de_semana, false);
});

test("ajustarVendaImposto remove imposto de venda sem nota e preserva venda fiscal", () => {
  const vendaSemNota = ajustarVendaImposto(
    {
      status: "finalizada",
      venda_bruta: 100,
      venda_liquida: 82,
      custo_produtos: 50,
      lucro: 32,
      imposto: 18,
      itens: [{ venda_bruta: 100, valor_liquido: 82, custo_total: 50, lucro: 32, imposto: 18 }],
    },
    false,
  );

  assert.equal(vendaSemNota.imposto_aplicado, false);
  assert.equal(vendaSemNota.imposto_original, 18);
  assert.equal(vendaSemNota.imposto, 0);
  assert.equal(vendaSemNota.venda_liquida, 100);
  assert.equal(vendaSemNota.lucro, 50);
  assert.equal(vendaSemNota.margem_sobre_venda, 50);
  assert.equal(vendaSemNota.itens[0].valor_liquido, 100);

  const vendaComNota = ajustarVendaImposto({ status: "pago_nf", imposto: 18 }, false);
  assert.equal(vendaComNota.imposto_aplicado, true);
  assert.equal(vendaComNota.imposto_original, 18);
});

test("calcula valor recebido visual conforme status da venda", () => {
  assert.equal(calcularValorRecebidoVenda({ valor_recebido: 12.5, status: "aberta" }), 12.5);
  assert.equal(calcularValorRecebidoVenda({ status: "finalizada", venda_bruta: 100 }), 100);
  assert.equal(calcularValorRecebidoVenda({ status: "aberta", venda_bruta: 100 }), 0);
});

test("formata datas e sanitiza numeros para os paineis financeiros", () => {
  assert.equal(formatarDataVendaFinanceiro("2026-05-19T23:14:22-03:00"), "19/05/2026");
  assert.equal(formatarDataVendaFinanceiro("invalida"), "N/A");
  assert.equal(sanitizarNumero(null), 0);
  assert.equal(sanitizarNumero(Number.POSITIVE_INFINITY), 0);
  assert.equal(sanitizarNumero("12.5"), "12.5");
});

test("filtra e ordena vendas para relatorio personalizado", () => {
  const vendas = [
    {
      id: 1,
      data_venda: "2026-05-18",
      funcionario_nome: "Ana",
      forma_pagamento: "Pix",
      categoria: "Racao",
      status: "finalizada",
      venda_bruta: 50,
      lucro: 12,
    },
    {
      id: 2,
      data_venda: "2026-05-19",
      funcionario: "Bia",
      pagamento_principal: "Cartao Credito",
      categoria: "Medicamento",
      status: "aberta",
      venda_bruta: 100,
      lucro: 30,
    },
  ];

  assert.deepEqual(
    filtrarVendasRelatorio(vendas, {
      escopo: "filtrado",
      filtroFuncionario: "Bia",
      filtroFormaPagamento: "Cartao Credito",
      filtroCategoria: "Medicamento",
      filtroStatusLista: "em_aberto",
    }).map((venda) => venda.id),
    [2],
  );

  assert.deepEqual(ordenarVendasRelatorio(vendas, "bruta_asc").map((venda) => venda.id), [1, 2]);
  assert.deepEqual(ordenarVendasRelatorio(vendas, "lucro_desc").map((venda) => venda.id), [2, 1]);
  assert.deepEqual(ordenarVendasRelatorio(vendas, "data_desc").map((venda) => venda.id), [2, 1]);
});

test("calcula totalizadores da lista de vendas financeiras", () => {
  const totalizadores = calcularTotalizadoresListaVendasFinanceiro([
    {
      status: "finalizada",
      nf_emitida: true,
      venda_bruta: 100,
      taxa_loja: 2,
      desconto: 5,
      taxa_entrega: 4,
      taxa_operacional: 1,
      taxa_cartao: 3,
      comissao: 6,
      imposto: 7,
      custo_campanha: 8,
      venda_liquida: 80,
      custo_produtos: 40,
      lucro: 20,
    },
    {
      status: "aberta",
      valor_recebido: 15,
      venda_bruta: 50,
      taxa_loja: 1,
      desconto: 2,
      taxa_entrega: 3,
      taxa_operacional: 4,
      taxa_cartao: 5,
      comissao: 6,
      imposto: 7,
      custo_campanha: 8,
      venda_liquida: 30,
      custo_produtos: 30,
      lucro: -10,
    },
  ]);

  assert.deepEqual(totalizadores, {
    quantidade: 2,
    venda_bruta: 150,
    taxa_loja: 3,
    desconto: 7,
    taxa_entrega: 7,
    taxa_operacional: 5,
    taxa_cartao: 8,
    comissao: 12,
    imposto: 14,
    custo_campanha: 16,
    venda_liquida: 110,
    valor_recebido: 115,
    custo_produtos: 70,
    lucro: 10,
    com_nf: 1,
    margem_sobre_venda: 6.7,
    margem_sobre_custo: 14.3,
  });
});

test("calcula analise financeira de promocoes", () => {
  const analise = calcularAnalisePromocoesFinanceiro([
    {
      tem_promocao: true,
      venda_liquida: 100,
      itens: [
        {
          produto_id: 1,
          produto_nome: "Defenza",
          em_promocao: true,
          quantidade: 2,
          valor_liquido: 60,
          desconto_promocional: 5,
          promocao_origem: "campanha, cupom",
        },
        {
          produto_id: 1,
          produto_nome: "Defenza",
          em_promocao: true,
          quantidade: 1,
          valor_promocional: 20,
          desconto_promocional: 2,
          promocao_origem: "campanha",
        },
      ],
    },
    {
      venda_bruta: 80,
      itens: [{ produto_nome: "Sem promocao", quantidade: 1, venda_bruta: 80 }],
    },
  ]);

  assert.equal(analise.totalVendas, 2);
  assert.equal(analise.vendasPromocao, 1);
  assert.equal(analise.vendasNormais, 1);
  assert.equal(analise.valorVendasPromocao, 100);
  assert.equal(analise.valorVendasNormais, 80);
  assert.equal(analise.valorItensPromocionais, 80);
  assert.equal(analise.descontoPromocional, 7);
  assert.equal(analise.percentualPromocao, 50);
  assert.deepEqual(analise.comparativo, [
    { tipo: "Normais", quantidade: 1, valor: 80 },
    { tipo: "Preco promocional", quantidade: 1, valor: 100 },
  ]);
  assert.deepEqual(analise.topProdutos, [
    {
      produto_nome: "Defenza",
      quantidade: 3,
      valor: 80,
      desconto: 7,
      origens: ["campanha", "cupom"],
    },
  ]);
});

test("calcula distribuicao temporal financeira por dia e horario", () => {
  const analise = calcularDistribuicaoTemporalVendasFinanceiro([
    {
      data_venda: "2026-05-18T09:15:00",
      venda_bruta: 100,
      venda_liquida: 80,
    },
    {
      data_venda: "2026-05-18T09:45:00",
      venda_bruta: 50,
      venda_liquida: 40,
    },
    {
      data_venda: "2026-05-19T15:30:00",
      venda_bruta: 200,
      venda_liquida: 150,
    },
    {
      data_venda: "data-invalida",
      venda_bruta: 999,
      venda_liquida: 999,
    },
  ]);

  assert.equal(analise.vendasPorDiaSemanaResumo.length, 7);
  assert.deepEqual(
    analise.vendasPorDiaSemanaResumo.map((dia) => dia.curto),
    ["Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"],
  );

  const segunda = analise.vendasPorDiaSemanaResumo[0];
  assert.equal(segunda.nome, "Segunda");
  assert.equal(segunda.quantidade, 2);
  assert.equal(segunda.valor_bruto, 150);
  assert.equal(segunda.valor_liquido, 120);
  assert.equal(segunda.ticket_medio, 60);

  const terca = analise.vendasPorDiaSemanaResumo[1];
  assert.equal(terca.quantidade, 1);
  assert.equal(terca.valor_liquido, 150);
  assert.equal(terca.ticket_medio, 150);

  assert.equal(analise.vendasPorHorarioResumo.length, 24);
  assert.deepEqual(
    analise.vendasPorHorarioComMovimento.map((hora) => ({
      faixa: hora.faixa,
      quantidade: hora.quantidade,
      valor_liquido: hora.valor_liquido,
      ticket_medio: hora.ticket_medio,
    })),
    [
      { faixa: "09h", quantidade: 2, valor_liquido: 120, ticket_medio: 60 },
      { faixa: "15h", quantidade: 1, valor_liquido: 150, ticket_medio: 150 },
    ],
  );
  assert.equal(analise.melhorDiaSemana.nome, "Terca");
  assert.equal(analise.melhorHorario.faixa, "15h");

  const vazio = calcularDistribuicaoTemporalVendasFinanceiro([]);
  assert.equal(vazio.melhorDiaSemana.nome, "Segunda");
  assert.equal(vazio.melhorHorario, undefined);
});

test("descreve periodo de comparacao financeiro", () => {
  assert.equal(getTextoComparacaoPeriodo("periodo_anterior"), "mesmo período anterior");
  assert.equal(getTextoComparacaoPeriodo("mes_anterior"), "mesmo período do mês anterior");
  assert.equal(getTextoComparacaoPeriodo("ano_anterior"), "mesmo período do ano anterior");
  assert.equal(getTextoComparacaoPeriodo("x"), "período anterior");
});

test("calcula intervalo comparativo preservando datas locais", () => {
  assert.deepEqual(
    calcularPeriodoComparacaoFinanceiro({
      dataInicio: "2026-05-10",
      dataFim: "2026-05-19",
      periodoComparacao: "periodo_anterior",
    }),
    { data_inicio: "2026-04-30", data_fim: "2026-05-09" },
  );

  assert.deepEqual(
    calcularPeriodoComparacaoFinanceiro({
      dataInicio: "2026-05-10",
      dataFim: "2026-05-19",
      periodoComparacao: "mes_anterior",
    }),
    { data_inicio: "2026-04-10", data_fim: "2026-04-19" },
  );

  assert.deepEqual(
    calcularPeriodoComparacaoFinanceiro({
      dataInicio: "2026-05-10",
      dataFim: "2026-05-19",
      periodoComparacao: "ano_anterior",
    }),
    { data_inicio: "2025-05-10", data_fim: "2025-05-19" },
  );

  assert.deepEqual(
    calcularPeriodoComparacaoFinanceiro({
      dataInicio: "2026-05-10",
      dataFim: "2026-05-19",
      periodoComparacao: "desconhecido",
    }),
    { data_inicio: "", data_fim: "" },
  );
});

test("calcula periodos dos filtros rapidos de vendas", () => {
  const baseDate = "2026-05-19";

  assert.deepEqual(calcularFiltroRapidoPeriodoVendas("hoje", baseDate), {
    inicio: "2026-05-19",
    fim: "2026-05-19",
  });
  assert.deepEqual(calcularFiltroRapidoPeriodoVendas("ontem", baseDate), {
    inicio: "2026-05-18",
    fim: "2026-05-18",
  });
  assert.deepEqual(calcularFiltroRapidoPeriodoVendas("esta_semana", baseDate), {
    inicio: "2026-05-18",
    fim: "2026-05-19",
  });
  assert.deepEqual(calcularFiltroRapidoPeriodoVendas("este_mes", baseDate), {
    inicio: "2026-05-01",
    fim: "2026-05-19",
  });
  assert.deepEqual(calcularFiltroRapidoPeriodoVendas("mes_anterior", baseDate), {
    inicio: "2026-04-01",
    fim: "2026-04-30",
  });
  assert.deepEqual(calcularFiltroRapidoPeriodoVendas("ultimos_7_dias", baseDate), {
    inicio: "2026-05-12",
    fim: "2026-05-19",
  });
  assert.deepEqual(calcularFiltroRapidoPeriodoVendas("ultimos_30_dias", baseDate), {
    inicio: "2026-04-19",
    fim: "2026-05-19",
  });
  assert.deepEqual(calcularFiltroRapidoPeriodoVendas("este_ano", baseDate), {
    inicio: "2026-01-01",
    fim: "2026-05-19",
  });
  assert.equal(calcularFiltroRapidoPeriodoVendas("desconhecido", baseDate), null);
});

test("calcula variacao financeira com percentual arredondado", () => {
  assert.deepEqual(calcularVariacaoFinanceira(150, 100), { valor: 50, percentual: 50 });
  assert.deepEqual(calcularVariacaoFinanceira(80, 100), { valor: -20, percentual: -20 });
  assert.deepEqual(calcularVariacaoFinanceira(10, 3), {
    valor: 7,
    percentual: 233.3,
  });
  assert.deepEqual(calcularVariacaoFinanceira(100, 0), { valor: 0, percentual: 0 });
});

test("calcula analise inteligente de produtos e alertas de vendas", () => {
  const produtosAnalise = [
    {
      nome: "Produto alta margem",
      marca: "Marca A",
      quantidade: 2,
      custo_total: 50,
      valor_total: 100,
      categoria: "Racao",
    },
    ...Array.from({ length: 5 }, (_, indice) => ({
      nome: `Produto baixa margem ${indice + 1}`,
      quantidade: 1,
      custo_total: 90,
      valor_total: 100,
      categoria: "Medicamentos",
    })),
  ];

  const analise = calcularAnaliseInteligenteVendas({
    produtosAnalise,
    resumo: { quantidade_vendas: 8, venda_liquida: 1000, em_aberto: 250 },
    resumoComparacao: { quantidade_vendas: 10 },
    vendasPorData: [{ valor_liquido: 100 }, { valor_liquido: 200 }],
  });

  assert.equal(analise.produtosMaisLucrativos[0].nome, "Produto alta margem");
  assert.equal(analise.produtosMaisLucrativos[0].lucro_total, 50);
  assert.equal(analise.produtosPorCategoria.Racao.quantidade, 2);
  assert.equal(analise.produtosPorCategoria.Racao.total, 100);
  assert.equal(analise.produtosPorCategoria.Racao.margem_media, 100);
  assert.equal(analise.previsaoProximos7Dias, 1050);
  assert.deepEqual(
    analise.alertasInteligentesVendas.map((alerta) => alerta.id),
    [
      "queda-vendas",
      "recebiveis-abertos",
      "mix-baixa-margem",
      "oportunidade-upsell",
    ],
  );

  assert.deepEqual(calcularAnaliseInteligenteVendas({ produtosAnalise: [] }), {
    produtosMaisLucrativos: [],
    produtosPorCategoria: {},
    alertasInteligentesVendas: [],
    previsaoProximos7Dias: 0,
  });
});
