export const STATUS_BUSCA_DEVOLUCAO = [
  "finalizada",
  "baixa_parcial",
  "pago_nf",
  "finalizada_devolucao",
];

export const STATUS_DEVOLUCAO_DIRETA = new Set([
  ...STATUS_BUSCA_DEVOLUCAO,
  "finalizada_devolucao_parcial",
]);

export function normalizarStatusVenda(status) {
  return String(status || "")
    .trim()
    .toLowerCase();
}

export function getTipoDevolucaoVenda(venda) {
  const status = normalizarStatusVenda(venda?.status);
  if (status === "devolvida_total" || status === "finalizada_devolucao_total") {
    return "total";
  }
  if (status === "finalizada_devolucao" || status === "finalizada_devolucao_parcial") {
    return "parcial";
  }
  return null;
}

export function getTextoDevolucaoVendaPDV(venda) {
  const tipo = getTipoDevolucaoVenda(venda);
  if (tipo === "parcial") {
    return {
      situacao: "com Devolução Parcial",
      orientacao: "Use Devolução para registrar o saldo restante.",
    };
  }
  if (tipo === "total") {
    return {
      situacao: "Devolvida Integralmente",
      orientacao: "Todos os itens foram devolvidos.",
    };
  }
  return null;
}

export function podeAbrirDevolucaoVenda(venda) {
  return Boolean(venda?.id && STATUS_DEVOLUCAO_DIRETA.has(normalizarStatusVenda(venda.status)));
}

export function getStatusBuscaDevolucao() {
  return [...STATUS_BUSCA_DEVOLUCAO];
}

export function getNumeroVendaParaExibicao(venda) {
  return venda?.numero_venda || venda?.numero || venda?.id || "";
}
