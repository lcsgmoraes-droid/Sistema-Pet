export const numeroSeguro = (valor) => {
  const numero = Number(valor);
  return Number.isFinite(numero) ? numero : 0;
};

export const UNIDADE_COMPRA_PADRAO = "UN";

export const UNIDADES_COMPRA_OPCOES = [
  { value: "UN", label: "UN - Unidade", embalagem: false },
  { value: "CX", label: "CX - Caixa", embalagem: true },
  { value: "FD", label: "FD - Fardo", embalagem: true },
  { value: "PCT", label: "PCT - Pacote", embalagem: true },
  { value: "SC", label: "SC - Saco", embalagem: true },
];

const UNIDADES_COMPRA_VALIDAS = new Set(UNIDADES_COMPRA_OPCOES.map((opcao) => opcao.value));
const UNIDADES_COMPRA_COM_EMBALAGEM = new Set(
  UNIDADES_COMPRA_OPCOES.filter((opcao) => opcao.embalagem).map((opcao) => opcao.value),
);

export const textoNumeroSeguro = (valor, fallback = "0") => {
  if (valor === null || valor === undefined || valor === "") {
    return fallback;
  }

  return String(valor);
};

export const normalizarTextoBusca = (texto = "") =>
  String(texto || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/\s+/g, " ")
    .trim();

export const textoContemTokens = (texto, busca) => {
  const tokens = normalizarTextoBusca(busca).split(" ").filter(Boolean);
  if (tokens.length === 0) {
    return true;
  }

  const base = normalizarTextoBusca(texto);
  return tokens.every((token) => base.includes(token));
};

export const normalizarUnidadeCompraPedido = (valor) => {
  const unidade = String(valor || UNIDADE_COMPRA_PADRAO)
    .trim()
    .toUpperCase();
  return UNIDADES_COMPRA_VALIDAS.has(unidade) ? unidade : UNIDADE_COMPRA_PADRAO;
};

export const normalizarQuantidadePorEmbalagemPedido = (unidadeCompra, valor) => {
  const unidade = normalizarUnidadeCompraPedido(unidadeCompra);
  if (!UNIDADES_COMPRA_COM_EMBALAGEM.has(unidade)) {
    return 1;
  }

  if (valor === null || valor === undefined || valor === "") {
    return null;
  }

  const quantidade = numeroSeguro(valor);
  return quantidade > 0 ? quantidade : null;
};

export const calcularQuantidadeTotalUnidadesPedido = (item = {}) => {
  const unidade = normalizarUnidadeCompraPedido(item.unidade_compra);
  const quantidadePorEmbalagem = normalizarQuantidadePorEmbalagemPedido(
    unidade,
    item.quantidade_por_embalagem,
  );
  return numeroSeguro(item.quantidade_pedida) * (quantidadePorEmbalagem || 1);
};

export const formatarNumeroPedidoCurto = (valor) => {
  const numero = numeroSeguro(valor);
  return numero.toLocaleString("pt-BR", {
    minimumFractionDigits: numero % 1 === 0 ? 0 : 2,
    maximumFractionDigits: 2,
  });
};

export const formatarQuantidadeCompraPedido = (item = {}) => {
  const unidade = normalizarUnidadeCompraPedido(item.unidade_compra);
  const quantidade = numeroSeguro(item.quantidade_pedida);
  const quantidadeTexto = formatarNumeroPedidoCurto(quantidade);
  const quantidadePorEmbalagem = normalizarQuantidadePorEmbalagemPedido(
    unidade,
    item.quantidade_por_embalagem,
  );

  if (
    !UNIDADES_COMPRA_COM_EMBALAGEM.has(unidade) ||
    !quantidadePorEmbalagem ||
    quantidadePorEmbalagem <= 1
  ) {
    return `${quantidadeTexto} ${unidade}`;
  }

  const totalUnidades = quantidade * quantidadePorEmbalagem;
  return `${quantidadeTexto} ${unidade} (${formatarNumeroPedidoCurto(totalUnidades)} unid)`;
};

