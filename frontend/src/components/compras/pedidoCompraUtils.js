export const numeroSeguro = (valor) => {
  const numero = Number(valor);
  return Number.isFinite(numero) ? numero : 0;
};

export const textoNumeroSeguro = (valor, fallback = '0') => {
  if (valor === null || valor === undefined || valor === '') {
    return fallback;
  }

  return String(valor);
};

export const normalizarTextoBusca = (texto = '') =>
  String(texto || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/\s+/g, ' ')
    .trim();

export const textoContemTokens = (texto, busca) => {
  const tokens = normalizarTextoBusca(busca).split(' ').filter(Boolean);
  if (tokens.length === 0) {
    return true;
  }

  const base = normalizarTextoBusca(texto);
  return tokens.every((token) => base.includes(token));
};

export const normalizarItemPedido = (item = {}) => {
  const quantidade = numeroSeguro(item.quantidade_pedida);
  const preco = numeroSeguro(item.preco_unitario);
  const desconto = numeroSeguro(item.desconto_item);
  const totalInformado = Number(item.total ?? item.valor_total);
  const total = Number.isFinite(totalInformado)
    ? totalInformado
    : (preco - desconto) * quantidade;

  return {
    produto_id: Number(item.produto_id),
    produto_nome: item.produto_nome || item.nome || `Produto ${item.produto_id}`,
    produto_codigo: item.produto_codigo || item.codigo || item.sku || '',
    quantidade_pedida: quantidade,
    preco_unitario: preco,
    desconto_item: desconto,
    total
  };
};

export const clonarItensPedido = (itens = []) => itens.map((item) => normalizarItemPedido(item));

export const consolidarItensPedido = (itensBase = [], itensAdicionais = [], estrategia = 'somar') => {
  const mapa = new Map();

  const adicionarOuSomarItem = (item) => {
    const normalizado = normalizarItemPedido(item);
    const chave = Number(normalizado.produto_id);

    if (!Number.isFinite(chave) || chave <= 0) {
      return;
    }

    const existente = mapa.get(chave);
    if (!existente) {
      mapa.set(chave, normalizado);
      return;
    }

    if (estrategia === 'manter_existente') {
      const preco = numeroSeguro(existente.preco_unitario);
      const desconto = numeroSeguro(existente.desconto_item);
      const quantidade = numeroSeguro(existente.quantidade_pedida);

      mapa.set(chave, {
        ...normalizado,
        ...existente,
        preco_unitario: preco,
        desconto_item: desconto,
        quantidade_pedida: quantidade,
        total: (preco - desconto) * quantidade
      });
      return;
    }

    if (estrategia === 'maior_quantidade') {
      const quantidadeExistente = numeroSeguro(existente.quantidade_pedida);
      const quantidadeNova = numeroSeguro(normalizado.quantidade_pedida);
      const itemEscolhido = quantidadeNova >= quantidadeExistente
        ? normalizado
        : existente;
      const preco = numeroSeguro(itemEscolhido.preco_unitario);
      const desconto = numeroSeguro(itemEscolhido.desconto_item);
      const quantidade = Math.max(quantidadeExistente, quantidadeNova);

      mapa.set(chave, {
        ...existente,
        ...normalizado,
        ...itemEscolhido,
        quantidade_pedida: quantidade,
        preco_unitario: preco,
        desconto_item: desconto,
        total: (preco - desconto) * quantidade
      });
      return;
    }

    const preco = numeroSeguro(normalizado.preco_unitario) || numeroSeguro(existente.preco_unitario);
    const desconto = numeroSeguro(normalizado.desconto_item) || numeroSeguro(existente.desconto_item);
    const quantidade = numeroSeguro(existente.quantidade_pedida) + numeroSeguro(normalizado.quantidade_pedida);

    mapa.set(chave, {
      ...existente,
      ...normalizado,
      preco_unitario: preco,
      desconto_item: desconto,
      quantidade_pedida: quantidade,
      total: (preco - desconto) * quantidade
    });
  };

  clonarItensPedido(itensBase).forEach(adicionarOuSomarItem);
  clonarItensPedido(itensAdicionais).forEach(adicionarOuSomarItem);

  return Array.from(mapa.values());
};

export const converterPedidoParaFormData = (pedido) => ({
  fornecedor_id: pedido?.fornecedor_id?.toString() || '',
  data_prevista_entrega: pedido?.data_prevista_entrega
    ? new Date(pedido.data_prevista_entrega).toISOString().split('T')[0]
    : '',
  valor_frete: textoNumeroSeguro(pedido?.valor_frete, '0'),
  valor_desconto: textoNumeroSeguro(pedido?.valor_desconto, '0'),
  observacoes: pedido?.observacoes || '',
  itens: clonarItensPedido(
    (pedido?.itens || []).map((item) => ({
      produto_id: item.produto_id,
      produto_nome: item.produto_nome || `Produto ${item.produto_id}`,
      produto_codigo: item.produto_codigo || item.codigo || item.sku || '',
      quantidade_pedida: item.quantidade_pedida,
      preco_unitario: item.preco_unitario,
      desconto_item: item.desconto_item || 0,
      total: item.total ?? item.valor_total
    }))
  )
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
    return matchSimple[1].trim().replace(/^"|"$/g, '');
  }

  return fallback;
};

export const baixarArquivoResposta = (response, fallback) => {
  const contentDisposition = response?.headers?.['content-disposition'] || response?.headers?.['Content-Disposition'];
  const nomeArquivo = extrairNomeArquivoCabecalho(contentDisposition, fallback);
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', nomeArquivo);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};
