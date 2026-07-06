const CAMPOS_CODIGO_PRODUTO = [
  "codigo",
  "sku",
  "codigo_barras",
  "gtin_ean",
  "gtin_ean_tributario",
  "codigos_barras_alternativos",
  "produto_codigo",
  "produto_sku",
  "produto_codigo_barras",
  "produto_gtin_ean",
  "produto_gtin_ean_tributario",
  "produto_codigos_barras_alternativos",
  "ean",
  "ean_tributario",
  "eans",
  "eans_alternativos",
];

export function normalizarCodigoProdutoBusca(valor) {
  return String(valor ?? "")
    .trim()
    .toLowerCase();
}

export function apenasDigitos(valor) {
  return String(valor ?? "").replace(/\D/g, "");
}

export function normalizarListaCodigosProduto(valor) {
  if (valor === null || valor === undefined || valor === "") return [];

  if (Array.isArray(valor)) {
    return valor.flatMap((item) => normalizarListaCodigosProduto(item));
  }

  const texto = String(valor).trim();
  if (!texto) return [];

  try {
    const parsed = JSON.parse(texto);
    if (Array.isArray(parsed)) {
      return normalizarListaCodigosProduto(parsed);
    }
  } catch {
    // Mantem compatibilidade com campos antigos em texto simples.
  }

  return texto
    .split(/[,;\n|]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export function codigosProdutoParaBusca(produto) {
  const codigos = CAMPOS_CODIGO_PRODUTO.flatMap((campo) =>
    normalizarListaCodigosProduto(produto?.[campo]),
  );

  return [...new Set(codigos)];
}

export function produtoCorrespondeBusca(
  produto,
  termo,
  normalizarTexto = normalizarCodigoProdutoBusca,
) {
  const termoNormalizado = normalizarTexto(termo).trim();
  const termosBusca = termoNormalizado.split(/\s+/).filter(Boolean);

  if (termosBusca.length === 0) return true;

  const codigos = codigosProdutoParaBusca(produto);
  const camposTexto = [
    produto?.nome,
    produto?.descricao,
    produto?.descricao_curta,
    ...codigos,
  ].map((value) => normalizarTexto(value || ""));
  const camposDigitos = codigos.map((codigo) => apenasDigitos(codigo));

  return termosBusca.every((termoBusca) => {
    const correspondeTexto = camposTexto.some((campo) => campo.includes(termoBusca));
    if (correspondeTexto) return true;

    const termoDigitos = apenasDigitos(termoBusca);
    if (!termoDigitos) return false;

    return camposDigitos.some((campo) => campo.includes(termoDigitos));
  });
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
          termoDigitos.length >= 6 && codigoDigitos.length >= 6 && codigoDigitos === termoDigitos
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
