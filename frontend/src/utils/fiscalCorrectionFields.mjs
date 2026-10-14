export function agruparPendenciasFiscais(validacao, camposPermitidos) {
  const itens = [
    ...(validacao?.bloqueios || []),
    ...(validacao?.correcoes || []),
    ...(validacao?.diagnostico_rejeicao?.correcoes || []),
  ];
  const produtos = new Map();
  const gerais = [];

  itens.forEach((item) => {
    if (!item?.produto_id || !camposPermitidos[item.campo]) {
      gerais.push(item);
      return;
    }
    // O mesmo produto pode aparecer em lotes diferentes na mesma venda.
    const chave = `${item.produto_id}:${item.item_numero ?? item.item_id ?? ""}`;
    const atual = produtos.get(chave) || {
      chave,
      id: item.produto_id,
      itemId: item.item_id,
      nome: item.produto_nome || `Produto ${item.produto_id}`,
      sku: item.sku,
      codigo_barras: item.codigo_barras,
      tipo: item.produto_tipo,
      itemNumero: item.item_numero,
      loteId: item.lote_id,
      pendencias: [],
    };
    atual.itemId ??= item.item_id;
    atual.itemNumero ??= item.item_numero;
    atual.loteId ??= item.lote_id;
    const indice = atual.pendencias.findIndex((pendencia) => pendencia.campo === item.campo);
    if (indice < 0) {
      atual.pendencias.push(item);
    } else {
      const anterior = atual.pendencias[indice];
      atual.pendencias[indice] = {
        ...anterior,
        ...item,
        valor_sugerido: item.valor_sugerido ?? anterior.valor_sugerido,
        fonte_sugestao: item.fonte_sugestao ?? anterior.fonte_sugestao,
        confianca: item.confianca ?? anterior.confianca,
        preenchimento_automatico:
          item.preenchimento_automatico ?? anterior.preenchimento_automatico,
        valor_invalido: item.valor_invalido ?? anterior.valor_invalido,
      };
    }
    produtos.set(chave, atual);
  });

  return { produtos: [...produtos.values()], gerais };
}

export function camposFiscaisAlterados(_produto, fiscal = {}, original = {}) {
  const aliases = { pis_cst: "cst_pis", cofins_cst: "cst_cofins" };
  const camposPermitidos = [
    "ncm",
    "cest",
    "origem_mercadoria",
    "cfop",
    "cst_icms",
    "pis_cst",
    "cofins_cst",
  ];
  return Object.fromEntries(
    camposPermitidos
      .filter(
        (campo) =>
          Object.hasOwn(fiscal, campo) &&
          String(fiscal[campo] ?? "") !== String(original[campo] ?? ""),
      )
      .map((campo) => [aliases[campo] || campo, fiscal[campo]]),
  );
}
