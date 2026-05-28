import {
  campaignAllowsSaleChannel,
  getCashbackBonusParamKey,
} from "../utils/campaignChannelScope.js";

export function identificarIconeFormaPagamento(icone, nome) {
  const key = String(icone || nome || "").toLowerCase();
  if (key.includes("pix")) return "qr_code";
  if (key.includes("dinheiro") || key.includes("cash")) return "banknote";
  if (key.includes("debito") || key.includes("débito")) return "credit_card";
  if (key.includes("parcelado")) return "credit_card";
  if (key.includes("credito") || key.includes("crédito")) return "credit_card";
  if (key.includes("transfer") || key.includes("banc")) return "transfer";
  if (key.includes("boleto")) return "receipt";
  if (key.includes("wallet") || key.includes("carteira")) return "wallet";
  return "credit_card";
}

export function obterCorParcelamentoAtual({
  formaPagamento = null,
  simulacoesParcelamento = {},
  numeroParcelas = 1,
}) {
  if (!formaPagamento?.permite_parcelamento) return "verde";
  return simulacoesParcelamento[formaPagamento.id]?.[numeroParcelas]?.cor ?? "verde";
}

export function avaliarEstadoJustificativaMargem({
  statusMargem = null,
  corParcelamentoAtual = "verde",
  justificativaTexto = "",
}) {
  const margemCriticaAtual =
    statusMargem === "vermelho" || corParcelamentoAtual === "vermelho";

  return {
    margemCriticaAtual,
    mostrarCampoJustificativa:
      margemCriticaAtual ||
      Boolean(justificativaTexto && justificativaTexto.trim().length > 0),
  };
}

export function calcularResumoRecebimento({
  valorTotal = 0,
  pagamentos = [],
  totalPagoExistente = 0,
  valorRecebido = 0,
}) {
  const total = Number(valorTotal || 0);
  const pagoExistente = Number(totalPagoExistente || 0);
  const pagoNovo = pagamentos.reduce((sum, pagamento) => sum + Number(pagamento.valor || 0), 0);
  const valorPago = pagoNovo + pagoExistente;
  const valorRestante = Math.max(0, total - valorPago);
  const vendaQuitadaComPagamentosExistentes = pagoExistente >= total - 0.01;

  return {
    valorPago,
    valorRestante,
    vendaQuitadaComPagamentosExistentes,
    podeConfirmarFinalizacao:
      pagamentos.length > 0 || vendaQuitadaComPagamentosExistentes,
    troco: Number(valorRecebido || 0) > 0 ? Number(valorRecebido || 0) - valorRestante : 0,
  };
}

export function montarCupomParaFinalizar({ cupomAplicado, venda = {} }) {
  if (cupomAplicado) return cupomAplicado;
  if (!venda.cupom_code) return null;

  return {
    code: venda.cupom_code,
    discount_applied: venda.cupom_discount_applied ?? venda.desconto_valor ?? null,
  };
}

export function descreverCupomMargem(cupomParaFinalizar, formatarValor = (valor) => String(valor)) {
  if (
    !cupomParaFinalizar?.code ||
    Number(cupomParaFinalizar?.discount_applied || 0) <= 0
  ) {
    return "";
  }

  return `A margem ficou baixa por conta do cupom ${String(cupomParaFinalizar.code).toUpperCase()} (${formatarValor(Number(cupomParaFinalizar.discount_applied || 0))} de desconto).`;
}

export function montarObservacoesComJustificativaMargem({
  observacoesAtuais = "",
  descricaoCupomMargem = "",
  justificativaTexto = "",
}) {
  const justificativaFinal = descricaoCupomMargem
    ? `${descricaoCupomMargem} Observacao informada: ${justificativaTexto}`
    : justificativaTexto;
  const blocoJustificativa = `JUSTIFICATIVA (Margem Critica): ${justificativaFinal}`;

  if (String(observacoesAtuais || "").includes(blocoJustificativa)) {
    return observacoesAtuais || "";
  }

  return observacoesAtuais
    ? `${observacoesAtuais}\n\n${blocoJustificativa}`
    : blocoJustificativa;
}

