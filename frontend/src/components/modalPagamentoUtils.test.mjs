import assert from "node:assert/strict";
import { test } from "node:test";
import {
  BANDEIRAS_CARTAO,
  calcularBeneficiosCampanhaPreview,
  calcularFaixasParcelamento,
  calcularCustoTotalItensVenda,
  calcularResumoRecebimento,
  dataCrediarioParaIso,
  devePerguntarNotaFiscal,
  descreverCupomMargem,
  ehFormaPagamentoPix,
  ehFormaPagamentoCartao,
  ehFormaPagamentoStonePos,
  avaliarEstadoJustificativaMargem,
  extrairCorIndicadorMargem,
  gerarPlanoCrediario,
  identificarIconeFormaPagamento,
  mapearTipoPagamentoStonePos,
  montarCupomParaFinalizar,
  montarFormasPagamentoAnalise,
  montarItensParaVerificarEstoqueNegativo,
  montarMensagemEstoqueNegativo,
  montarItensAnaliseMargem,
  montarFallbackSimulacaoParcelamento,
  montarPagamentoAVista,
  montarPagamentoRecebido,
  montarPagamentoSimuladoParcelamento,
  montarPagamentosMargem,
  montarPayloadAnaliseMargem,
  montarVendaParaPersistirComCupom,
  montarObservacoesComJustificativaMargem,
  mascararDataCrediario,
  normalizarResultadoSimulacaoParcelamento,
  normalizarBandeiraCartao,
  obterBandeiraPadraoPdv,
  obterBandeirasDisponiveis,
  obterCorVisualParcelamento,
  obterEstiloVisualParcelamento,
  obterCorParcelamentoAtual,
  obterModalidadeCartao,
  obterParcelasDisponiveis,
  obterParcelasPermitidasParaForma,
  obterTaxaCartaoSelecionada,
  podeEnviarPagamentoStonePos,
  persistirVendaAbertaParaPagamento,
  resolverFaixasParcelamentoDaForma,
  validarPagamentoParaAdicionar,
} from "./modalPagamentoUtils.js";

test("identifica icone da forma de pagamento por icone ou nome", () => {
  assert.equal(identificarIconeFormaPagamento("pix", "Pix"), "qr_code");
  assert.equal(identificarIconeFormaPagamento("", "Dinheiro"), "banknote");
  assert.equal(identificarIconeFormaPagamento("", "Cartao de debito"), "credit_card");
  assert.equal(identificarIconeFormaPagamento("", "Crédito parcelado"), "credit_card");
  assert.equal(identificarIconeFormaPagamento("", "Transferencia bancaria"), "transfer");
  assert.equal(identificarIconeFormaPagamento("", "Boleto"), "receipt");
  assert.equal(identificarIconeFormaPagamento("", "Carteira digital"), "wallet");
  assert.equal(identificarIconeFormaPagamento("", "Outro"), "credit_card");
});

test("mantem lista padrao de bandeiras de cartao", () => {
  assert.deepEqual(BANDEIRAS_CARTAO, [
    "Visa",
    "Mastercard",
    "Elo",
    "American Express",
    "Hipercard",
    "Hiper",
    "Cabal",
    "Diners Club",
    "Discover",
    "UnionPay",
    "Outros",
  ]);
});

test("resolve bandeiras e parcelas pela matriz de taxas da operadora", () => {
  const taxas = [
    { id: 1, bandeira: "visa", modalidade: "credito", parcelas: 1, taxa_percentual: 2 },
    { id: 2, bandeira: "visa", modalidade: "credito", parcelas: 3, taxa_percentual: 3 },
    { id: 3, bandeira: "mastercard", modalidade: "credito", parcelas: 1 },
    { id: 4, bandeira: "outros", modalidade: "credito", parcelas: 2 },
    { id: 5, bandeira: "visa", modalidade: "debito", parcelas: 1 },
  ];

  assert.equal(normalizarBandeiraCartao("American Express"), "amex");
  assert.equal(normalizarBandeiraCartao("Diners Club"), "diners");
  assert.equal(normalizarBandeiraCartao("Union Pay"), "unionpay");
  assert.equal(obterModalidadeCartao({ tipo: "cartao_credito" }), "credito");
  assert.equal(ehFormaPagamentoCartao({ tipo: "cartao_debito" }), true);
  assert.deepEqual(obterBandeirasDisponiveis({ taxas, modalidade: "credito" }), [
    "Visa",
    "Mastercard",
  ]);
  assert.deepEqual(obterBandeirasDisponiveis({ taxas, modalidade: "voucher" }), []);
  assert.deepEqual(
    obterParcelasDisponiveis({
      taxas,
      modalidade: "credito",
      bandeira: "Visa",
      maxParcelas: 12,
    }),
    [1, 2, 3],
  );
  assert.equal(
    obterBandeiraPadraoPdv({
      operadora: { bandeira_padrao: "mastercard" },
      bandeiras: ["Visa", "Mastercard"],
    }),
    "Mastercard",
  );
  assert.equal(
    obterTaxaCartaoSelecionada({
      taxas,
      modalidade: "credito",
      bandeira: "Visa",
      parcelas: 1,
    }).id,
    1,
  );
});

