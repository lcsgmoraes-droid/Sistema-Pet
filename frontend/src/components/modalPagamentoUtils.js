import {
  campaignAllowsSaleChannel,
  getCashbackBonusParamKey,
} from "../utils/campaignChannelScope.js";

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
