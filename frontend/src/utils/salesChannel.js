export const CANAL_APP = "app";
export const CANAL_ECOMMERCE = "ecommerce";
export const CANAL_LOJA_FISICA = "loja_fisica";

const CHANNEL_ALIASES = {
  pdv: CANAL_LOJA_FISICA,
  loja: CANAL_LOJA_FISICA,
  loja_fisica: CANAL_LOJA_FISICA,
  "loja-fisica": CANAL_LOJA_FISICA,
  balcao: CANAL_LOJA_FISICA,
  caixa: CANAL_LOJA_FISICA,
  app: CANAL_APP,
  aplicativo: CANAL_APP,
  mobile: CANAL_APP,
  app_movel: CANAL_APP,
  ecommerce: CANAL_ECOMMERCE,
  "e-commerce": CANAL_ECOMMERCE,
  e_commerce: CANAL_ECOMMERCE,
  loja_virtual: CANAL_ECOMMERCE,
  site: CANAL_ECOMMERCE,
  web: CANAL_ECOMMERCE,
  app_funcionario: "app_funcionario",
  banho_tosa: "banho_tosa",
  "banho-e-tosa": "banho_tosa",
  "banho e tosa": "banho_tosa",
  bt: "banho_tosa",
  veterinario: "veterinario",
  veterinaria: "veterinario",
  vet: "veterinario",
  clinica: "veterinario",
};

function channelKey(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "_");
}

export function normalizeSalesChannel(value, defaultChannel = CANAL_ECOMMERCE) {
  const key = channelKey(value);
  if (!key) return defaultChannel;
  return CHANNEL_ALIASES[key] || key;
}

export function isOnlineSalesChannel(value) {
  return [CANAL_APP, CANAL_ECOMMERCE].includes(normalizeSalesChannel(value));
}

export function benefitChannelFromSalesChannel(value) {
  const channel = normalizeSalesChannel(value, CANAL_LOJA_FISICA);
  if (
    [CANAL_APP, CANAL_ECOMMERCE, CANAL_LOJA_FISICA, "banho_tosa", "veterinario"].includes(channel)
  ) {
    return channel;
  }
  return CANAL_LOJA_FISICA;
}

export function getSalesChannelInfo(value) {
  const channel = normalizeSalesChannel(value, CANAL_LOJA_FISICA);
  return (
    {
      [CANAL_ECOMMERCE]: {
        value: CANAL_ECOMMERCE,
        cor: "border-l-purple-500",
        bg: "bg-purple-50",
        border: "border-purple-200 hover:border-purple-300",
        icon: "\uD83D\uDED2",
        label: "Ecommerce",
      },
      [CANAL_APP]: {
        value: CANAL_APP,
        cor: "border-l-green-500",
        bg: "bg-green-50",
        border: "border-green-200 hover:border-green-300",
        icon: "\uD83D\uDCF1",
        label: "App",
      },
      app_funcionario: {
        value: "app_funcionario",
        cor: "border-l-cyan-500",
        bg: "bg-cyan-50",
        border: "border-cyan-200 hover:border-cyan-300",
        iconKey: "smartphone",
        iconColor: "text-cyan-700",
        label: "App Funcionario",
        title: "Venda pelo app do funcionario",
      },
      [CANAL_LOJA_FISICA]: {
        value: CANAL_LOJA_FISICA,
        cor: "border-l-blue-500",
        bg: "bg-blue-50",
        border: "border-blue-200 hover:border-blue-300",
        icon: "\uD83C\uDFEA",
        label: "PDV",
      },
      banho_tosa: {
        value: "banho_tosa",
        cor: "border-l-pink-500",
        bg: "bg-pink-50",
        border: "border-pink-200 hover:border-pink-300",
        iconKey: "scissors",
        iconColor: "text-pink-700",
        label: "Banho & Tosa",
        title: "Venda gerada pelo modulo Banho & Tosa",
      },
      veterinario: {
        value: "veterinario",
        cor: "border-l-amber-500",
        bg: "bg-yellow-50",
        border: "border-amber-200 hover:border-amber-300",
        iconKey: "stethoscope",
        iconColor: "text-amber-700",
        label: "Veterinario",
        title: "Venda gerada pelo modulo Veterinario",
      },
    }[channel] || {
      value: CANAL_LOJA_FISICA,
      cor: "border-l-gray-400",
      bg: "bg-gray-50",
      border: "border-gray-200 hover:border-blue-300",
      icon: "\uD83C\uDFEA",
      label: "PDV",
    }
  );
}
