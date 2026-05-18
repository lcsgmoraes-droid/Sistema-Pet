export function montarNomeXml(dados) {
  const numero = String(dados?.numero_nf || '0').replaceAll(/\D/g, '');
  const serie = String(dados?.serie || '1').replaceAll(/\D/g, '');
  const chave = String(dados?.chave_acesso || '').replaceAll(/\D/g, '').slice(-8);
  return `nfe_${numero || '0'}_${serie || '1'}_${chave || 'xml'}.xml`;
}

export function formatarOpcaoProduto(produto) {
  const sku = produto?.codigo || 'Sem SKU';
  const ean = produto?.codigo_barras || produto?.gtin_ean || produto?.gtin_ean_tributario || 'Sem EAN';
  const nome = produto?.nome || 'Produto sem nome';
  const estoque = produto?.estoque_atual || 0;
  return `${sku} | EAN: ${ean} | ${nome} (Est: ${estoque})`;
}

export function formatarValorFiscal(valor, casas = 4) {
  return Number(valor || 0).toLocaleString('pt-BR', {
    minimumFractionDigits: casas,
    maximumFractionDigits: casas,
  });
}

export function obterCustoAquisicaoItem(item) {
  return Number(
    item?.custo_aquisicao_unitario ??
    item?.custo_aquisicao_unitario_nf ??
    item?.composicao_custo?.custo_aquisicao_unitario ??
    item?.custo_unitario_efetivo ??
    item?.custo_unitario_efetivo_nf ??
    item?.valor_unitario ??
    0
  );
}

export function normalizarMultiplicadorPack(valor, fallback = 1) {
  const parsed = Number.parseInt(valor, 10);

  if (!Number.isInteger(parsed)) {
    return fallback;
  }

  return Math.max(1, Math.min(200, parsed));
}

export function obterChavePackItem(item) {
  return item?.id ?? item?.item_id ?? null;
}

export function itemTemOverridePack(item, multiplicadoresOverride = {}) {
  const chaveItem = obterChavePackItem(item);

  if (chaveItem === null || chaveItem === undefined) {
    return false;
  }

  return (
    Object.prototype.hasOwnProperty.call(multiplicadoresOverride, chaveItem) ||
    Object.prototype.hasOwnProperty.call(multiplicadoresOverride, String(chaveItem))
  );
}

export function obterConfiguracaoPackItem(item, multiplicadoresOverride = {}) {
  const chaveItem = obterChavePackItem(item);
  const multiplicadorDetectado = normalizarMultiplicadorPack(item?.pack_multiplicador_detectado, 1);
  const overrideManual = itemTemOverridePack(item, multiplicadoresOverride);
  const overrideRaw = overrideManual
    ? (multiplicadoresOverride[chaveItem] ?? multiplicadoresOverride[String(chaveItem)])
    : null;
  const multiplicador = overrideManual
    ? normalizarMultiplicadorPack(overrideRaw, multiplicadorDetectado)
    : multiplicadorDetectado;
  const sugestaoAutomaticaDiferenteDoPadrao = multiplicadorDetectado > 1;

  return {
    chaveItem,
    multiplicador,
    multiplicadorDetectado,
    overrideManual,
    packDetectadoAutomatico: Boolean(item?.pack_detectado_automatico || sugestaoAutomaticaDiferenteDoPadrao),
    sugestaoAutomaticaDiferenteDoPadrao,
    usandoSugestaoAutomatica: sugestaoAutomaticaDiferenteDoPadrao && !overrideManual,
  };
}