test("crediario oferece de uma a sessenta parcelas sem herdar o limite cadastral antigo", () => {
  const parcelas = obterParcelasPermitidasParaForma({
    tipo: "crediario",
    parcelas_maximas: 1,
  });

  assert.equal(parcelas.length, 60);
  assert.deepEqual(parcelas.slice(0, 3), [1, 2, 3]);
  assert.equal(parcelas.at(-1), 60);
});

test("calcula dados auxiliares da venda sem depender do modal", () => {
  assert.equal(ehFormaPagamentoPix({ nome: "Pix QR Code" }), true);
  assert.equal(ehFormaPagamentoPix({ nome: "Cartao de credito" }), false);

  assert.equal(
    calcularCustoTotalItensVenda([
      { custo: 10, quantidade: 2 },
      { custo: 4.5, quantidade: 3 },
      { custo: 99, quantidade: 0 },
    ]),
    132.5,
  );

  const venda = { id: 10, total: 100, desconto_valor: 5 };
  assert.equal(montarVendaParaPersistirComCupom({ venda, cupomParaFinalizar: null }), venda);
  assert.deepEqual(
    montarVendaParaPersistirComCupom({
      venda,
      cupomParaFinalizar: {
        code: "recompra10",
        discount_applied: 7,
      },
    }),
    {
      id: 10,
      total: 100,
      desconto_valor: 5,
      cupom_code: "recompra10",
      cupom_discount_applied: 7,
    },
  );

  assert.equal(devePerguntarNotaFiscal({ status: "finalizada" }), true);
  assert.equal(devePerguntarNotaFiscal({ status: "pago_nf" }), true);
  assert.equal(devePerguntarNotaFiscal({ status: "aberta" }), false);
});

test("bloqueia envio para Stone POS porque a integracao foi descontinuada", () => {
  assert.equal(ehFormaPagamentoStonePos({ tipo: "cartao_credito" }), false);
  assert.equal(ehFormaPagamentoStonePos({ tipo: "cartao_debito" }), false);
  assert.equal(ehFormaPagamentoStonePos({ nome: "Pix" }), false);
  assert.equal(ehFormaPagamentoStonePos({ tipo: "dinheiro" }), false);

  assert.equal(mapearTipoPagamentoStonePos({ tipo: "cartao_credito" }), null);
  assert.equal(mapearTipoPagamentoStonePos({ tipo: "cartao_debito" }), null);
  assert.equal(mapearTipoPagamentoStonePos({ nome: "Pix QR Code" }), null);
});

test("nao libera Stone POS mesmo para venda sem pagamentos manuais", () => {
  const forma = { tipo: "cartao_credito" };
  assert.deepEqual(
    podeEnviarPagamentoStonePos({
      formaPagamento: forma,
      pagamentos: [],
      totalPagoExistente: 0,
      valorRestante: 100,
      stonePedidoPendente: false,
    }),
    {
      podeEnviar: false,
      motivo: "Integracao Stone POS descontinuada.",
    },
  );
  assert.deepEqual(
    podeEnviarPagamentoStonePos({
      formaPagamento: forma,
      pagamentos: [{ valor: 10 }],
      totalPagoExistente: 0,
      valorRestante: 90,
      stonePedidoPendente: false,
    }),
    {
      podeEnviar: false,
      motivo: "Integracao Stone POS descontinuada.",
    },
  );
});

