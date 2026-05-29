import { formatBenefitChannelsSummary } from "./campaignChannelScope.js";

const CAMPAIGN_TYPE_LABELS = {
  birthday: "Aniversario",
  birthday_customer: "Aniversario do cliente",
  birthday_pet: "Aniversario do pet",
  cashback: "Cashback",
  inactivity: "Clientes inativos",
  loyalty_stamp: "Cartao fidelidade",
  monthly_highlight: "Destaque mensal",
  quick_repurchase: "Recompra rapida",
  ranking_monthly: "Ranking mensal",
  welcome: "Boas-vindas",
  welcome_app: "Boas-vindas App",
  win_back: "Reativacao",
};

const CHANNEL_LABELS = {
  all: "Todos os canais",
  app: "App",
  ecommerce: "E-commerce",
  pdv: "PDV",
};

function formatCurrency(value) {
  const amount = Number(value || 0);
  return amount.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).replace(/\u00a0/g, " ");
}

function formatDate(value) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleDateString("pt-BR", { timeZone: "UTC" });
}

function getCouponBenefit(coupon = {}) {
  if (coupon.coupon_type === "percent" && coupon.discount_percent != null) {
    return `${Number(coupon.discount_percent).toLocaleString("pt-BR")}% de desconto`;
  }

  if (coupon.coupon_type === "fixed" && coupon.discount_value != null) {
    return `${formatCurrency(coupon.discount_value)} de desconto`;
  }

  if (coupon.coupon_type === "gift") {
    return coupon.meta?.mensagem || coupon.meta?.categoria || "Brinde";
  }

  return "Beneficio cadastrado no cupom";
}

function hasBenefitChannelScope(params = {}) {
  return [
    "benefit_channels",
    "canais_beneficio",
    "aplicar_canais_venda",
    "benefit_channel_scope",
  ].some((key) => Object.prototype.hasOwnProperty.call(params, key));
}

function getConfiguredRules(coupon = {}) {
  const explicitRules =
    coupon.meta?.regras_resumo || coupon.rules_summary || coupon.regras_resumo;

  if (explicitRules) return explicitRules;

  const params = coupon.campaign_params || coupon.params || coupon.meta?.campaign_params || {};
  const campaignType = coupon.campaign_type || coupon.tipo_campanha || coupon.meta?.campaign_type;
  const rules = [];

  if (campaignType === "quick_repurchase") {
    rules.push("Gerado apos uma compra finalizada");
  } else if (campaignType === "inactivity" || campaignType === "win_back") {
    const inactivityDays = params.inactivity_days || params.dias_inatividade;
    rules.push(
      inactivityDays
        ? `Cliente sem compra ha ${inactivityDays} dia(s)`
        : "Cliente inativo conforme configuracao da campanha"
    );
  } else if (campaignType === "birthday_customer") {
    rules.push("Gerado por aniversario do cliente");
  } else if (campaignType === "birthday_pet") {
    rules.push("Gerado por aniversario do pet");
  } else if (campaignType === "welcome" || campaignType === "welcome_app") {
    rules.push("Gerado como boas-vindas");
  } else if (campaignType === "loyalty_stamp") {
    const stamps = params.stamps_to_complete || params.carimbos_para_resgate;
    rules.push(
      stamps ? `Resgate ao completar ${stamps} carimbo(s)` : "Gerado pelo cartao fidelidade"
    );
  }

  if (params.coupon_valid_days) {
    rules.push(`validade configurada de ${params.coupon_valid_days} dia(s)`);
  }

  if (hasBenefitChannelScope(params)) {
    rules.push(`Canais de beneficio: ${formatBenefitChannelsSummary(params)}`);
  }

  return rules.join("; ");
}

export function buildPdvCouponTooltip(coupon = {}) {
  const code = String(coupon.code || coupon.codigo || coupon.id || "").trim();
  const campaignName =
    coupon.nome_campanha || coupon.campaign_name || coupon.meta?.campaign_name || "Cupom manual";
  const campaignType = coupon.campaign_type || coupon.tipo_campanha || coupon.meta?.campaign_type;
  const campaignTypeLabel = CAMPAIGN_TYPE_LABELS[campaignType] || campaignType;
  const channel = coupon.channel || coupon.canal || "all";
  const channelLabel = CHANNEL_LABELS[channel] || channel;
  const validUntil = formatDate(coupon.valid_until);
  const reason = coupon.meta?.motivo || coupon.meta?.source || coupon.meta?.origem;
  const rules = getConfiguredRules(coupon);

  const lines = [
    code ? `Cupom ${code}` : "Cupom disponivel",
    `Campanha: ${campaignName}`,
  ];

  if (campaignTypeLabel) lines.push(`Tipo: ${campaignTypeLabel}`);
  lines.push(`Beneficio: ${getCouponBenefit(coupon)}`);

  if (coupon.min_purchase_value != null) {
    lines.push(`Compra minima: ${formatCurrency(coupon.min_purchase_value)}`);
  }

  if (validUntil) lines.push(`Valido ate: ${validUntil}`);
  if (channelLabel) lines.push(`Canal: ${channelLabel}`);
  if (reason) lines.push(`Origem: ${reason}`);
  if (rules) lines.push(`Regras: ${rules}`);

  return lines.filter(Boolean).join("\n");
}
