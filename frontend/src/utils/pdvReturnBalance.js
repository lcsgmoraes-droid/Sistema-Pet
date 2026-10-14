export function criarMapaSaldosDevolucao(venda, resposta) {
  if (!Array.isArray(venda?.itens) || !Array.isArray(resposta?.itens)) {
    throw new Error("Não foi possível consultar o saldo dos itens da venda");
  }

  const saldos = Object.fromEntries(resposta.itens.map((item) => [item.item_id, item]));
  for (const item of venda.itens) {
    const saldo = saldos[item.id];
    const vendida = Number(item.quantidade);
    const devolvida = Number(saldo?.quantidade_devolvida);
    const disponivel = Number(saldo?.quantidade_disponivel);
    if (
      !saldo ||
      !Number.isFinite(vendida) ||
      !Number.isFinite(devolvida) ||
      !Number.isFinite(disponivel) ||
      vendida < 0 ||
      devolvida < 0 ||
      disponivel < 0 ||
      devolvida + disponivel > vendida + 0.000001
    ) {
      throw new Error("Não foi possível conferir o saldo devolvível desta venda");
    }
  }
  return saldos;
}

export function quantidadeDisponivelDevolucao(saldos, itemId) {
  return Number(saldos?.[itemId]?.quantidade_disponivel) || 0;
}
