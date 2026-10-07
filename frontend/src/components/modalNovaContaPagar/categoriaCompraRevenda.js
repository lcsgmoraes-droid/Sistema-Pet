const NOME_COMPRA_REVENDA_PADRAO = "produto para revenda";

export const ehCategoriaCompraRevendaPadrao = (categoria) =>
  String(categoria?.nome || "")
    .trim()
    .toLocaleLowerCase("pt-BR") === NOME_COMPRA_REVENDA_PADRAO && !categoria?.dre_subcategoria_id;

export const dadosAoSelecionarCategoria = (dados, categoria, categoriaId) => {
  const compraRevenda = ehCategoriaCompraRevendaPadrao(categoria);
  const afetaDre = compraRevenda ? false : dados.afeta_dre;
  return {
    ...dados,
    categoria_id: categoriaId,
    afeta_dre: afetaDre,
    dre_subcategoria_id: afetaDre ? categoria?.dre_subcategoria_id || null : null,
    tipo_despesa_id: compraRevenda ? null : dados.tipo_despesa_id,
  };
};
