export const BENEFIT_CHANNEL_OPTIONS = [
  {
    value: 'loja_fisica',
    label: 'Loja / PDV',
    description: 'Vendas normais feitas no caixa.',
  },
  {
    value: 'banho_tosa',
    label: 'Banho & Tosa',
    description: 'Atendimentos vindos da agenda e fila de banho e tosa.',
  },
  {
    value: 'veterinario',
    label: 'Veterinario',
    description: 'Consultas, procedimentos e recebimentos da clinica.',
  },
  {
    value: 'app',
    label: 'App',
    description: 'Pedidos confirmados pelo aplicativo do cliente.',
  },
  {
    value: 'ecommerce',
    label: 'E-commerce',
    description: 'Pedidos confirmados pelo site.',
  },
];

export const DEFAULT_BENEFIT_CHANNELS = ['loja_fisica', 'app', 'ecommerce'];

export const PURCHASE_BENEFIT_CAMPAIGN_TYPES = new Set([
  'loyalty_stamp',
  'cashback',
  'quick_repurchase',
]);

const ALL_CHANNELS = BENEFIT_CHANNEL_OPTIONS.map((option) => option.value);
const LEGACY_BLOCKED_SERVICE_CHANNELS = new Set(['banho_tosa', 'veterinario']);

const CHANNEL_ALIASES = {
  pdv: 'loja_fisica',
  loja: 'loja_fisica',
  loja_fisica: 'loja_fisica',
  'loja-fisica': 'loja_fisica',
  balcao: 'loja_fisica',
  banho_tosa: 'banho_tosa',
  'banho-e-tosa': 'banho_tosa',
  'banho e tosa': 'banho_tosa',
  bt: 'banho_tosa',
  veterinario: 'veterinario',
  veterinaria: 'veterinario',
  vet: 'veterinario',
  clinica: 'veterinario',
  app: 'app',
  aplicativo: 'app',
  mobile: 'app',
  ecommerce: 'ecommerce',
  'e-commerce': 'ecommerce',
  site: 'ecommerce',
  web: 'ecommerce',
};

export function normalizeBenefitChannel(channel) {
  const value = String(channel || 'loja_fisica').trim().toLowerCase().replace(/\s+/g, '_');
  return CHANNEL_ALIASES[value] || value || 'loja_fisica';
}
function extractBenefitScope(params = {}) {
  if (Object.prototype.hasOwnProperty.call(params, 'benefit_channels')) {
    return params.benefit_channels;
  }
  if (Object.prototype.hasOwnProperty.call(params, 'canais_beneficio')) {
    return params.canais_beneficio;
  }
  if (Object.prototype.hasOwnProperty.call(params, 'aplicar_canais_venda')) {
    return params.aplicar_canais_venda;
  }
  if (Object.prototype.hasOwnProperty.call(params, 'benefit_channel_scope')) {
    return params.benefit_channel_scope;
  }
  return null;
}

export function getConfiguredBenefitChannels(params = {}) {
  const scope = extractBenefitScope(params);
  if (scope == null) return null;

  if (typeof scope === 'string') {
    const normalizedText = scope.trim().toLowerCase();
    if (['all', 'todos', 'tudo'].includes(normalizedText)) return [...ALL_CHANNELS];
    return [normalizeBenefitChannel(scope)];
  }

  if (Array.isArray(scope)) {
    const rawValues = scope.map((item) => String(item || '').trim().toLowerCase());
    if (rawValues.some((item) => ['all', 'todos', 'tudo'].includes(item))) {
      return [...ALL_CHANNELS];
    }
    return [...new Set(scope.map(normalizeBenefitChannel))].filter(Boolean);
  }

  if (typeof scope === 'object') {
    if (scope.all || scope.todos || scope.tudo) return [...ALL_CHANNELS];
    return Object.entries(scope)
      .filter(([, enabled]) => Boolean(enabled))
      .map(([key]) => normalizeBenefitChannel(key));
  }

  return null;
}

export function getBenefitChannelsForEdit(params = {}) {
  return getConfiguredBenefitChannels(params) || [...DEFAULT_BENEFIT_CHANNELS];
}

export function campaignAllowsSaleChannel(campaign, saleChannel) {
  const params = campaign?.params || campaign || {};
  const channel = normalizeBenefitChannel(saleChannel);
  const configuredChannels = getConfiguredBenefitChannels(params);

  if (!configuredChannels) {
    return !LEGACY_BLOCKED_SERVICE_CHANNELS.has(channel);
  }

  return configuredChannels.includes(channel);
}

export function getCashbackBonusParamKey(saleChannel) {
  const channel = normalizeBenefitChannel(saleChannel);
  if (channel === 'app') return 'app_bonus_percent';
  if (channel === 'ecommerce') return 'ecommerce_bonus_percent';
  return 'pdv_bonus_percent';
}

export function formatBenefitChannelsSummary(params = {}) {
  const configuredChannels = getConfiguredBenefitChannels(params);
  const channels = configuredChannels || DEFAULT_BENEFIT_CHANNELS;
  const labels = channels
    .map((channel) => BENEFIT_CHANNEL_OPTIONS.find((option) => option.value === channel)?.label)
    .filter(Boolean);

  if (labels.length === BENEFIT_CHANNEL_OPTIONS.length) return 'Todos os canais';
  return labels.join(', ') || 'Sem canal liberado';
}