test("extrai cor de margem do retorno do backend", () => {
  assert.equal(extrairCorIndicadorMargem({ resultado: { cor_indicador: "vermelho" } }), "vermelho");
  assert.equal(extrairCorIndicadorMargem({ resultado: {} }), null);
  assert.equal(extrairCorIndicadorMargem(null), null);
});

test("obtem cor do parcelamento atual com fallback seguro", () => {
  const simulacoes = {
    12: {
      1: { cor: "verde" },
      2: { cor: "amarelo" },
      3: {},
    },
  };

  assert.equal(
    obterCorParcelamentoAtual({
      formaPagamento: { id: 12, permite_parcelamento: true },
      simulacoesParcelamento: simulacoes,
      numeroParcelas: 2,
    }),
    "amarelo",
  );
  assert.equal(
    obterCorParcelamentoAtual({
      formaPagamento: { id: 12, permite_parcelamento: true },
      simulacoesParcelamento: simulacoes,
      numeroParcelas: 3,
    }),
    "verde",
  );
  assert.equal(
    obterCorParcelamentoAtual({
      formaPagamento: { id: 12, permite_parcelamento: false },
      simulacoesParcelamento: simulacoes,
      numeroParcelas: 2,
    }),
    "verde",
  );
});

test("resolve estilo visual de parcelamento por cor", () => {
  assert.equal(
    obterCorVisualParcelamento({
      formaPagamento: { id: 12 },
      simulacoesParcelamento: { 12: { 3: { cor: "vermelho" } } },
      numeroParcelas: 3,
      statusMargem: "amarelo",
    }),
    "vermelho",
  );
  assert.equal(
    obterCorVisualParcelamento({
      formaPagamento: { id: 12 },
      simulacoesParcelamento: {},
      numeroParcelas: 3,
      statusMargem: "amarelo",
    }),
    "amarelo",
  );

  assert.deepEqual(obterEstiloVisualParcelamento("verde"), {
    selectClass: "border-gray-300 bg-white",
    painelClass: "bg-blue-50 border-blue-200",
    tituloClass: "text-blue-800",
    descricaoClass: "text-blue-600",
    optionClass: "",
    prefixo: "",
    aviso: "",
  });

  assert.deepEqual(obterEstiloVisualParcelamento("vermelho"), {
    selectClass: "border-red-400 bg-red-50 text-red-900",
    painelClass: "bg-red-50 border-red-300",
    tituloClass: "text-red-800",
    descricaoClass: "text-red-700",
    optionClass: "bg-red-100 text-red-900",
    prefixo: "\uD83D\uDEAB ",
    aviso: " - Requer justificativa",
  });
});

test("avalia quando margem exige justificativa ou campo visivel", () => {
  assert.deepEqual(
    avaliarEstadoJustificativaMargem({
      statusMargem: "vermelho",
      corParcelamentoAtual: "verde",
      justificativaTexto: "",
    }),
    { margemCriticaAtual: true, mostrarCampoJustificativa: true },
  );

  assert.deepEqual(
    avaliarEstadoJustificativaMargem({
      statusMargem: "verde",
      corParcelamentoAtual: "vermelho",
      justificativaTexto: "",
    }),
    { margemCriticaAtual: true, mostrarCampoJustificativa: true },
  );

  assert.deepEqual(
    avaliarEstadoJustificativaMargem({
      statusMargem: "verde",
      corParcelamentoAtual: "verde",
      justificativaTexto: "ajuste aprovado",
    }),
    { margemCriticaAtual: false, mostrarCampoJustificativa: true },
  );
});

test("calcula faixas quando ha parcelas saudaveis, alerta e criticas", () => {
  const faixas = calcularFaixasParcelamento(
    {
      1: { cor: "verde" },
      2: { cor: "verde" },
      3: { cor: "amarelo" },
      4: { cor: "vermelho" },
      5: { cor: "vermelho" },
    },
    5,
  );

  assert.deepEqual(faixas, {
    saudavel: { min: 1, max: 2 },
    alerta: { min: 3, max: 3 },
    proibido: { min: 4, max: 5 },
  });
});

