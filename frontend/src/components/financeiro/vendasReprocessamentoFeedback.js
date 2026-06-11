export const REPROCESSAMENTO_DESTAQUE_MS = 4500;

export function normalizarVendaIdsFeedback(vendaIds = []) {
  const ids = [];
  const vistos = new Set();

  vendaIds.forEach((rawId) => {
    const vendaId = Number(rawId);
    if (!Number.isFinite(vendaId) || vendaId <= 0 || vistos.has(vendaId)) return;
    ids.push(vendaId);
    vistos.add(vendaId);
  });

  return ids;
}

export function montarFeedbackReprocessamentoVendas({
  vendaIds = [],
  vendasVisiveis = [],
} = {}) {
  const ids = normalizarVendaIdsFeedback(vendaIds);
  if (!ids.length) return { ids: [], focoId: null };

  const idsSet = new Set(ids);
  const focoVisivel = vendasVisiveis
    .map((venda) => Number(venda?.id))
    .find((vendaId) => idsSet.has(vendaId));

  return {
    ids,
    focoId: focoVisivel || ids[0],
  };
}