export function ajustarComposicaoCustoParaMultiplicador(composicao, quantidadeBase, multiplicador) {
  if (!composicao) {
    return composicao;
  }

  const quantidadeEfetiva = Number(quantidadeBase || 0) * multiplicador;
  const componentesTotal = composicao.componentes_total || {};
  const valorUnitario = (valorTotal) => (quantidadeEfetiva > 0 ? Number(valorTotal || 0) / quantidadeEfetiva : 0);

  return {
    ...composicao,
    quantidade_efetiva: quantidadeEfetiva,
    custo_bruto_unitario: valorUnitario(componentesTotal.valor_produtos),
    custo_aquisicao_unitario: valorUnitario(composicao.custo_aquisicao_total),
    componentes_unitario: {
      ...(composicao.componentes_unitario || {}),
      valor_frete: valorUnitario(componentesTotal.valor_frete),
      valor_seguro: valorUnitario(componentesTotal.valor_seguro),
      valor_outras_despesas: valorUnitario(componentesTotal.valor_outras_despesas),
      valor_desconto: valorUnitario(componentesTotal.valor_desconto),
      valor_icms_st: valorUnitario(componentesTotal.valor_icms_st),
      valor_ipi: valorUnitario(componentesTotal.valor_ipi),
      valor_icms: valorUnitario(componentesTotal.valor_icms),
      valor_pis: valorUnitario(componentesTotal.valor_pis),
      valor_cofins: valorUnitario(componentesTotal.valor_cofins),
    },
  };
}

export function aplicarMultiplicadorPackAoItem(item, multiplicadoresOverride = {}) {
  if (!item) {
    return item;
  }

  const configPack = obterConfiguracaoPackItem(item, multiplicadoresOverride);
  const quantidadeNF = Number(item.quantidade_nf ?? item.quantidade ?? 0);
  const quantidadeEfetiva = quantidadeNF * configPack.multiplicador;
  const custoTotal = Number(
    item.custo_aquisicao_total_nf ??
    item.custo_aquisicao_total ??
    item.composicao_custo?.custo_aquisicao_total ??
    item.valor_total_nf ??
    item.valor_total ??
    0,
  );
  const custoUnitarioFallback = Number(
    item.custo_aquisicao_unitario_nf ??
    item.custo_aquisicao_unitario ??
    item.composicao_custo?.custo_aquisicao_unitario ??
    item.custo_unitario_efetivo_nf ??
    item.custo_unitario_efetivo ??
    item.valor_unitario_nf ??
    item.valor_unitario ??
    0,
  );
  const custoUnitarioEfetivo = quantidadeEfetiva > 0
    ? (custoTotal / quantidadeEfetiva)
    : custoUnitarioFallback;

  let produtoVinculadoAjustado = item.produto_vinculado;
  if (item.produto_vinculado) {
    const custoAnterior = Number(item.produto_vinculado.custo_anterior || 0);
    const variacaoCusto = custoAnterior > 0
      ? ((custoUnitarioEfetivo - custoAnterior) / custoAnterior) * 100
      : 0;
    const precoVendaAtual = Number(item.produto_vinculado.preco_venda_atual || 0);
    const margemReferencia = precoVendaAtual > 0 && custoAnterior > 0
      ? ((precoVendaAtual - custoAnterior) / precoVendaAtual) * 100
      : 0;
    const margemProjetada = precoVendaAtual > 0
      ? ((precoVendaAtual - custoUnitarioEfetivo) / precoVendaAtual) * 100
      : 0;

    produtoVinculadoAjustado = {
      ...item.produto_vinculado,
      custo_novo: custoUnitarioEfetivo,
      variacao_custo_percentual: Number(variacaoCusto.toFixed(2)),
      margem_atual: Number(margemReferencia.toFixed(2)),
      margem_projetada_custo_novo: Number(margemProjetada.toFixed(2)),
    };
  }

  return {
    ...item,
    pack_multiplicador_usado: configPack.multiplicador,
    pack_override_manual: configPack.overrideManual,
    pack_usa_sugestao_automatica: configPack.usandoSugestaoAutomatica,
    pack_sugestao_destacada: configPack.sugestaoAutomaticaDiferenteDoPadrao,
    quantidade_efetiva_nf: quantidadeEfetiva,
    quantidade_efetiva: quantidadeEfetiva,
    custo_unitario_efetivo_nf: custoUnitarioEfetivo,
    custo_unitario_efetivo: custoUnitarioEfetivo,
    custo_aquisicao_unitario_nf: custoUnitarioEfetivo,
    custo_aquisicao_unitario: custoUnitarioEfetivo,
    composicao_custo: ajustarComposicaoCustoParaMultiplicador(
      item.composicao_custo,
      quantidadeNF,
      configPack.multiplicador,
    ),
    produto_vinculado: produtoVinculadoAjustado,
  };
}

