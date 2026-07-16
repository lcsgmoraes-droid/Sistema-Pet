export function createEmptyDashboardSummary() {
  return {
    saldo_atual: 0,
    contas_receber: { total: 0, vencidas: 0 },
    contas_pagar: { total: 0, vencidas: 0 },
    vendas_periodo: {
      quantidade: 0,
      valor_total: 0,
      faturamento_bruto: 0,
      finalizadas: 0,
      ticket_medio: 0,
    },
    fluxo_periodo: { entradas: 0, saidas: 0, lucro: 0 },
  };
}

export function createEmptyManagementMetrics() {
  return {
    vips_inativos: { quantidade: 0, impacto: "R$ 0,00" },
    clientes_inativos: { quantidade: 0, impacto: "Reativação pendente" },
    clientes_endividados: { quantidade: 0, impacto: "R$ 0,00" },
    oportunidades_novos: { quantidade: 0, impacto: "R$ 0,00/mês" },
    whatsapp_inativo: { quantidade: 0, impacto: "Canal de contato ausente" },
    total_clientes: 0,
  };
}

function numberValue(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : 0;
}

export function getPeriodLabel(periodDays) {
  return Number(periodDays) === 1 ? "Hoje" : `Últimos ${periodDays} dias`;
}

export function calculateDashboardIndicators(summary = createEmptyDashboardSummary()) {
  const inflows = numberValue(summary?.fluxo_periodo?.entradas);
  const outflows = numberValue(summary?.fluxo_periodo?.saidas);
  const cashResult = numberValue(summary?.fluxo_periodo?.lucro);
  const overdueReceivable = numberValue(summary?.contas_receber?.vencidas);
  const overduePayable = numberValue(summary?.contas_pagar?.vencidas);
  const salesCount = numberValue(summary?.vendas_periodo?.quantidade);

  return {
    inflows,
    outflows,
    cashResult,
    overdueReceivable,
    overduePayable,
    cashMargin: inflows > 0 ? (cashResult / inflows) * 100 : null,
    expenseCoverage: outflows > 0 ? (inflows / outflows) * 100 : null,
    hasMovement: salesCount > 0 || inflows !== 0 || outflows !== 0,
  };
}

export function getExecutiveStatus(summary = createEmptyDashboardSummary()) {
  const indicators = calculateDashboardIndicators(summary);
  const hasOverdue = indicators.overdueReceivable > 0 || indicators.overduePayable > 0;

  if (!indicators.hasMovement) {
    return {
      tone: "neutral",
      title: "Aguardando movimentação",
      description: "Registre vendas e lançamentos para acompanhar a evolução do negócio.",
    };
  }

  if (indicators.cashResult < 0 && hasOverdue) {
    return {
      tone: "critical",
      title: "Ação necessária",
      description: "O caixa do período está negativo e existem contas vencidas.",
    };
  }

  if (indicators.cashResult < 0) {
    return {
      tone: "critical",
      title: "Caixa pressionado",
      description: "As saídas registradas superaram as entradas no período.",
    };
  }

  if (hasOverdue) {
    return {
      tone: "warning",
      title: "Operação com pendências",
      description: "O caixa está positivo, mas há recebimentos ou pagamentos vencidos.",
    };
  }

  return {
    tone: "positive",
    title: "Operação em dia",
    description: "O caixa do período está positivo e não há valores vencidos.",
  };
}