test("mantem tudo como proibido quando nao ha parcela verde", () => {
  const faixas = calcularFaixasParcelamento(
    {
      1: { cor: "vermelho" },
      2: { cor: "vermelho" },
    },
    2,
  );

  assert.deepEqual(faixas, {
    saudavel: { min: 1, max: 0 },
    alerta: { min: 1, max: 0 },
    proibido: { min: 1, max: 2 },
  });
});

test("ignora parcelas sem simulacao e mantem limite maximo informado", () => {
  const faixas = calcularFaixasParcelamento(
    {
      1: { cor: "verde" },
      4: { cor: "vermelho" },
    },
    4,
  );

  assert.deepEqual(faixas, {
    saudavel: { min: 1, max: 1 },
    alerta: { min: 2, max: 3 },
    proibido: { min: 4, max: 4 },
  });
});

test("resolve faixas de parcelamento existentes ou indica simulacao pendente", () => {
  const formaCredito = {
    id: 4,
    permite_parcelamento: true,
    parcelas_maximas: 3,
  };
  const simulacoes = {
    4: {
      1: { cor: "verde" },
      2: { cor: "amarelo" },
      3: { cor: "vermelho" },
    },
  };

  assert.deepEqual(
    resolverFaixasParcelamentoDaForma({
      formaPagamentoSelecionada: formaCredito,
      simulacoesParcelamento: {},
      formasPagamento: [formaCredito],
    }),
    {
      acao: "simular",
      formaPagamento: formaCredito,
      faixas: null,
    },
  );

  assert.deepEqual(
    resolverFaixasParcelamentoDaForma({
      formaPagamentoSelecionada: formaCredito,
      simulacoesParcelamento: simulacoes,
      formasPagamento: [formaCredito],
    }),
    {
      acao: "usar_existente",
      formaPagamento: formaCredito,
      faixas: {
        saudavel: { min: 1, max: 1 },
        alerta: { min: 2, max: 2 },
        proibido: { min: 3, max: 3 },
      },
    },
  );

  assert.deepEqual(
    resolverFaixasParcelamentoDaForma({
      formaPagamentoSelecionada: null,
      simulacoesParcelamento: simulacoes,
      formasPagamento: [formaCredito],
    })?.faixas,
    {
      saudavel: { min: 1, max: 1 },
      alerta: { min: 2, max: 2 },
      proibido: { min: 3, max: 3 },
    },
  );

  assert.equal(
    resolverFaixasParcelamentoDaForma({
      formaPagamentoSelecionada: { id: 5, permite_parcelamento: false },
      simulacoesParcelamento: simulacoes,
      formasPagamento: [formaCredito],
    }),
    null,
  );
});

test("monta pagamento simulado e normaliza retorno da margem por parcela", () => {
  assert.deepEqual(
    montarPagamentoSimuladoParcelamento({
      formaPagamentoId: 7,
      valorTotal: 150,
      parcelas: 3,
      operadoraId: 9,
      bandeira: "Visa",
      modalidade: "credito",
    }),
    [
      {
        forma_pagamento_id: 7,
        valor: 150,
        parcelas: 3,
        operadora_id: 9,
        bandeira: "Visa",
        modalidade: "credito",
      },
    ],
  );

  assert.deepEqual(
    normalizarResultadoSimulacaoParcelamento({
      resultado: { cor_indicador: "amarelo" },
    }),
    { cor: "amarelo", classificacao: "amarelo" },
  );

  assert.equal(normalizarResultadoSimulacaoParcelamento({ resultado: {} }), null);

  assert.deepEqual(montarFallbackSimulacaoParcelamento(), {
    cor: null,
    classificacao: "verde",
  });
});