export function aplicarOverridesPackNoPreview(preview, multiplicadoresOverride = {}) {
  if (!preview || !Array.isArray(preview.itens)) {
    return preview;
  }

  return {
    ...preview,
    itens: preview.itens.map((item) => aplicarMultiplicadorPackAoItem(item, multiplicadoresOverride)),
  };
}

export const CONFERENCIA_STATUS_META = {
  nao_iniciada: {
    label: 'Nao conferida',
    cls: 'bg-gray-100 text-gray-700 border-gray-200',
  },
  sem_divergencia: {
    label: 'Conferida sem divergencias',
    cls: 'bg-green-100 text-green-800 border-green-200',
  },
  com_divergencia: {
    label: 'Conferida com divergencias',
    cls: 'bg-orange-100 text-orange-800 border-orange-200',
  },
};

export const BASE_CALCULO_MARGEM_OPCOES = [
  {
    value: 'nf',
    label: 'Custo da NF',
    descricao: 'Padrao. Usa o custo fiscal da NF como base da margem.',
  },
  {
    value: 'sistema',
    label: 'Custo no sistema',
    descricao: 'Usa o custo que sera aplicado no processamento da entrada.',
  },
];

export const ACAO_CONFERENCIA_OPCOES = [
  { value: 'sem_acao', label: 'Sem acao' },
  { value: 'contatar_fornecedor', label: 'Contatar fornecedor' },
  { value: 'reposicao_fornecedor', label: 'Pedir reposicao' },
  { value: 'nf_devolucao', label: 'NF de devolucao' },
  { value: 'ajuste_interno', label: 'Ajuste interno' },
];

export function normalizarNumeroConferencia(valor, fallback = 0) {
  const numero = Number.parseFloat(String(valor ?? '').replace(',', '.'));
  if (!Number.isFinite(numero)) return fallback;
  return Math.max(0, numero);
}

export function obterDraftConferenciaItem(item) {
  const quantidadeNF = Number(item?.quantidade ?? item?.quantidade_nf ?? 0);
  const quantidadeConferida = Math.max(
    0,
    Math.min(
      Number(item?.quantidade_conferida ?? quantidadeNF),
      quantidadeNF,
    ),
  );
  const quantidadeAvariada = Math.max(
    0,
    Math.min(
      Number(item?.quantidade_avariada ?? 0),
      Math.max(0, quantidadeNF - quantidadeConferida),
    ),
  );

  return {
    quantidade_conferida: quantidadeConferida,
    quantidade_avariada: quantidadeAvariada,
    observacao_conferencia: item?.observacao_conferencia || '',
    acao_sugerida: item?.acao_sugerida || 'sem_acao',
  };
}

export function calcularConferenciaItem(item, draft) {
  const quantidadeNF = Number(item?.quantidade ?? item?.quantidade_nf ?? 0);
  const base = draft || obterDraftConferenciaItem(item);
  const quantidadeConferida = Math.max(
    0,
    Math.min(Number(base?.quantidade_conferida ?? quantidadeNF), quantidadeNF),
  );
  const quantidadeAvariada = Math.max(
    0,
    Math.min(Number(base?.quantidade_avariada ?? 0), Math.max(0, quantidadeNF - quantidadeConferida)),
  );
  const quantidadeFaltante = Math.max(0, quantidadeNF - quantidadeConferida - quantidadeAvariada);
  const temAvaria = quantidadeAvariada > 0;
  const temFalta = quantidadeFaltante > 0;

  let statusConferencia = 'ok';
  if (temAvaria && temFalta) statusConferencia = 'falta_avaria';
  else if (temAvaria) statusConferencia = 'avaria';
  else if (temFalta) statusConferencia = 'falta';

  const temDivergencia = statusConferencia !== 'ok';
  const acaoSugerida = temDivergencia
    ? (base?.acao_sugerida || (temAvaria ? 'nf_devolucao' : 'contatar_fornecedor'))
    : 'sem_acao';

  return {
    quantidadeNF,
    quantidadeConferida,
    quantidadeAvariada,
    quantidadeFaltante,
    statusConferencia,
    temDivergencia,
    acaoSugerida,
    observacaoConferencia: base?.observacao_conferencia || '',
  };
}

