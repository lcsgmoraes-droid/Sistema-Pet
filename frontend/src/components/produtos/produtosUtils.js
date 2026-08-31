export const normalizeSearchText = (value) => {
  if (value === null || value === undefined) return "";
  return String(value)
    .toLowerCase()
    .normalize("NFD")
    .replaceAll(/[\u0300-\u036f]/g, "");
};

export const normalizeExpandId = (value) => String(value ?? "");

const normalizarUrlImagemProduto = (url, origin) => {
  if (!url) return null;
  if (/^https?:\/\//i.test(url)) return url;
  if (!origin) return url;
  return `${origin}${url.startsWith("/") ? "" : "/"}${url}`;
};

export const obterFontesImagemProduto = (
  produto,
  origin = typeof window !== "undefined" ? window.location.origin : "",
) => {
  const original = normalizarUrlImagemProduto(produto?.imagem_principal, origin);
  const miniaturaInformada = normalizarUrlImagemProduto(
    produto?.imagem_principal_thumbnail,
    origin,
  );
  const miniaturaDerivada = original?.includes("/originais/")
    ? original.replace("/originais/", "/thumbs/")
    : null;
  const src = miniaturaInformada || miniaturaDerivada || original;

  return {
    src,
    fallbackSrc: original && original !== src ? original : null,
  };
};

export const isExpandIdSelected = (expandedIds, value) => {
  const normalizedId = normalizeExpandId(value);
  return (expandedIds || []).some((id) => normalizeExpandId(id) === normalizedId);
};

export const getKitCompositionFromResponse = (response) => {
  const data = response?.data ?? response;
  return Array.isArray(data?.composicao_kit) ? data.composicao_kit : [];
};

export const getKitComponentAvailableStock = (component) => {
  const stock =
    component?.estoque_disponivel ?? component?.estoque_componente ?? component?.produto_estoque;

  if (stock === null || stock === undefined) return null;

  const normalizedStock = Number(stock);
  return Number.isFinite(normalizedStock) ? normalizedStock : null;
};

export const corrigirTextoQuebrado = (value) => {
  if (value === null || value === undefined) return "";

  const textoOriginal = String(value);
  const scoreQuebrado = (texto) => (texto.match(/[ÃÂâ�]/g) || []).length;

  const tentarTextDecoderUtf8 = (texto) => {
    try {
      const bytes = Uint8Array.from(texto, (char) => (char.codePointAt(0) ?? 0) & 0xff);
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
    .replaceAll("âŒ", "❌")
    .replaceAll("Ã§", "ç")
    .replaceAll("Ã£", "ã")
    .replaceAll("Ãµ", "õ")
    .replaceAll("Ã¡", "á")
    .replaceAll("Ã©", "é")
    .replaceAll("Ãª", "ê")
    .replaceAll("Ã­", "í")
    .replaceAll("Ã³", "ó")
    .replaceAll("Ãº", "ú")
    .replaceAll("â€“", "-")
    .replaceAll("Â", "");
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

export const formatarQuantidadeLote = (valor) => {
  const numero = Number(valor || 0);
  if (!Number.isFinite(numero)) return "0";
  return Number.isInteger(numero)
    ? String(numero)
    : numero.toLocaleString("pt-BR", {
        minimumFractionDigits: 0,
        maximumFractionDigits: 3,
      });
};

export const obterLotesValidadeDisponiveis = (produto) => {
  const lotesResumo = Array.isArray(produto?.lotes_validade_resumo)
    ? produto.lotes_validade_resumo
    : [];
  const lotesCompletos = Array.isArray(produto?.lotes) ? produto.lotes : [];
  const origem = lotesResumo.length > 0 ? lotesResumo : lotesCompletos;

  return origem
    .map((lote) => {
      const quantidadeDisponivel = Number(lote?.quantidade_disponivel ?? lote?.quantidade ?? 0);
      const quantidadeInicial = Number(lote?.quantidade_inicial ?? quantidadeDisponivel);

      return {
        id: lote?.id,
        nome_lote: lote?.nome_lote || lote?.lote || "Sem lote",
        data_validade: lote?.data_validade || null,
        quantidade_inicial: Number.isFinite(quantidadeInicial) ? quantidadeInicial : 0,
        quantidade_disponivel: Number.isFinite(quantidadeDisponivel) ? quantidadeDisponivel : 0,
      };
    })
    .filter((lote) => lote.quantidade_disponivel > 0)
    .sort((a, b) => {
      const dataA = a.data_validade
        ? new Date(a.data_validade).getTime()
        : Number.POSITIVE_INFINITY;
      const dataB = b.data_validade
        ? new Date(b.data_validade).getTime()
        : Number.POSITIVE_INFINITY;

      if (dataA !== dataB) return dataA - dataB;
      return String(a.nome_lote).localeCompare(String(b.nome_lote), "pt-BR");
    });
};

export const montarTooltipLotesValidade = (lotes, formatarData) => {
  if (!lotes?.length) return "Sem lotes disponiveis com saldo.";

  const linhas = lotes.map((lote) => {
    const saldo = formatarQuantidadeLote(lote.quantidade_disponivel);
    const inicial = formatarQuantidadeLote(lote.quantidade_inicial);
    const validade = lote.data_validade ? formatarData(lote.data_validade) : "sem validade";
    const quantidade = lote.quantidade_inicial > 0 ? `${saldo} un de ${inicial}` : `${saldo} un`;

    return `${lote.nome_lote}: ${quantidade} - ${validade}`;
  });

  return ["Lotes com saldo:", ...linhas].join("\n");
};

export const obterCanaisAtivosProduto = (produto) => {
  const ativoLojaFisica = produto?.ativo !== false && produto?.situacao !== false;
  if (!ativoLojaFisica) return [];

  return [
    produto?.anunciar_ecommerce === true ? { key: "ecommerce", label: "E-commerce" } : null,
    produto?.anunciar_app === true ? { key: "app", label: "App" } : null,
  ].filter(Boolean);
};
