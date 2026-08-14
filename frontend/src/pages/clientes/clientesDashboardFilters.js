export const CLIENTES_DASHBOARD_VIEWS = {
  ativos: {
    title: "Clientes ativos",
    description: "Clientes ativos da empresa.",
  },
  vip_em_risco: {
    title: "VIPs em risco",
    description: "Clientes VIP sem compra há mais de 20 dias.",
  },
  inativos_90_dias: {
    title: "Clientes inativos",
    description: "Clientes sem compra há mais de 90 dias ou que ainda não compraram.",
  },
  novos_promissores: {
    title: "Novos clientes promissores",
    description: "Clientes do segmento Novo com ticket médio acima de R$ 200.",
  },
  sem_whatsapp: {
    title: "Clientes sem WhatsApp",
    description: "Clientes ativos sem celular cadastrado.",
  },
};

export function normalizarVisaoDashboardClientes(searchParams) {
  const visao = searchParams?.get?.("visao") || "";
  return CLIENTES_DASHBOARD_VIEWS[visao] ? visao : "";
}