test("calcula previa de cashback, carimbos e recompra elegiveis por canal", () => {
  const resultado = calcularBeneficiosCampanhaPreview({
    campanhasCompra: [
      {
        name: "Cashback Ouro",
        campaign_type: "cashback",
        params: {
          benefit_channels: ["loja_fisica"],
          bronze_percent: 1,
          gold_percent: 3,
          pdv_bonus_percent: 2,
        },
      },
      {
        name: "Cartao fidelidade",
        campaign_type: "loyalty_stamp",
        params: { benefit_channels: ["loja_fisica"], min_purchase_value: 20 },
      },
      {
        name: "Recompra",
        campaign_type: "quick_repurchase",
        params: {
          benefit_channels: ["loja_fisica"],
          min_purchase_value: 50,
          coupon_type: "percent",
          coupon_value: 10,
        },
      },
      {
        name: "Cashback App",
        campaign_type: "cashback",
        params: { benefit_channels: ["app"], bronze_percent: 99 },
      },
    ],
    rankCliente: "gold",
    canalVenda: "loja_fisica",
    valorBase: 100,
  });

  assert.deepEqual(resultado, {
    cashbackPrevisto: [
      {
        campanha: "Cashback Ouro",
        percentual: 5,
        valor: 5,
      },
    ],
    carimbosPrevistos: [
      {
        campanha: "Cartao fidelidade",
        quantidade: 5,
      },
    ],
    recompraPrevista: [
      {
        campanha: "Recompra",
        tipo: "percent",
        valor: 10,
      },
    ],
  });
});

test("ignora campanhas exatamente duplicadas sem esconder configuracoes distintas", () => {
  const fidelidade = {
    name: "Cartao fidelidade",
    campaign_type: "loyalty_stamp",
    params: { benefit_channels: ["loja_fisica"], min_purchase_value: 50 },
  };
  const resultado = calcularBeneficiosCampanhaPreview({
    campanhasCompra: [
      fidelidade,
      { ...fidelidade, id: 99 },
      {
        ...fidelidade,
        name: "Cartao fidelidade VIP",
        params: { benefit_channels: ["loja_fisica"], min_purchase_value: 100 },
      },
    ],
    canalVenda: "loja_fisica",
    valorBase: 100,
  });

  assert.deepEqual(resultado.carimbosPrevistos, [
    { campanha: "Cartao fidelidade", quantidade: 2 },
    { campanha: "Cartao fidelidade VIP", quantidade: 1 },
  ]);
});

test("calcula resumo do recebimento considerando pagamentos novos e existentes", () => {
  const resumo = calcularResumoRecebimento({
    valorTotal: 100,
    pagamentos: [{ valor: 20 }, { valor: 10 }],
    totalPagoExistente: 30,
    valorRecebido: 50,
  });

  assert.deepEqual(resumo, {
    valorPago: 60,
    valorRestante: 40,
    vendaQuitadaComPagamentosExistentes: false,
    podeConfirmarFinalizacao: true,
    troco: 10,
  });
});

test("monta cupom salvo na venda quando nao ha cupom aplicado na tela", () => {
  const cupom = montarCupomParaFinalizar({
    cupomAplicado: null,
    venda: {
      cupom_code: "recompra10",
      cupom_discount_applied: 12.5,
      desconto_valor: 15,
    },
  });

  assert.deepEqual(cupom, {
    code: "recompra10",
    discount_applied: 12.5,
  });
});

test("descreve cupom somente quando ha codigo e desconto", () => {
  const texto = descreverCupomMargem(
    { code: "recompra10", discount_applied: 12.5 },
    (valor) => `R$ ${valor.toFixed(2)}`,
  );

  assert.equal(texto, "A margem ficou baixa por conta do cupom RECOMPRA10 (R$ 12.50 de desconto).");
  assert.equal(descreverCupomMargem(null), "");
});

test("monta itens e mensagem para confirmacao de estoque negativo", () => {
  assert.deepEqual(
    montarItensParaVerificarEstoqueNegativo([
      { tipo: "produto", produto_id: 10, quantidade: 2 },
      { tipo: "servico", produto_id: 11, quantidade: 1 },
      { tipo: "produto", quantidade: 3 },
    ]),
    [{ produto_id: 10, quantidade: 2 }],
  );

  assert.equal(
    montarMensagemEstoqueNegativo([
      {
        produto_nome: "Racao",
        estoque_atual: 1,
        estoque_resultante: -1,
      },
      {
        produto_nome: "Areia",
        estoque_atual: 0,
        estoque_resultante: -2,
      },
    ]),
    "\u26A0\uFE0F ATEN\u00C7\u00C3O: Os seguintes produtos ficar\u00E3o com ESTOQUE NEGATIVO:\n\n\u2022 Racao: estoque atual 1, ap\u00F3s venda ficar\u00E1 -1\n\u2022 Areia: estoque atual 0, ap\u00F3s venda ficar\u00E1 -2\n\nDeseja continuar mesmo assim?",
  );
});