export function montarConferenciaState(nota) {
  const state = {};
  (nota?.itens || []).forEach((item) => {
    state[item.id] = obterDraftConferenciaItem(item);
  });
  return state;
}

export function calcularResumoConferencia(nota, conferenciaItens) {
  const itens = nota?.itens || [];
  const resumo = {
    itens_total: itens.length,
    itens_ok: 0,
    itens_com_divergencia: 0,
    itens_com_avaria: 0,
    quantidade_total_nf: 0,
    quantidade_total_conferida: 0,
    quantidade_total_avariada: 0,
    quantidade_total_faltante: 0,
  };

  itens.forEach((item) => {
    const conferenciaItem = calcularConferenciaItem(item, conferenciaItens?.[item.id]);
    resumo.quantidade_total_nf += conferenciaItem.quantidadeNF;
    resumo.quantidade_total_conferida += conferenciaItem.quantidadeConferida;
    resumo.quantidade_total_avariada += conferenciaItem.quantidadeAvariada;
    resumo.quantidade_total_faltante += conferenciaItem.quantidadeFaltante;

    if (conferenciaItem.temDivergencia) {
      resumo.itens_com_divergencia += 1;
    } else {
      resumo.itens_ok += 1;
    }

    if (conferenciaItem.quantidadeAvariada > 0) {
      resumo.itens_com_avaria += 1;
    }
  });

  const statusBase = nota?.conferencia?.status || nota?.conferencia_status || 'nao_iniciada';
  const status = statusBase === 'nao_iniciada'
    ? 'nao_iniciada'
    : (resumo.itens_com_divergencia > 0 ? 'com_divergencia' : 'sem_divergencia');

  return {
    ...resumo,
    status,
    tem_nf_devolucao_sugerida: resumo.itens_com_avaria > 0,
  };
}

export function formatarDataRelatorio(valor) {
  if (!valor) return 'Nao informado';
  const dt = new Date(valor);
  if (Number.isNaN(dt.getTime())) return 'Nao informado';
  return dt.toLocaleDateString('pt-BR');
}

export function formatarMoedaRelatorio(valor) {
  const numero = Number(valor || 0);
  if (Number.isNaN(numero)) return '0,00';
  return numero.toFixed(2).replace('.', ',');
}

export function normalizarProdutoPreview(item) {
  return item.produto_vinculado || {
    produto_id: item.produto_id,
    produto_nome: item.produto_nome,
    produto_codigo: item.produto_codigo,
    produto_ean: item.produto_ean,
    custo_anterior: item.custo_anterior,
    custo_novo: item.custo_novo,
    variacao_custo_percentual: item.variacao_custo_percentual,
    preco_venda_atual: item.preco_venda_atual,
    margem_atual: item.margem_atual,
    margem_projetada_custo_novo: item.margem_projetada_custo_novo,
    estoque_atual: item.estoque_atual,
  };
}

export function obterCustoBasePreviewItem(item) {
  return Number(
    item?.produto_vinculado?.custo_novo ??
    item?.custo_novo ??
    item?.custo_aquisicao_unitario_nf ??
    item?.custo_unitario_efetivo_nf ??
    item?.valor_unitario_nf ??
    0
  );
}

export function obterHistoricoNfAnterior(historicos, numeroNotaAtual) {
  if (!Array.isArray(historicos) || historicos.length === 0) return null;
  const numeroAtual = String(numeroNotaAtual || '').trim();

  const candidatoNfeAnterior = historicos.find((hist) => {
    if (!hist) return false;
    const ehNfe = hist.motivo === 'nfe_entrada';
    const temNumero = !!hist.nota_numero;
    const temCusto = hist.preco_custo_novo !== null && hist.preco_custo_novo !== undefined;
    const notaDiferente = String(hist.nota_numero || '').trim() !== numeroAtual;
    return ehNfe && temNumero && temCusto && notaDiferente;
  });

  if (candidatoNfeAnterior) return candidatoNfeAnterior;

  return historicos.find((hist) =>
    hist &&
    hist.preco_custo_novo !== null &&
    hist.preco_custo_novo !== undefined
  ) || null;
}