export function montarPagamentoRecebido({
  formaPagamento,
  valor = 0,
  valorRestante = 0,
  bandeira = "",
  nsuCartao = "",
  operadora = null,
  numeroParcelas = 1,
  troco = 0,
}) {
  const tipo = formaPagamento?.tipo;
  const isCartao = ["cartao_credito", "cartao_debito"].includes(tipo);
  const parcelas = formaPagamento?.permite_parcelamento ? numeroParcelas : 1;

  return {
    forma_pagamento: formaPagamento.nome,
    forma_id: formaPagamento.id,
    forma_pagamento_id: formaPagamento.id,
    nome: formaPagamento.nome,
    valor: Math.min(Number(valor || 0), Number(valorRestante || 0)),
    bandeira: isCartao ? bandeira : null,
    nsu_cartao: isCartao && nsuCartao ? nsuCartao : null,
    operadora_id: operadora?.id || null,
    numero_parcelas: parcelas,
    parcelas,
    valor_recebido: Number(valor || 0),
    troco: tipo === "dinheiro" && troco > 0 ? troco : null,
    is_credito_cliente:
      formaPagamento.nome === "Crédito Cliente" || tipo === "credito_cliente",
    is_cashback: formaPagamento.id === "cashback",
  };
}

export function validarPagamentoParaAdicionar({
  formaPagamento,
  valor = 0,
  saldoCashback = 0,
  bandeira = "",
  operadora = null,
  numeroParcelas = 1,
}) {
  if (!formaPagamento) {
    return "Selecione uma forma de pagamento";
  }

  const valorNumerico = Number(valor || 0);

  if (valorNumerico <= 0) {
    return "Informe o valor recebido";
  }

  if (
    formaPagamento.id === "credito_cliente" &&
    valorNumerico > Number(formaPagamento.credito_disponivel || 0)
  ) {
    return `Valor excede o crédito disponível (R$ ${Number(
      formaPagamento.credito_disponivel || 0,
    ).toFixed(2)})`;
  }

  if (
    formaPagamento.id === "cashback" &&
    valorNumerico > Number(saldoCashback || 0) + 0.01
  ) {
    return `Valor excede o cashback disponível (R$ ${Number(saldoCashback || 0)
      .toFixed(2)
      .replace(".", ",")})`;
  }

  const isCartao = ["cartao_credito", "cartao_debito"].includes(
    formaPagamento.tipo,
  );

  if (isCartao && !bandeira) {
    return "Selecione a bandeira do cartão";
  }

  if (isCartao && !operadora) {
    return "Selecione a operadora do cartão";
  }

  if (operadora && numeroParcelas > operadora.max_parcelas) {
    return `A operadora ${operadora.nome} permite no máximo ${operadora.max_parcelas}x`;
  }

  return "";
}

export function montarItensAnaliseMargem(itens = []) {
  return (itens || []).map((item) => ({
    produto_id: item.produto_id,
    quantidade: item.quantidade,
    preco_venda: item.preco_unitario || item.preco_venda || 0,
    custo: item.custo || null,
  }));
}

export function montarPagamentoAVista(valor, formaPagamentoId = 1) {
  return [
    {
      forma_pagamento_id: formaPagamentoId,
      valor,
      parcelas: 1,
    },
  ];
}

export function montarPagamentosMargem({
  pagamentosExistentes = [],
  pagamentos = [],
}) {
  return [
    ...pagamentosExistentes,
    ...pagamentos.filter((pagamento) => !pagamento.is_cashback),
  ];
}

export function montarPayloadAnaliseMargem({ venda = {}, formasPagamento = [] }) {
  return {
    items: montarItensAnaliseMargem(venda.itens || []),
    formas_pagamento: formasPagamento,
    desconto: venda.desconto_valor || 0,
    taxa_entrega: venda.entrega?.taxa_entrega_total || 0,
    vendedor_id: venda.funcionario_id || null,
  };
}

export function montarItensParaVerificarEstoqueNegativo(itens = []) {
  return (itens || [])
    .filter((item) => item.tipo === "produto" && item.produto_id)
    .map((item) => ({
      produto_id: item.produto_id,
      quantidade: item.quantidade,
    }));
}

export function montarMensagemEstoqueNegativo(produtosNegativos = []) {
  const mensagens = (produtosNegativos || [])
    .map(
      (produto) =>
        `\u2022 ${produto.produto_nome}: estoque atual ${produto.estoque_atual}, ap\u00F3s venda ficar\u00E1 ${produto.estoque_resultante}`,
    )
    .join("\n");

  return `\u26A0\uFE0F ATEN\u00C7\u00C3O: Os seguintes produtos ficar\u00E3o com ESTOQUE NEGATIVO:\n\n${mensagens}\n\nDeseja continuar mesmo assim?`;
}

