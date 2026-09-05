import {
  CANAL_APP,
  CANAL_ECOMMERCE,
  CANAL_LOJA_FISICA,
  CANAL_WHATSAPP,
  normalizeSalesChannel,
} from "../../utils/salesChannel";

export function obterCanalVendaFinanceiro(venda) {
  return normalizeSalesChannel(
    venda?.canal_venda ||
      venda?.origem_canal_venda ||
      venda?.canal ||
      venda?.origem ||
      venda?.origem_loja_virtual,
    CANAL_LOJA_FISICA,
  );
}

export const VENDAS_FINANCEIRO_CHANNEL_FILTERS = [
  {
    value: "",
    label: "Consolidado",
    filterLabel: "Todos os canais",
    description: "Todos os canais",
    activeClass: "bg-slate-900 text-white border-slate-900",
    idleClass: "bg-white text-slate-700 border-slate-200 hover:border-slate-300",
  },
  {
    value: CANAL_LOJA_FISICA,
    label: "ERP/PDV",
    filterLabel: "ERP/PDV",
    description: "Loja fisica",
    activeClass: "bg-blue-600 text-white border-blue-600",
    idleClass: "bg-blue-50 text-blue-700 border-blue-200 hover:border-blue-300",
  },
  {
    value: CANAL_APP,
    label: "App",
    filterLabel: "App",
    description: "Aplicativo",
    activeClass: "bg-emerald-600 text-white border-emerald-600",
    idleClass: "bg-emerald-50 text-emerald-700 border-emerald-200 hover:border-emerald-300",
  },
  {
    value: CANAL_ECOMMERCE,
    label: "E-commerce",
    filterLabel: "E-commerce",
    description: "Site da loja",
    activeClass: "bg-purple-600 text-white border-purple-600",
    idleClass: "bg-purple-50 text-purple-700 border-purple-200 hover:border-purple-300",
  },
  {
    value: CANAL_WHATSAPP,
    label: "WhatsApp",
    filterLabel: "WhatsApp",
    description: "Atendimento pelo WhatsApp",
    activeClass: "bg-emerald-600 text-white border-emerald-600",
    idleClass: "bg-emerald-50 text-emerald-700 border-emerald-200 hover:border-emerald-300",
  },
];
