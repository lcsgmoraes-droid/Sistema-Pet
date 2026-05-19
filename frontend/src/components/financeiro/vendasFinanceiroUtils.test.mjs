import assert from "node:assert/strict";
import { test } from "node:test";
import {
  ajustarVendaImposto,
  calcularAnaliseInteligenteVendas,
  calcularFiltroRapidoPeriodoVendas,
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
  montarFeriadosPadrao,
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