export function detectarDivergencias(item) {
  const produtoNome = item.produto_vinculado?.produto_nome || item.produto_nome;
  if (!produtoNome) return [];

  const divergencias = [];
  const descNF = item.descricao_nf || item.descricao || '';
  const descProd = produtoNome || '';

  if (!descNF || !descProd) return [];

  const normalizarTexto = (txt) =>
    (txt || '')
      .toString()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase();

  const normalizarPesoToken = (pesoToken) => {
    const match = String(pesoToken || '').match(/(\d+(?:[.,]\d+)?)\s*(kg|g|gr|mg|ml|l|un|und|unid)/i);
    if (!match) return null;
    const valor = Number.parseFloat(match[1].replace(',', '.'));
    if (Number.isNaN(valor)) return null;
    const unidade = match[2].toLowerCase();

    if (['kg', 'g', 'gr', 'mg'].includes(unidade)) {
      const emGramas = unidade === 'kg'
        ? valor * 1000
        : unidade === 'mg'
          ? valor / 1000
          : valor;
      return { grupo: 'massa', valorBase: emGramas, texto: `${valor}${unidade}` };
    }

    if (['l', 'ml'].includes(unidade)) {
      const emMl = unidade === 'l' ? valor * 1000 : valor;
      return { grupo: 'volume', valorBase: emMl, texto: `${valor}${unidade}` };
    }

    return { grupo: 'unidade', valorBase: valor, texto: `${valor}${unidade}` };
  };

  const detectarEspecie = (txt) => {
    const t = normalizarTexto(txt);
    if (/(\bgato\b|\bcat\b|\bfelino\b)/.test(t)) return 'gato';
    if (/(\bcachorro\b|\bcao\b|\bdog\b|\bcanino\b)/.test(t)) return 'cachorro';
    return null;
  };

  const descNFLower = normalizarTexto(descNF);
  const descProdLower = normalizarTexto(descProd);

  const regexPeso = /(\d+(?:[.,]\d+)?)\s*(kg|g|ml|l|un|und|unid)/gi;
  const pesosNF = [...descNFLower.matchAll(regexPeso)];
  const pesosProd = [...descProdLower.matchAll(regexPeso)];

  if (pesosNF.length > 0 && pesosProd.length > 0) {
    const pesoNF = normalizarPesoToken(pesosNF[0][0]);
    const pesoProd = normalizarPesoToken(pesosProd[0][0]);

    if (pesoNF && pesoProd) {
      const mesmaCategoria = pesoNF.grupo === pesoProd.grupo;
      const tolerancia = pesoNF.grupo === 'unidade' ? 0.01 : 0.5;
      const diferente = !mesmaCategoria || Math.abs(pesoNF.valorBase - pesoProd.valorBase) > tolerancia;

      if (diferente) {
        divergencias.push(`Peso/Tamanho diferente: NF="${pesoNF.texto}" vs Produto="${pesoProd.texto}"`);
      }
    }
  }

  const cores = ['preto', 'branco', 'vermelho', 'azul', 'verde', 'amarelo', 'rosa', 'roxo', 'laranja', 'marrom', 'cinza'];
  const corNF = cores.find((cor) => descNFLower.includes(cor));
  const corProd = cores.find((cor) => descProdLower.includes(cor));

  if (corNF && corProd && corNF !== corProd) {
    divergencias.push(`Cor diferente: NF="${corNF}" vs Produto="${corProd}"`);
  }

  const sabores = ['frango', 'carne', 'peixe', 'cordeiro', 'salmao', 'salmão', 'atum', 'vegetais'];
  const saborNF = sabores.find((sabor) => descNFLower.includes(sabor));
  const saborProd = sabores.find((sabor) => descProdLower.includes(sabor));

  if (saborNF && saborProd && saborNF !== saborProd) {
    divergencias.push(`Sabor diferente: NF="${saborNF}" vs Produto="${saborProd}"`);
  }

  const especieNF = detectarEspecie(descNF);
  const especieProduto = detectarEspecie(descProd);

  if (especieNF && especieProduto && especieNF !== especieProduto) {
    if (especieNF === 'cachorro') {
      divergencias.push('⚠️ Animal diferente: NF para CACHORRO mas produto é para GATO');
    } else {
      divergencias.push('⚠️ Animal diferente: NF para GATO mas produto é para CACHORRO');
    }
  }

  return divergencias;
}
