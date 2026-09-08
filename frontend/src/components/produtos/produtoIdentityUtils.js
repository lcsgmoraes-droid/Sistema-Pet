export function separarAliasesSku(texto) {
  const aliases = String(texto || "")
    .split(/[\n,;]+/)
    .map((sku) => sku.trim())
    .filter(Boolean);
  return [...new Map(aliases.map((sku) => [sku.toUpperCase(), sku])).values()];
}

export function campoPreservadoNaFusao(campo, estrategia) {
  return (
    estrategia === "manter_principal" &&
    (["codigo", "nome", "unidade", "codigo_barras", "codigos_barras_alternativos"].includes(
      campo,
    ) ||
      campo.startsWith("preco_") ||
      campo.startsWith("promocao_"))
  );
}

export function podeAplicarFusao({
  preview,
  previewAtual,
  confirmado,
  preservarBling,
  aliases,
  ocupado,
  estrategia,
  observacao = "",
}) {
  return Boolean(
    previewAtual &&
    preview?.preview_token &&
    confirmado &&
    !ocupado &&
    Number(preview.filas_pendentes || 0) === 0 &&
    (!preview.conflito_bling || preservarBling) &&
    aliases.length <= 20 &&
    aliases.every((sku) => sku.length <= 100) &&
    ((estrategia !== "manter_principal" && aliases.length === 0) || observacao.trim().length >= 10),
  );
}