test("monta pagamento de cartao com valor efetivo limitado ao restante", () => {
  const pagamento = montarPagamentoRecebido({
    formaPagamento: {
      id: 2,
      nome: "Credito",
      tipo: "cartao_credito",
      permite_parcelamento: true,
    },
    valor: 150,
    valorRestante: 100,
    bandeira: "Visa",
    nsuCartao: "123456",
    operadora: { id: 7 },
    numeroParcelas: 3,
    troco: 50,
  });

  assert.deepEqual(pagamento, {
    forma_pagamento: "Credito",
    forma_pagamento_tipo: "cartao_credito",
    forma_id: 2,
    forma_pagamento_id: 2,
    nome: "Credito",
    valor: 100,
    bandeira: "Visa",
    nsu_cartao: "123456",
    operadora_id: 7,
    modalidade_cartao: "credito",
    numero_parcelas: 3,
    parcelas: 3,
    valor_recebido: 150,
    troco: null,
    is_credito_cliente: false,
    is_cashback: false,
  });
});

test("monta pagamento em dinheiro com troco e sem dados de cartao", () => {
  const pagamento = montarPagamentoRecebido({
    formaPagamento: {
      id: 1,
      nome: "Dinheiro",
      tipo: "dinheiro",
      permite_parcelamento: false,
    },
    valor: 120,
    valorRestante: 100,
    bandeira: "Visa",
    nsuCartao: "123456",
    operadora: { id: 7 },
    numeroParcelas: 2,
    troco: 20,
  });

  assert.equal(pagamento.valor, 100);
  assert.equal(pagamento.bandeira, null);
  assert.equal(pagamento.nsu_cartao, null);
  assert.equal(pagamento.numero_parcelas, 1);
  assert.equal(pagamento.modalidade_cartao, null);
  assert.equal(pagamento.troco, 20);
});

test("monta crediario do ERP com vencimento informado em DD-MM-AAAA", () => {
  const pagamento = montarPagamentoRecebido({
    formaPagamento: {
      id: 9,
      nome: "Crediário",
      tipo: "crediario",
      data_vencimento_crediario: "30-09-2026",
    },
    valor: 100,
    valorRestante: 100,
  });

  assert.equal(pagamento.forma_pagamento_id, 9);
  assert.equal(pagamento.forma_pagamento_tipo, "crediario");
  assert.equal(pagamento.data_recebimento_prevista, "2026-09-30");
  assert.equal(dataCrediarioParaIso("30-09-2026"), "2026-09-30");
  assert.equal(dataCrediarioParaIso("31-02-2026"), null);
  assert.equal(mascararDataCrediario("30092026"), "30-09-2026");
});

test("monta crediario parcelado e gera previa mensal preservando o dia original", () => {
  const formaPagamento = {
    id: 9,
    nome: "Crediário",
    tipo: "crediario",
    data_vencimento_crediario: "31-01-2027",
    intervalo_crediario: "mensal",
  };
  const pagamento = montarPagamentoRecebido({
    formaPagamento,
    valor: 200,
    valorRestante: 200,
    numeroParcelas: 3,
  });
  const plano = gerarPlanoCrediario({
    valorTotal: 200,
    numeroParcelas: 3,
    primeiraData: "31-01-2027",
    intervalo: "mensal",
  });

  assert.equal(pagamento.numero_parcelas, 3);
  assert.equal(pagamento.intervalo_crediario, "mensal");
  assert.deepEqual(
    plano.map((parcela) => parcela.data_vencimento),
    ["31-01-2027", "28-02-2027", "31-03-2027"],
  );
  assert.deepEqual(
    plano.map((parcela) => parcela.valor),
    [66.67, 66.67, 66.66],
  );
});

test("nao envia identificador textual do credito do cliente ao backend", () => {
  const pagamento = montarPagamentoRecebido({
    formaPagamento: {
      id: "credito_cliente",
      nome: "Crédito Cliente",
      tipo: "credito_cliente",
      credito_disponivel: 7,
    },
    valor: 7,
    valorRestante: 121.4,
    operadora: { id: 1, nome: "Stone" },
  });

  assert.equal(pagamento.forma_id, "credito_cliente");
  assert.equal(pagamento.forma_pagamento_id, null);
  assert.equal(pagamento.operadora_id, null);
  assert.equal(pagamento.is_credito_cliente, true);
});

