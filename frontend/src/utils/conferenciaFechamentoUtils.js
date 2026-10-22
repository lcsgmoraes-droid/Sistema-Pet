const ESTADOS_CONFERENCIA = new Set(["pendente", "ok", "divergencia"]);

const CLASSES_CONFERENCIA = {
  pendente: "border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900",
  ok: "border border-emerald-300 bg-emerald-50 dark:border-emerald-700 dark:bg-emerald-950/40",
  divergencia: "border border-red-300 bg-red-50 dark:border-red-700 dark:bg-red-950/40",
};

function idPositivo(valor) {
  if (typeof valor === "string" && !/^[1-9]\d*$/.test(valor)) return null;
  if (typeof valor !== "string" && typeof valor !== "number") return null;
  const numero = Number(valor);
  return Number.isSafeInteger(numero) && numero > 0 ? numero : null;
}

function mesmaVenda(item, referencia) {
  if (item?.venda_id == null || referencia?.venda_id == null) return true;
  const vendaId = idPositivo(item.venda_id);
  return vendaId !== null && vendaId === idPositivo(referencia.venda_id);
}

function localizarUnico(registros, id) {
  if (id === null || !Array.isArray(registros)) return null;
  const correspondentes = registros.filter((item) => idPositivo(item?.id) === id);
  return correspondentes.length === 1 ? correspondentes[0] : null;
}

export function localizarVendaConferencia(auditoria, venda) {
  const id = idPositivo(venda?.venda_id ?? venda?.id);
  if (venda?.venda_id != null && venda?.id != null && id !== idPositivo(venda.id)) {
    return null;
  }
  const item = localizarUnico(auditoria?.vendas, id);
  return item && mesmaVenda(item, venda) ? { tipo: "venda", item } : null;
}

export function localizarLancamentoConferencia(auditoria, lancamento) {
  const pagamento = lancamento?.origem === "pagamento";
  const movimento = lancamento?.origem === "movimento";
  if ((!pagamento && !movimento) || typeof lancamento?.id !== "string") return null;
  const referencia = lancamento.id.match(
    pagamento ? /^pagamento-([1-9]\d*)$/ : /^movimento-([1-9]\d*)$/,
  );
  if (!referencia) return null;
  const item = localizarUnico(
    pagamento ? auditoria?.pagamentos : auditoria?.movimentacoes,
    idPositivo(referencia[1]),
  );
  return item && mesmaVenda(item, lancamento)
    ? { tipo: pagamento ? "pagamento" : "movimentacao", item }
    : null;
}

export function estadoConferenciaCaixa(item) {
  if (item?.conferencia_alterada === true) return "pendente";
  if (ESTADOS_CONFERENCIA.has(item?.estado_conferencia)) return item.estado_conferencia;
  return item?.conferido === true ? "ok" : "pendente";
}

export function classeConferenciaCaixa(item) {
  return CLASSES_CONFERENCIA[estadoConferenciaCaixa(item)];
}

export function urlConsultaVendaPdv(id) {
  const vendaId = idPositivo(id);
  return vendaId === null ? null : `/pdv?venda=${vendaId}`;
}
