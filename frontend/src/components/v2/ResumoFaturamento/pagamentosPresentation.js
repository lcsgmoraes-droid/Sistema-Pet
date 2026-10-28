export const MOTIVOS_DIFERENCA_PAGAMENTO = {
  devolucao: "Devoluções consideradas nas vendas",
  pagamento_acima_total_venda: "Pagamentos acima do valor aplicado às vendas",
  quitacao_sem_historico_correspondente: "Quitação sem histórico correspondente",
};

export function motivoDiferencaPagamento(motivo) {
  return MOTIVOS_DIFERENCA_PAGAMENTO[motivo] || "Diferença entre pagamentos e valor das vendas";
}

export function diferencasPorVenda(composicao) {
  return new Map((composicao?.diferencas_pagamentos || []).map((item) => [item.venda_id, item]));
}

export function pagamentoLegadoParaConferir(venda) {
  return (venda?.pagamentos || []).find((pagamento) =>
    ["venda_legada", "conta_legada"].includes(pagamento.origem),
  );
}

export function pagamentoPrecisaConferencia(venda, diferenca) {
  return Boolean(
    (diferenca && diferenca.motivo !== "devolucao") || pagamentoLegadoParaConferir(venda),
  );
}
