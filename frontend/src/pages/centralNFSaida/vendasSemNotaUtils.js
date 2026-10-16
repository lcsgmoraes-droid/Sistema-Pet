export function vendaCompativelNfeNfce(venda) {
  return venda.compativel_nfe_nfce === true;
}

export function vendasSelecionadasParaEmissao(vendas, selecionados) {
  return vendas.filter((venda) => vendaCompativelNfeNfce(venda) && selecionados.has(venda.id));
}

export function selecionarPaginaCompativel(vendas, selecionados) {
  const compativeis = vendas.filter(vendaCompativelNfeNfce);
  const todas = compativeis.length > 0 && compativeis.every((venda) => selecionados.has(venda.id));
  return todas ? new Set() : new Set(compativeis.map((venda) => venda.id));
}
