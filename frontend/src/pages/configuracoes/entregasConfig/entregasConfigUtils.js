export const fieldStyle = {
  width: "100%",
  padding: "10px 12px",
  border: "1px solid #d1d5db",
  borderRadius: 8,
  fontSize: 14,
  color: "#111827",
  background: "#fff",
  boxSizing: "border-box",
};

export function optionalNumber(value) {
  if (value === "" || value === null || value === undefined) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function optionalPositiveNumber(value) {
  const parsed = optionalNumber(value);
  return parsed !== null && parsed > 0 ? parsed : null;
}

export function nextTierLimit(tiers) {
  const lastTier = tiers[tiers.length - 1];
  const lastLimit = Number(lastTier?.ate_km);
  return Number.isFinite(lastLimit) && lastLimit > 0 ? String(lastLimit + 1) : "1";
}

export function createInitialEntregasForm() {
  return {
    entregador_padrao_id: "",
    ponto_inicial_rota: "",
    cep: "",
    logradouro: "",
    numero: "",
    complemento: "",
    bairro: "",
    cidade: "",
    estado: "",
    metodo_km_entrega: "auto_rota",
    entrega_ativa: true,
    retirada_ativa: true,
    modalidade_cobranca: "fixa",
    taxa_fixa: 0,
    valor_por_km_cobrado: 0,
    taxa_minima: 0,
    faixas_distancia: [],
    valor_km_excedente: 0,
    distancia_maxima_entrega_km: "",
    frete_gratis_acima: 0,
    distancia_maxima_frete_gratis_km: "",
    pedido_minimo: 0,
    prazo_entrega_texto: "",
  };
}

export function normalizeEntregasConfig(config = {}) {
  return {
    entregador_padrao_id: config.entregador_padrao_id ?? "",
    ponto_inicial_rota: "",
    cep: config.cep ?? "",
    logradouro: config.logradouro ?? "",
    numero: config.numero ?? "",
    complemento: config.complemento ?? "",
    bairro: config.bairro ?? "",
    cidade: config.cidade ?? "",
    estado: config.estado ?? "",
    metodo_km_entrega: config.metodo_km_entrega ?? "auto_rota",
    entrega_ativa: config.entrega_ativa !== false,
    retirada_ativa: config.retirada_ativa !== false,
    modalidade_cobranca: config.modalidade_cobranca ?? "fixa",
    taxa_fixa: Number(config.taxa_fixa || 0),
    valor_por_km_cobrado: Number(config.valor_por_km_cobrado || 0),
    taxa_minima: Number(config.taxa_minima || 0),
    faixas_distancia: Array.isArray(config.faixas_distancia)
      ? config.faixas_distancia.map((faixa) => ({
          ate_km: String(faixa.ate_km ?? ""),
          valor: Number(faixa.valor || 0),
        }))
      : [],
    valor_km_excedente: Number(config.valor_km_excedente || 0),
    distancia_maxima_entrega_km: config.distancia_maxima_entrega_km ?? "",
    frete_gratis_acima: Number(config.frete_gratis_acima || 0),
    distancia_maxima_frete_gratis_km: config.distancia_maxima_frete_gratis_km ?? "",
    pedido_minimo: Number(config.pedido_minimo || 0),
    prazo_entrega_texto: config.prazo_entrega_texto ?? "",
  };
}

export function normalizeEntregadores(data) {
  return Array.isArray(data) ? data : data?.clientes || data?.items || [];
}

function normalizeDistanceTiers(form) {
  return form.faixas_distancia.map((tier) => ({
    ate_km: Number(tier.ate_km),
    valor: Number(tier.valor),
  }));
}

export function validateEntregasForm(form) {
  if (form.modalidade_cobranca === "por_km" && Number(form.valor_por_km_cobrado || 0) <= 0) {
    return "Informe um valor por km maior que zero.";
  }
  const distancePricing = ["por_km", "por_faixa"].includes(form.modalidade_cobranca);
  if (distancePricing && (!form.logradouro || !form.numero)) {
    return "Para cobrar por distância, complete pelo menos logradouro e número da loja.";
  }
  const distanceTiers = normalizeDistanceTiers(form);
  if (form.modalidade_cobranca === "por_faixa") {
    if (
      distanceTiers.length === 0 ||
      distanceTiers.some(
        (tier) =>
          !Number.isFinite(tier.ate_km) ||
          tier.ate_km <= 0 ||
          !Number.isFinite(tier.valor) ||
          tier.valor < 0,
      )
    ) {
      return "Preencha todas as faixas com uma distância maior que zero e um preço válido.";
    }
    if (
      distanceTiers.some(
        (tier, index) => index > 0 && tier.ate_km <= distanceTiers[index - 1].ate_km,
      )
    ) {
      return "Organize as faixas em ordem crescente, sem repetir a distância.";
    }
  }
  return null;
}

export function buildEntregasPayload(form) {
  return {
    entregador_padrao_id: form.entregador_padrao_id || null,
    cep: form.cep || null,
    logradouro: form.logradouro || null,
    numero: form.numero || null,
    complemento: form.complemento || null,
    bairro: form.bairro || null,
    cidade: form.cidade || null,
    estado: form.estado || null,
    metodo_km_entrega: form.metodo_km_entrega || "auto_rota",
    entrega_ativa: form.entrega_ativa,
    retirada_ativa: form.retirada_ativa,
    modalidade_cobranca: form.modalidade_cobranca,
    taxa_fixa: Number(form.taxa_fixa || 0),
    valor_por_km_cobrado:
      form.modalidade_cobranca === "por_km" ? Number(form.valor_por_km_cobrado || 0) : null,
    taxa_minima: Number(form.taxa_minima || 0),
    faixas_distancia: normalizeDistanceTiers(form),
    valor_km_excedente: optionalPositiveNumber(form.valor_km_excedente),
    distancia_maxima_entrega_km: optionalPositiveNumber(form.distancia_maxima_entrega_km),
    frete_gratis_acima: optionalPositiveNumber(form.frete_gratis_acima),
    distancia_maxima_frete_gratis_km: optionalPositiveNumber(form.distancia_maxima_frete_gratis_km),
    pedido_minimo: Number(form.pedido_minimo || 0),
    prazo_entrega_texto: form.prazo_entrega_texto.trim() || null,
  };
}
