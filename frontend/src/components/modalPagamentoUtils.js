import {
  campaignAllowsSaleChannel,
  getCashbackBonusParamKey,
} from "../utils/campaignChannelScope.js";

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
