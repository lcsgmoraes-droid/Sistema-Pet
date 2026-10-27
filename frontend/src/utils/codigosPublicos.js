function primeiroCodigo(...valores) {
  const valor = valores.find((item) => item != null && String(item).trim());
  return valor === undefined ? "" : String(valor).trim();
}

// IDs são referências técnicas. Nunca usá-los como código alternativo de exibição.
export function obterCodigoPessoaPublico(pessoa) {
  const codigoProprio =
    pessoa &&
    !["cliente_id", "tutor_id", "pessoa_id", "customer_id"].some((chave) => chave in pessoa)
      ? pessoa.codigo
      : undefined;
  return primeiroCodigo(
    pessoa?.cliente_codigo,
    pessoa?.codigo_cliente,
    pessoa?.cod_cliente,
    pessoa?.tutor_codigo,
    pessoa?.codigo_tutor,
    pessoa?.pessoa_codigo,
    pessoa?.codigo_pessoa,
    pessoa?.customer_code,
    pessoa?.cliente?.codigo,
    pessoa?.tutor?.codigo,
    pessoa?.pessoa?.codigo,
    pessoa?.customer?.codigo,
    codigoProprio,
  );
}

export function obterCodigoProdutoPublico(produto) {
  return primeiroCodigo(
    produto?.produto_codigo,
    produto?.codigo_produto,
    produto?.produto?.codigo,
    produto?.codigo,
    produto?.produto_sku,
    produto?.sku,
    produto?.produto?.sku,
    produto?.codigo_barras,
    produto?.produto?.codigo_barras,
  );
}
