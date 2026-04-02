export const normalizeSearchText = (value) => {
  if (value === null || value === undefined) return "";
  return String(value)
    .toLowerCase()
    .normalize("NFD")
    .replaceAll(/[\u0300-\u036f]/g, "");
};

export const corrigirTextoQuebrado = (value) => {
  if (value === null || value === undefined) return "";

  const textoOriginal = String(value);
  const scoreQuebrado = (texto) => (texto.match(/[ÃƒÃ‚Ã¢ï¿½]/g) || []).length;

  const tentarTextDecoderUtf8 = (texto) => {
    try {
      const bytes = Uint8Array.from(
        texto,
        (char) => (char.codePointAt(0) ?? 0) & 0xff,
      );
      return new TextDecoder("utf-8").decode(bytes);
    } catch {
      return texto;
    }
  };

  const candidatos = [
    textoOriginal,
    tentarTextDecoderUtf8(textoOriginal),
    tentarTextDecoderUtf8(tentarTextDecoderUtf8(textoOriginal)),
  ];

  let melhor = candidatos[0];
  let melhorScore = scoreQuebrado(melhor);

  for (const candidato of candidatos) {
    const score = scoreQuebrado(candidato);
    if (score < melhorScore) {
      melhor = candidato;
      melhorScore = score;
    }
  }

  return melhor
    .replaceAll("Ã¢ÂÅ’", "âŒ")
    .replaceAll("ÃƒÂ§", "Ã§")
    .replaceAll("ÃƒÂ£", "Ã£")
    .replaceAll("ÃƒÂµ", "Ãµ")
    .replaceAll("ÃƒÂ¡", "Ã¡")
    .replaceAll("ÃƒÂ©", "Ã©")
    .replaceAll("ÃƒÂª", "Ãª")
    .replaceAll("ÃƒÂ­", "Ã­")
    .replaceAll("ÃƒÂ³", "Ã³")
    .replaceAll("ÃƒÂº", "Ãº")
    .replaceAll("Ã¢â‚¬â€œ", "-")
    .replaceAll("Ã‚", "");
};

export const montarMensagemConflitoExclusao = (nomeProduto, detalheServidor) => {
  const detalheLimpo = corrigirTextoQuebrado(detalheServidor || "");
  const correspondenciaQuantidade = detalheLimpo.match(/possui\s+(\d+)/i);
  const quantidadeVariacoes = correspondenciaQuantidade?.[1] || "1";
  const nomeLimpo = corrigirTextoQuebrado(nomeProduto || "Produto");

  return `Produto '${nomeLimpo}' possui ${quantidadeVariacoes} variacao(oes) ativa(s) e nao pode ser desativado. Desative primeiro todas as variacoes.`;
};

export const isKitVirtualProduto = (produto) => {
  const tipoProduto = String(produto?.tipo_produto || "").toUpperCase();
  const tipoKit = String(produto?.tipo_kit || "").toUpperCase();
  return (tipoProduto === "KIT" || tipoProduto === "VARIACAO") && tipoKit === "VIRTUAL";
};

export const isKitFisicoProduto = (produto) => {
  const tipoProduto = String(produto?.tipo_produto || "").toUpperCase();
  const tipoKit = String(produto?.tipo_kit || "").toUpperCase();
  return (tipoProduto === "KIT" || tipoProduto === "VARIACAO") && tipoKit === "FISICO";
};

export const isProdutoComComposicao = (produto) =>
  isKitVirtualProduto(produto) || isKitFisicoProduto(produto);

export const obterEstoqueVisualProduto = (produto) => {
  if (isKitVirtualProduto(produto)) {
    return Number(produto?.estoque_virtual ?? produto?.estoque_atual ?? produto?.estoque ?? 0);
  }

  return Number(produto?.estoque_atual ?? produto?.estoque ?? 0);
};
