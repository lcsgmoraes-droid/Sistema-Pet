export const ALTERAR_PRECO_GRANEL_PADRAO = false;

export function montarCamposAtualizacaoPrecoGranel({
  deveAlterarPreco = false,
  precoVendaSugerido = 0,
} = {}) {
  const precoVenda = Number(precoVendaSugerido);

  if (!deveAlterarPreco || !Number.isFinite(precoVenda) || precoVenda <= 0) {
    return {
      atualizar_preco_venda_granel: false,
      preco_venda_granel: null,
    };
  }

  return {
    atualizar_preco_venda_granel: true,
    preco_venda_granel: Number(precoVenda.toFixed(2)),
  };
}