export const montarTooltipQuantidadeCompraPedido = (item = {}) => {
  const unidade = normalizarUnidadeCompraPedido(item.unidade_compra);
  const quantidadePorEmbalagem = normalizarQuantidadePorEmbalagemPedido(
    unidade,
    item.quantidade_por_embalagem,
  );

  if (!UNIDADES_COMPRA_COM_EMBALAGEM.has(unidade)) {
    return "";
  }

  if (!quantidadePorEmbalagem) {
    return `Quantidade por ${unidade} ainda nao informada. O pedido sera enviado sem conversao para unidades.`;
  }

  if (quantidadePorEmbalagem <= 1) {
    return "";
  }

  const totalUnidades = calcularQuantidadeTotalUnidadesPedido(item);
  return `Cada ${unidade} contem ${formatarNumeroPedidoCurto(quantidadePorEmbalagem)} unidades vendaveis. Este item representa ${formatarNumeroPedidoCurto(totalUnidades)} unidades no total.`;
};

export const normalizarItemPedido = (item = {}) => {
  const quantidade = numeroSeguro(item.quantidade_pedida);
  const unidadeCompra = normalizarUnidadeCompraPedido(item.unidade_compra);
  const quantidadePorEmbalagem = normalizarQuantidadePorEmbalagemPedido(
    unidadeCompra,
    item.quantidade_por_embalagem,
  );
  const quantidadeTotalUnidadesInformada = numeroSeguro(item.quantidade_total_unidades);
  const quantidadeTotalUnidades =
    quantidadeTotalUnidadesInformada > 0
      ? quantidadeTotalUnidadesInformada
      : quantidade * (quantidadePorEmbalagem || 1);
  const preco = numeroSeguro(item.preco_unitario);
  const desconto = numeroSeguro(item.desconto_item);
  const totalInformado = Number(item.total ?? item.valor_total);
  const total = Number.isFinite(totalInformado)
    ? totalInformado
    : (preco - desconto) * quantidadeTotalUnidades;

  return {
    produto_id: Number(item.produto_id),
    produto_nome: item.produto_nome || item.nome || `Produto ${item.produto_id}`,
    produto_codigo: item.produto_codigo || item.codigo || item.sku || "",
    quantidade_pedida: quantidade,
    unidade_compra: unidadeCompra,
    quantidade_por_embalagem: quantidadePorEmbalagem,
    quantidade_total_unidades: quantidadeTotalUnidades,
    preco_unitario: preco,
    desconto_item: desconto,
    total,
  };
};

export const clonarItensPedido = (itens = []) => itens.map((item) => normalizarItemPedido(item));

export const consolidarItensPedido = (
  itensBase = [],
  itensAdicionais = [],
  estrategia = "somar",
) => {
  const mapa = new Map();

  const adicionarOuSomarItem = (item) => {
    const normalizado = normalizarItemPedido(item);
    const produtoId = Number(normalizado.produto_id);
    const chave = [
      produtoId,
      normalizado.unidade_compra,
      normalizado.quantidade_por_embalagem ?? "indefinida",
    ].join(":");

    if (!Number.isFinite(produtoId) || produtoId <= 0) {
      return;
    }

    const existente = mapa.get(chave);
    if (!existente) {
      mapa.set(chave, normalizado);
      return;
    }

    if (estrategia === "manter_existente") {
      const preco = numeroSeguro(existente.preco_unitario);
      const desconto = numeroSeguro(existente.desconto_item);
      const quantidade = numeroSeguro(existente.quantidade_pedida);
      const quantidadeTotalUnidades = calcularQuantidadeTotalUnidadesPedido({
        quantidade_pedida: quantidade,
        unidade_compra: existente.unidade_compra,
        quantidade_por_embalagem: existente.quantidade_por_embalagem,
      });

      mapa.set(chave, {
        ...normalizado,
        ...existente,
        preco_unitario: preco,
        desconto_item: desconto,
        quantidade_pedida: quantidade,
        quantidade_total_unidades: quantidadeTotalUnidades,
        total: (preco - desconto) * quantidadeTotalUnidades,
      });
      return;
    }

    if (estrategia === "maior_quantidade") {
      const quantidadeExistente = numeroSeguro(existente.quantidade_pedida);
      const quantidadeNova = numeroSeguro(normalizado.quantidade_pedida);
      const itemEscolhido = quantidadeNova >= quantidadeExistente ? normalizado : existente;
      const preco = numeroSeguro(itemEscolhido.preco_unitario);
      const desconto = numeroSeguro(itemEscolhido.desconto_item);
      const quantidade = Math.max(quantidadeExistente, quantidadeNova);
      const quantidadeTotalUnidades = calcularQuantidadeTotalUnidadesPedido({
        quantidade_pedida: quantidade,
        unidade_compra: itemEscolhido.unidade_compra,
        quantidade_por_embalagem: itemEscolhido.quantidade_por_embalagem,
      });

      mapa.set(chave, {
        ...existente,
        ...normalizado,
        ...itemEscolhido,
        quantidade_pedida: quantidade,
        quantidade_total_unidades: quantidadeTotalUnidades,
        preco_unitario: preco,
        desconto_item: desconto,
        total: (preco - desconto) * quantidadeTotalUnidades,
      });
      return;
    }

    const preco =
      numeroSeguro(normalizado.preco_unitario) || numeroSeguro(existente.preco_unitario);
    const desconto =
      numeroSeguro(normalizado.desconto_item) || numeroSeguro(existente.desconto_item);
    const quantidade =
      numeroSeguro(existente.quantidade_pedida) + numeroSeguro(normalizado.quantidade_pedida);
    const quantidadeTotalUnidades = calcularQuantidadeTotalUnidadesPedido({
      quantidade_pedida: quantidade,
      unidade_compra: normalizado.unidade_compra,
      quantidade_por_embalagem: normalizado.quantidade_por_embalagem,
    });

    mapa.set(chave, {
      ...existente,
      ...normalizado,
      preco_unitario: preco,
      desconto_item: desconto,
      quantidade_pedida: quantidade,
      quantidade_total_unidades: quantidadeTotalUnidades,
      total: (preco - desconto) * quantidadeTotalUnidades,
    });
  };

  clonarItensPedido(itensBase).forEach(adicionarOuSomarItem);
  clonarItensPedido(itensAdicionais).forEach(adicionarOuSomarItem);

  return Array.from(mapa.values());
};

