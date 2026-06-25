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

export function podeAbrirDevolucaoVenda(venda) {
  return Boolean(venda?.id && STATUS_DEVOLUCAO_DIRETA.has(normalizarStatusVenda(venda.status)));
}

export function getStatusBuscaDevolucao() {
  return [...STATUS_BUSCA_DEVOLUCAO];
}

export function getNumeroVendaParaExibicao(venda) {
  return venda?.numero_venda || venda?.numero || venda?.id || "";
}
