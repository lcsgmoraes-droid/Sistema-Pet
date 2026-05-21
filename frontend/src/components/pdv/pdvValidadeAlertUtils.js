export function extractProdutoIdsCarrinho(itens = []) {
  const ids = new Set();

  itens.forEach((item) => {
    const id = item?.produto_id ?? item?.produto?.id ?? item?.id;
    const numericId = Number(id);
    if (Number.isFinite(numericId) && numericId > 0) {
      ids.add(numericId);
    }
  });

  return Array.from(ids);
}

export function buildValidadePdvQuery(produtoIds = []) {
  const params = new URLSearchParams();
  produtoIds.forEach((id) => params.append("produto_ids", String(id)));
  return params.toString();
}

export function buildValidadePdvMessage(alertas = []) {
  const nomes = alertas
    .map((alerta) => {
      const nome = alerta?.produto_nome || alerta?.produto?.nome;
      if (!nome) return null;
      const quantidade = Number(alerta?.quantidade_bloqueada || 0);
      return quantidade > 0 ? `${nome} (${quantidade})` : nome;
    })
    .filter(Boolean);

  if (!nomes.length) {
    return "";
  }

  return `Conferir produtos com validade em risco: ${nomes.join(", ")}.`;
}