export function montarFormasPagamentoAnalise({
  pagamentos = [],
  formasPagamento = [],
  valorTotal = 0,
}) {
  const totalAlocado = pagamentos.reduce(
    (sum, pagamento) => sum + Number(pagamento.valor || 0),
    0,
  );
  const restante = Number(valorTotal || 0) - totalAlocado;
  const dinheiro = formasPagamento.find(
    (forma) =>
      forma.tipo === "dinheiro" ||
      String(forma.nome || "").toLowerCase().includes("dinheiro"),
  );

  if (pagamentos.length === 0) {
    return montarPagamentoAVista(Number(valorTotal || 0), dinheiro?.id || null);
  }

  const formasAnalise = pagamentos.map((pagamento) => ({
    forma_pagamento_id: pagamento.forma_pagamento_id || pagamento.forma_id,
    valor: pagamento.valor,
    parcelas: pagamento.parcelas || pagamento.numero_parcelas || 1,
  }));

  if (restante > 0) {
    formasAnalise.push({
      forma_pagamento_id: dinheiro?.id || null,
      valor: restante,
      parcelas: 1,
    });
  }

  return formasAnalise;
}

export function calcularFaixasParcelamento(simulacoes, maxParcelas) {
  const faixas = {
    saudavel: { min: 1, max: 0 },
    alerta: { min: 0, max: 0 },
    proibido: { min: 0, max: maxParcelas },
  };

  let ultimaVerde = 0;
  let primeiraVermelha = maxParcelas + 1;

  for (let i = 1; i <= maxParcelas; i += 1) {
    const sim = simulacoes[i];
    if (!sim) continue;

    if (sim.cor === "verde") {
      ultimaVerde = i;
    } else if (sim.cor === "vermelho" && i < primeiraVermelha) {
      primeiraVermelha = i;
    }
  }

  faixas.saudavel.max = ultimaVerde;
  faixas.alerta.min = ultimaVerde + 1;
  faixas.alerta.max = primeiraVermelha - 1;
  faixas.proibido.min = primeiraVermelha;

  return faixas;
}

export function calcularBeneficiosCampanhaPreview({
  campanhasCompra = [],
  rankCliente = "bronze",
  canalVenda = "loja_fisica",
  valorBase = 0,
}) {
  const valorBaseNumerico = Number(valorBase || 0);
  const canal = canalVenda || "loja_fisica";
  const campanhasElegiveisCanal = campanhasCompra.filter((campanha) =>
    campaignAllowsSaleChannel(campanha, canal),
  );

  const cashbackPrevisto = campanhasElegiveisCanal
    .filter((campanha) => campanha.campaign_type === "cashback")
    .map((campanha) => {
      const params = campanha.params || {};
      const chaveRank = `${rankCliente}_percent`;
      const percentualBase = Number(params[chaveRank] ?? params.bronze_percent ?? 0);
      const bonusCanal = Number(params[getCashbackBonusParamKey(canal)] ?? 0);
      const percentualTotal = percentualBase + bonusCanal;
      const valor = (valorBaseNumerico * percentualTotal) / 100;

      if (valor <= 0) return null;

      return {
        campanha: campanha.name,
        percentual: percentualTotal,
        valor,
      };
    })
    .filter(Boolean);

  const carimbosPrevistos = campanhasElegiveisCanal
    .filter((campanha) => campanha.campaign_type === "loyalty_stamp")
    .map((campanha) => {
      const params = campanha.params || {};
      const valorPorCarimbo = Number(params.min_purchase_value || 0);

      if (valorPorCarimbo <= 0) return null;

      const quantidade = Math.floor(valorBaseNumerico / valorPorCarimbo);
      if (quantidade <= 0) return null;

      return {
        campanha: campanha.name,
        quantidade,
      };
    })
    .filter(Boolean);

  const recompraPrevista = campanhasElegiveisCanal
    .filter((campanha) => campanha.campaign_type === "quick_repurchase")
    .map((campanha) => {
      const params = campanha.params || {};
      const minPurchase = Number(params.min_purchase_value || 0);
      const couponType = String(params.coupon_type || "percent");
      const couponValue = Number(params.coupon_value || 0);

      if (couponValue <= 0 || valorBaseNumerico < minPurchase) return null;

      return {
        campanha: campanha.name,
        tipo: couponType,
        valor: couponValue,
      };
    })
    .filter(Boolean);

  return {
    cashbackPrevisto,
    carimbosPrevistos,
    recompraPrevista,
  };
}
