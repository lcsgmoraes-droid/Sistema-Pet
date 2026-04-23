function normalizarNumero(valor) {
  const numero = Number(valor ?? 0);
  return Number.isFinite(numero) ? numero : 0;
}

export function montarItensVendaPayload(vendaAtual) {
  return (vendaAtual.itens || []).map((item) => ({
    tipo: item.tipo,
    produto_id: item.produto_id,
    servico_descricao: item.servico_descricao,
    quantidade: normalizarNumero(item.quantidade),
    preco_unitario: normalizarNumero(item.preco_unitario ?? item.preco_venda),
    desconto_item: normalizarNumero(
      item.desconto_valor ?? item.desconto_item ?? 0,
    ),
    subtotal: normalizarNumero(item.subtotal),
    lote_id: item.lote_id ?? null,
    pet_id: item.pet_id || vendaAtual.pet?.id || null,
  }));
}

export function montarPayloadVenda(vendaAtual, entregadorSelecionado = null) {
  const temEntrega = Boolean(vendaAtual.tem_entrega);
  const taxaEntregaTotal = temEntrega
    ? normalizarNumero(vendaAtual.entrega?.taxa_entrega_total)
    : 0;
  const taxaLoja = temEntrega
    ? normalizarNumero(vendaAtual.entrega?.taxa_loja)
    : 0;
  const taxaEntregador = temEntrega
    ? normalizarNumero(vendaAtual.entrega?.taxa_entregador)
    : 0;
  const entregadorId = temEntrega
    ? vendaAtual.entregador_id || entregadorSelecionado?.id || null
    : null;

  const percentualTaxaLoja =
    taxaEntregaTotal > 0 ? (taxaLoja / taxaEntregaTotal) * 100 : 0;
  const percentualTaxaEntregador =
    taxaEntregaTotal > 0 ? (taxaEntregador / taxaEntregaTotal) * 100 : 0;

  return {
    cliente_id: vendaAtual.cliente?.id || null,
    funcionario_id: vendaAtual.funcionario_id || null,
    itens: montarItensVendaPayload(vendaAtual),
    desconto_valor: normalizarNumero(vendaAtual.desconto_valor),
    desconto_percentual: normalizarNumero(vendaAtual.desconto_percentual),
    observacoes: vendaAtual.observacoes || "",
    tem_entrega: temEntrega,
    taxa_entrega: taxaEntregaTotal,
    percentual_taxa_loja: Number(percentualTaxaLoja.toFixed(2)),
    percentual_taxa_entregador: Number(percentualTaxaEntregador.toFixed(2)),
    endereco_entrega: temEntrega
      ? vendaAtual.entrega?.endereco_completo || ""
      : null,
    observacoes_entrega: temEntrega
      ? vendaAtual.entrega?.observacoes_entrega || ""
      : null,
    distancia_km: temEntrega
      ? normalizarNumero(vendaAtual.entrega?.distancia_km)
      : null,
    valor_por_km: temEntrega
      ? normalizarNumero(vendaAtual.entrega?.valor_por_km)
      : null,
    loja_origem: temEntrega ? vendaAtual.entrega?.loja_origem || null : null,
    entregador_id: entregadorId,
  };
}
