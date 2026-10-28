export function atalhoDiretoCorePet(vendaId, abrir) {
  return abrir && /^[1-9]\d*$/.test(String(vendaId || ""));
}

export async function carregarNotaDiretaCorePet(api, vendaId) {
  if (!atalhoDiretoCorePet(vendaId, true)) throw new Error("Identificador da venda inválido.");
  const { data } = await api.get(`/nfe/vendas/${encodeURIComponent(vendaId)}/detalhes`);
  if (data?.provedor !== "intnfe" || String(data.id) !== String(vendaId)) {
    throw new Error("Os dados retornados não correspondem à nota do CorePet solicitada.");
  }
  return { ...data, venda_id: Number(vendaId), valor: data.totais?.valor_total };
}
