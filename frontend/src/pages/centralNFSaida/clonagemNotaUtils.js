export function referenciaClonagem(nota) {
  return {
    provedor: nota.provedor === "intnfe" ? "intnfe" : "bling",
    venda_id: nota.venda_id || undefined,
    nfe_id: String(nota.id || ""),
    modelo: Number(nota.modelo) || 55,
  };
}

export function atualizarCampoClone(dados, caminho, valor) {
  const copia = structuredClone(dados);
  const partes = caminho.split(".");
  let destino = copia;
  for (const parte of partes.slice(0, -1)) destino = destino[parte] ??= {};
  destino[partes.at(-1)] = valor;
  if (partes[0] === "produtos" && ["quantidade", "valorUnitario"].includes(partes.at(-1))) {
    const item = copia.produtos[Number(partes[1])];
    item.valorTotal =
      Math.round((Number(item.quantidade) * Number(item.valorUnitario) + Number.EPSILON) * 100) /
      100;
  }
  return copia;
}

export function totalClonagem(dados = {}) {
  const produtos = (dados.produtos || []).reduce(
    (soma, item) =>
      soma +
      Number(item.valorTotal || 0) -
      Number(item.desconto || 0) +
      Number(item.impostos?.ipi?.valor || 0),
    0,
  );
  return Math.round((produtos + Number(dados.frete?.valor || 0) + Number.EPSILON) * 100) / 100;
}
