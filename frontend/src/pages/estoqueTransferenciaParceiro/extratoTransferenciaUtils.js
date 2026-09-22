export function criarExtratoTransferenciaVazio(overrides = {}) {
  const { totais: totaisOverrides = {}, ...demaisOverrides } = overrides;
  return {
    parceiro_id: null,
    parceiro_nome: null,
    items: [],
    totais: {
      saldo_anterior: 0,
      total_debitos: 0,
      total_creditos: 0,
      saldo_final: 0,
      total_lancamentos: 0,
      total_documentos: 0,
      documentos_em_aberto: 0,
      ...totaisOverrides,
    },
    ...demaisOverrides,
  };
}

export function filtrarItensExtratoTransferencia(items, foco = "todos") {
  const lista = Array.isArray(items) ? items : [];
  if (foco === "dividas") return lista.filter((item) => item.tipo === "divida");
  if (foco === "creditos") return lista.filter((item) => Number(item.credito || 0) > 0);
  if (foco === "em_aberto") {
    return lista.filter(
      (item) =>
        item.tipo === "divida" &&
        Number(item.saldo_documento || 0) > 0 &&
        ["pendente", "parcial", "vencido"].includes(item.conta_status),
    );
  }
  return lista;
}