test("monta itens e payload para analise de margem", () => {
  const venda = {
    total: 200,
    desconto_valor: 15,
    funcionario_id: 9,
    entrega: { taxa_entrega_total: 12 },
    itens: [
      {
        produto_id: 10,
        quantidade: 2,
        preco_unitario: 40,
        preco_venda: 45,
        custo: 20,
      },
      {
        produto_id: 11,
        quantidade: 1,
        preco_venda: 30,
      },
    ],
  };

  assert.deepEqual(montarItensAnaliseMargem(venda.itens), [
    { produto_id: 10, quantidade: 2, preco_venda: 40, custo: 20 },
    { produto_id: 11, quantidade: 1, preco_venda: 30, custo: null },
  ]);

  assert.deepEqual(
    montarPayloadAnaliseMargem({
      venda,
      formasPagamento: [{ forma_pagamento_id: 1, valor: 200, parcelas: 1 }],
    }),
    {
      items: [
        { produto_id: 10, quantidade: 2, preco_venda: 40, custo: 20 },
        { produto_id: 11, quantidade: 1, preco_venda: 30, custo: null },
      ],
      formas_pagamento: [{ forma_pagamento_id: 1, valor: 200, parcelas: 1 }],
      desconto: 15,
      taxa_entrega: 12,
      vendedor_id: 9,
    },
  );
});

test("monta pagamentos de margem ignorando cashback novo", () => {
  const pagamentos = montarPagamentosMargem({
    pagamentosExistentes: [{ id: 1, valor: 20 }],
    pagamentos: [
      { id: 2, valor: 30 },
      { id: 3, valor: 10, is_cashback: true },
    ],
  });

  assert.deepEqual(pagamentos, [
    { id: 1, valor: 20 },
    { id: 2, valor: 30 },
  ]);
});

test("monta formas de pagamento para analise da venda com restante em dinheiro", () => {
  const formas = montarFormasPagamentoAnalise({
    pagamentos: [{ forma_id: 4, valor: 60, parcelas: 2 }],
    formasPagamento: [{ id: 1, tipo: "dinheiro", nome: "Dinheiro" }],
    valorTotal: 100,
  });

  assert.deepEqual(formas, [
    {
      forma_pagamento_id: 4,
      valor: 60,
      parcelas: 2,
      operadora_id: null,
      bandeira: null,
      modalidade: null,
    },
    { forma_pagamento_id: 1, valor: 40, parcelas: 1 },
  ]);
});

test("analisa credito do cliente com Getnet Mastercard em uma vez", () => {
  const formas = montarFormasPagamentoAnalise({
    pagamentos: [
      {
        forma_pagamento: "Crédito Cliente",
        forma_id: "credito_cliente",
        forma_pagamento_id: "credito_cliente",
        valor: 7,
        parcelas: 1,
      },
      {
        forma_pagamento: "Crédito",
        forma_id: 4,
        forma_pagamento_id: 4,
        valor: 114.4,
        parcelas: 1,
        bandeira: "Mastercard",
        modalidade_cartao: "credito",
        operadora_id: 11,
      },
    ],
    formasPagamento: [
      { id: 1, tipo: "dinheiro", nome: "Dinheiro" },
      { id: 4, tipo: "cartao_credito", nome: "Crédito" },
    ],
    valorTotal: 121.4,
  });

  assert.deepEqual(formas, [
    {
      forma_pagamento_id: 4,
      valor: 114.4,
      parcelas: 1,
      operadora_id: 11,
      bandeira: "Mastercard",
      modalidade: "credito",
    },
  ]);
});

test("reutiliza venda criada quando a primeira finalizacao falha", async () => {
  const chamadas = { criar: 0, atualizar: 0 };
  const criarVenda = async () => {
    chamadas.criar += 1;
    return { id: 1068294 };
  };
  const atualizarVenda = async (vendaId) => {
    chamadas.atualizar += 1;
    assert.equal(vendaId, 1068294);
  };

  const primeiraVendaId = await persistirVendaAbertaParaPagamento({
    vendaParaPersistir: {},
    payloadVenda: { total: 121.4 },
    criarVenda,
    atualizarVenda,
  });
  const segundaVendaId = await persistirVendaAbertaParaPagamento({
    vendaParaPersistir: {},
    payloadVenda: { total: 121.4 },
    vendaIdPersistida: primeiraVendaId,
    criarVenda,
    atualizarVenda,
  });

  assert.equal(primeiraVendaId, 1068294);
  assert.equal(segundaVendaId, 1068294);
  assert.deepEqual(chamadas, { criar: 1, atualizar: 1 });
});

