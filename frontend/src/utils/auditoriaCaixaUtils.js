import { rotuloFormaPagamento } from "./pdvPaymentDisplay.js";

export const FILTRO_SEM_PAGAMENTOS = "__sem_pagamentos__";
export const TAMANHO_PAGINA_AUDITORIA = 25;

export function selecionarVendasAuditoria(vendas = [], composicao, recorte = "periodo") {
  if (!Array.isArray(composicao?.detalhes) || recorte === "todos") return vendas;
  const idsPeriodo = new Set(composicao.detalhes.map((venda) => String(venda.venda_id)));
  return vendas.filter((venda) =>
    recorte === "outros" ? !idsPeriodo.has(String(venda.id)) : idsPeriodo.has(String(venda.id)),
  );
}

export function paginarAuditoria(itens = [], pagina = 1) {
  const totalPaginas = Math.max(1, Math.ceil(itens.length / TAMANHO_PAGINA_AUDITORIA));
  const paginaAtual = Math.min(Math.max(Math.trunc(Number(pagina)) || 1, 1), totalPaginas);
  const inicio = (paginaAtual - 1) * TAMANHO_PAGINA_AUDITORIA;
  return {
    itens: itens.slice(inicio, inicio + TAMANHO_PAGINA_AUDITORIA),
    pagina: paginaAtual,
    total: itens.length,
    totalPaginas,
  };
}

export function chaveFormaAuditoria(pagamento = {}) {
  return rotuloFormaPagamento(pagamento)
    .normalize("NFD")
    .replaceAll(/[\u0300-\u036f]/g, "")
    .toLocaleLowerCase("pt-BR");
}

export function pagamentosVendaAuditoria(venda = {}) {
  return Array.isArray(venda.pagamentos) ? venda.pagamentos : venda.recebimentos || [];
}

export function naturezaQuitacaoAuditoria(item = {}) {
  const forma = chaveFormaAuditoria(item);
  if (forma.includes("cashback") || (forma.includes("credito") && forma.includes("cliente"))) {
    return "Crédito ou benefício — sem entrada de dinheiro";
  }
  if (item.intervalo_crediario || forma === "crediario" || forma === "boleto") {
    return "Plano a prazo — não é recebimento";
  }
  return "";
}

export function filtrarVendasAuditoria(vendas = [], forma = "") {
  return vendas.filter((venda) => {
    if (!forma) return true;
    const pagamentos = pagamentosVendaAuditoria(venda);
    if (forma === FILTRO_SEM_PAGAMENTOS) return pagamentos.length === 0;
    return [...pagamentos, ...(venda.recebimentos || [])].some(
      (pagamento) => chaveFormaAuditoria(pagamento) === forma,
    );
  });
}

export function filtrarLancamentosAuditoria(lancamentos = [], forma = "") {
  if (forma === FILTRO_SEM_PAGAMENTOS) return [];
  return lancamentos.filter(
    (item) =>
      !forma ||
      chaveFormaAuditoria({
        ...item,
        forma_pagamento: item.forma_pagamento || "Dinheiro",
      }) === forma,
  );
}

export function formasAuditoria(auditoria = {}) {
  const formas = new Map();
  const adicionar = (pagamento) => {
    formas.set(chaveFormaAuditoria(pagamento), rotuloFormaPagamento(pagamento));
  };
  for (const campo of [
    "pagamentos_vendas_por_forma_pagamento",
    "recebimentos_por_forma_pagamento",
    "vendas_por_forma_pagamento",
  ]) {
    for (const forma of Object.keys(auditoria.resumo?.[campo] || {})) {
      adicionar({ forma_pagamento: forma });
    }
  }
  for (const venda of auditoria.vendas || []) {
    for (const pagamento of [...pagamentosVendaAuditoria(venda), ...(venda.recebimentos || [])]) {
      adicionar(pagamento);
    }
  }
  for (const item of [...(auditoria.pagamentos || []), ...(auditoria.movimentacoes || [])]) {
    adicionar({ ...item, forma_pagamento: item.forma_pagamento || "Dinheiro" });
  }
  return Array.from(formas, ([chave, rotulo]) => ({ chave, rotulo })).sort((a, b) =>
    a.rotulo.localeCompare(b.rotulo, "pt-BR"),
  );
}