export const converterPedidoParaFormData = (pedido) => ({
  fornecedor_id: pedido?.fornecedor_id?.toString() || "",
  data_prevista_entrega: pedido?.data_prevista_entrega
    ? new Date(pedido.data_prevista_entrega).toISOString().split("T")[0]
    : "",
  valor_frete: textoNumeroSeguro(pedido?.valor_frete, "0"),
  valor_desconto: textoNumeroSeguro(pedido?.valor_desconto, "0"),
  observacoes: pedido?.observacoes || "",
  itens: clonarItensPedido(
    (pedido?.itens || []).map((item) => ({
      produto_id: item.produto_id,
      produto_nome: item.produto_nome || `Produto ${item.produto_id}`,
      produto_codigo: item.produto_codigo || item.codigo || item.sku || "",
      quantidade_pedida: item.quantidade_pedida,
      unidade_compra: item.unidade_compra || UNIDADE_COMPRA_PADRAO,
      quantidade_por_embalagem:
        item.quantidade_por_embalagem ?? (item.unidade_compra === UNIDADE_COMPRA_PADRAO ? 1 : null),
      quantidade_total_unidades: item.quantidade_total_unidades,
      preco_unitario: item.preco_unitario,
      desconto_item: item.desconto_item || 0,
      total: item.total ?? item.valor_total,
    })),
  ),
});

export const extrairNomeArquivoCabecalho = (contentDisposition, fallback) => {
  if (!contentDisposition) {
    return fallback;
  }

  const matchUtf8 = contentDisposition.match(/filename\*\s*=\s*UTF-8''([^;]+)/i);
  if (matchUtf8?.[1]) {
    try {
      return decodeURIComponent(matchUtf8[1].trim());
    } catch (_error) {
      // ignora e tenta os outros formatos
    }
  }

  const matchQuoted = contentDisposition.match(/filename\s*=\s*"([^"]+)"/i);
  if (matchQuoted?.[1]) {
    return matchQuoted[1].trim();
  }

  const matchSimple = contentDisposition.match(/filename\s*=\s*([^;]+)/i);
  if (matchSimple?.[1]) {
    return matchSimple[1].trim().replace(/^"|"$/g, "");
  }

  return fallback;
};

export const baixarArquivoResposta = (response, fallback) => {
  const contentDisposition =
    response?.headers?.["content-disposition"] || response?.headers?.["Content-Disposition"];
  const nomeArquivo = extrairNomeArquivoCabecalho(contentDisposition, fallback);
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", nomeArquivo);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};
