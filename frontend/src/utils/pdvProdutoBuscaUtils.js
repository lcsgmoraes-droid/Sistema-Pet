const CAMPOS_CODIGO_PRODUTO = [
  "codigo",
  "sku",
  "codigo_barras",
  "gtin_ean",
  "gtin_ean_tributario",
  "produto_codigo",
  "produto_sku",
  "produto_codigo_barras",
  "produto_gtin_ean",
  "produto_gtin_ean_tributario",
  "ean",
  "ean_tributario",
];

export function normalizarCodigoProdutoBusca(valor) {
  return String(valor ?? "").trim().toLowerCase();
}

export function apenasDigitos(valor) {
  return String(valor ?? "").replace(/\D/g, "");
}

export function codigosProdutoParaBusca(produto) {
  return CAMPOS_CODIGO_PRODUTO.map((campo) => produto?.[campo]).filter(Boolean);
}

export function encontrarProdutoPorCodigo(produtos, termo) {
  const termoNormalizado = normalizarCodigoProdutoBusca(termo);
  const termoDigitos = apenasDigitos(termo);

  if (!termoNormalizado) return null;

  return (
    produtos.find((produto) =>
      codigosProdutoParaBusca(produto).some((codigo) => {
        const codigoNormalizado = normalizarCodigoProdutoBusca(codigo);
        if (codigoNormalizado === termoNormalizado) return true;

        const codigoDigitos = apenasDigitos(codigo);
        return (
          termoDigitos.length >= 6 &&
          codigoDigitos.length >= 6 &&
          codigoDigitos === termoDigitos
        );
      }),
    ) || null
  );
}

export function deveAdicionarProdutoAutomaticamente({
  matchExato,
  termo,
  leituraScannerDetectada,
  modoVisualizacao,
  ultimoAutoAddProduto,
}) {
  if (!matchExato || modoVisualizacao) return false;

  const termoNormalizado = normalizarCodigoProdutoBusca(termo);
  if (!termoNormalizado || ultimoAutoAddProduto === termoNormalizado) {
    return false;
  }

  return Boolean(leituraScannerDetectada || apenasDigitos(termo).length >= 6);
}