test("monta pagamento a vista com a forma cadastrada no tenant", () => {
  assert.deepEqual(montarPagamentoAVista(99.9, 42), [
    { forma_pagamento_id: 42, valor: 99.9, parcelas: 1 },
  ]);
});

test("valida pagamento antes de adicionar", () => {
  assert.equal(
    validarPagamentoParaAdicionar({
      formaPagamento: null,
      valor: 100,
    }),
    "Selecione uma forma de pagamento",
  );

  assert.equal(
    validarPagamentoParaAdicionar({
      formaPagamento: { id: 1, tipo: "dinheiro" },
      valor: 0,
    }),
    "Informe o valor recebido",
  );

  assert.equal(
    validarPagamentoParaAdicionar({
      formaPagamento: {
        id: 9,
        tipo: "crediario",
        data_vencimento_crediario: "30-09-2026",
      },
      valor: 100,
    }),
    "Selecione o cliente da venda para usar o crediário",
  );

  assert.equal(
    validarPagamentoParaAdicionar({
      formaPagamento: {
        id: 9,
        tipo: "crediario",
        data_vencimento_crediario: "31-02-2026",
      },
      valor: 100,
      cliente: { id: 4 },
    }),
    "Informe uma data de vencimento válida no formato DD-MM-AAAA",
  );

  assert.equal(
    validarPagamentoParaAdicionar({
      formaPagamento: {
        id: "credito_cliente",
        tipo: "credito_cliente",
        credito_disponivel: 20,
      },
      valor: 25,
    }),
    "Valor excede o crédito disponível (R$ 20.00)",
  );

  assert.equal(
    validarPagamentoParaAdicionar({
      formaPagamento: {
        id: "cashback",
        tipo: "cashback",
      },
      valor: 15,
      saldoCashback: 10,
    }),
    "Valor excede o cashback disponível (R$ 10,00)",
  );

  assert.equal(
    validarPagamentoParaAdicionar({
      formaPagamento: { id: 2, tipo: "cartao_credito" },
      valor: 100,
      bandeira: "",
      operadora: { nome: "Cielo", max_parcelas: 3 },
    }),
    "Selecione a bandeira do cartão",
  );

  assert.equal(
    validarPagamentoParaAdicionar({
      formaPagamento: { id: 2, tipo: "cartao_credito" },
      valor: 100,
      bandeira: "Visa",
      operadora: null,
    }),
    "Selecione a operadora do cartão",
  );

  assert.equal(
    validarPagamentoParaAdicionar({
      formaPagamento: { id: 2, tipo: "cartao_credito" },
      valor: 100,
      bandeira: "Visa",
      operadora: { nome: "Cielo", max_parcelas: 3 },
      numeroParcelas: 4,
    }),
    "A operadora Cielo permite no máximo 3x",
  );

  assert.equal(
    validarPagamentoParaAdicionar({
      formaPagamento: { id: 1, tipo: "dinheiro" },
      valor: 100,
    }),
    "",
  );
});

test("monta observacoes com justificativa de margem sem duplicar bloco existente", () => {
  const observacoes = montarObservacoesComJustificativaMargem({
    observacoesAtuais: "Observacao original",
    descricaoCupomMargem: "A margem ficou baixa por conta do cupom TESTE.",
    justificativaTexto: "Autorizado pelo gerente",
  });

  assert.equal(
    observacoes,
    "Observacao original\n\nJUSTIFICATIVA (Margem Critica): A margem ficou baixa por conta do cupom TESTE. Observacao informada: Autorizado pelo gerente",
  );

  assert.equal(
    montarObservacoesComJustificativaMargem({
      observacoesAtuais: observacoes,
      descricaoCupomMargem: "A margem ficou baixa por conta do cupom TESTE.",
      justificativaTexto: "Autorizado pelo gerente",
    }),
    observacoes,
  );
});
