import { calcularValorRecebidoVenda } from "./vendasFinanceiroRelatorio.js";
import { PENDENCIA_IFOOD_LABEL, temRentabilidadePendente } from "./rentabilidadePendente.js";

export const RESUMO_VENDAS_VAZIO = {
  venda_bruta: 0,
  taxa_entrega: 0,
  desconto: 0,
  venda_liquida: 0,
  valor_recebido: 0,
  em_aberto: 0,
  quantidade_vendas: 0,
};

function arredondarMoeda(valor) {
  return Math.round((Number(valor) || 0) * 100) / 100;
}

function arredondarPercentual(valor) {
  return Math.round((Number(valor) || 0) * 10) / 10;
}

function vendaTemNotaFiscal(venda) {
  const nfeStatus = String(venda?.nfe_status || "").toLowerCase();
  if (["cancelada", "cancelado", "denegada", "rejeitada"].includes(nfeStatus)) {
    return false;
  }

  return Boolean(
    venda?.nf_emitida ||
    venda?.nfe_bling_id ||
    venda?.nfe_chave ||
    venda?.nfe_numero ||
    String(venda?.status || "").toLowerCase() === "pago_nf",
  );
}

export function calcularTotalizadoresListaVendasFinanceiro(vendas = []) {
  const totais = (vendas || []).reduce(
    (acc, venda) => {
      acc.quantidade += 1;
      acc.venda_bruta += Number(venda.venda_bruta || 0);
      acc.taxa_loja += Number(venda.taxa_loja || 0);
      acc.desconto += Number(venda.desconto || 0);
      acc.taxa_entrega += Number(venda.taxa_entrega || 0);
      acc.taxa_operacional += Number(venda.taxa_operacional || 0);
      acc.taxa_cartao += Number(venda.taxa_cartao || 0);
      acc.comissao += Number(venda.comissao || 0);
      acc.imposto += Number(venda.imposto || 0);
      acc.custo_campanha += Number(venda.custo_campanha || 0);
      acc.venda_liquida += Number(venda.venda_liquida || 0);
      acc.valor_recebido += calcularValorRecebidoVenda(venda);
      acc.custo_produtos += Number(venda.custo_produtos || 0);
      acc.lucro += Number(venda.lucro || 0);
      if (temRentabilidadePendente(venda)) acc.vendas_rentabilidade_pendente += 1;
      if (vendaTemNotaFiscal(venda)) acc.com_nf += 1;
      return acc;
    },
    {
      quantidade: 0,
      venda_bruta: 0,
      taxa_loja: 0,
      desconto: 0,
      taxa_entrega: 0,
      taxa_operacional: 0,
      taxa_cartao: 0,
      comissao: 0,
      imposto: 0,
      custo_campanha: 0,
      venda_liquida: 0,
      valor_recebido: 0,
      custo_produtos: 0,
      lucro: 0,
      com_nf: 0,
      vendas_rentabilidade_pendente: 0,
    },
  );

  const pendente = totais.vendas_rentabilidade_pendente > 0;
  return {
    ...totais,
    ...(pendente && {
      rentabilidade_status: "pending_ifood_financial",
      taxas_ifood_pendentes: true,
      taxa_cartao: null,
      venda_liquida: null,
      lucro: null,
    }),
    margem_sobre_venda: pendente
      ? null
      : totais.venda_bruta > 0
        ? arredondarPercentual((totais.lucro / totais.venda_bruta) * 100)
        : 0,
    margem_sobre_custo: pendente
      ? null
      : totais.custo_produtos > 0
        ? arredondarPercentual((totais.lucro / totais.custo_produtos) * 100)
        : 0,
  };
}

export function montarCardsTotalizadoresListaVendasFinanceiro(
  totalizadores = {},
  {
    formatarMoedaOuTraco = (valor) => String(Number(valor || 0)),
    formatarMoedaComSinalOuTraco = (valor, sinal) => `${sinal}${Number(valor || 0)}`,
    formatarPercentualOuTraco = (valor) => String(Number(valor || 0)),
  } = {},
) {
  const pendente = temRentabilidadePendente(totalizadores);
  const formatarDeducao = (valor) =>
    valor === null && pendente ? PENDENCIA_IFOOD_LABEL : formatarMoedaComSinalOuTraco(valor, "-");
  const formatarResultado = (valor, formatar) =>
    valor === null && pendente ? PENDENCIA_IFOOD_LABEL : formatar(valor);

  return [
    {
      label: "Vendas",
      value: Number(totalizadores.quantidade || 0).toLocaleString("pt-BR"),
      intent: "slate",
    },
    {
      label: "Com NF",
      value: Number(totalizadores.com_nf || 0).toLocaleString("pt-BR"),
      intent: "blue",
    },
    {
      label: "Venda Bruta",
      value: formatarMoedaOuTraco(totalizadores.venda_bruta),
      intent: "emerald",
    },
    {
      label: "Tx Loja",
      value: formatarMoedaComSinalOuTraco(totalizadores.taxa_loja, "+"),
      intent: "emerald",
    },
    { label: "Desconto", value: formatarDeducao(totalizadores.desconto), intent: "amber" },
    {
      label: "Tx. Entrega",
      value: formatarDeducao(totalizadores.taxa_entrega),
      intent: "blue",
    },
    {
      label: "Tx. Operac.",
      value: formatarDeducao(totalizadores.taxa_operacional),
      intent: "amber",
    },
    {
      label: "Tx. Pagto",
      value: formatarDeducao(totalizadores.taxa_cartao),
      intent: "violet",
    },
    { label: "Comissao", value: formatarDeducao(totalizadores.comissao), intent: "blue" },
    { label: "Imposto", value: formatarDeducao(totalizadores.imposto), intent: "red" },
    {
      label: "Custo Camp.",
      value: formatarDeducao(totalizadores.custo_campanha),
      intent: "cyan",
    },
    {
      label: "Liquida",
      value: formatarResultado(totalizadores.venda_liquida, formatarMoedaOuTraco),
      intent: "blue",
    },
    {
      label: "Valor Recebido",
      value: formatarMoedaOuTraco(totalizadores.valor_recebido),
      intent: "emerald",
    },
    { label: "Custo", value: formatarDeducao(totalizadores.custo_produtos), intent: "amber" },
    {
      label: "Lucro",
      value: formatarResultado(totalizadores.lucro, formatarMoedaOuTraco),
      intent: pendente ? "amber" : Number(totalizadores.lucro || 0) >= 0 ? "emerald" : "red",
    },
    {
      label: "MG Venda",
      value: formatarResultado(totalizadores.margem_sobre_venda, formatarPercentualOuTraco),
      intent: "slate",
    },
    {
      label: "MG Custo",
      value: formatarResultado(totalizadores.margem_sobre_custo, formatarPercentualOuTraco),
      intent: "slate",
    },
  ];
}

function ajustarItemImposto(item, aplicarImposto) {
  if (aplicarImposto) return item;

  const impostoOriginal = Number(item?.imposto || 0);
  if (temRentabilidadePendente(item)) {
    return { ...item, imposto_original: impostoOriginal, imposto: 0 };
  }
  const vendaBruta = Number(item?.venda_bruta || 0);
  const custoTotal = Number(item?.custo_total || 0);
  const valorLiquido = arredondarMoeda(Number(item?.valor_liquido || 0) + impostoOriginal);
  const lucro = arredondarMoeda(Number(item?.lucro || 0) + impostoOriginal);

  return {
    ...item,
    imposto_original: impostoOriginal,
    imposto: 0,
    valor_liquido: valorLiquido,
    lucro,
    margem_sobre_venda: vendaBruta > 0 ? arredondarPercentual((lucro / vendaBruta) * 100) : 0,
    margem_sobre_custo: custoTotal > 0 ? arredondarPercentual((lucro / custoTotal) * 100) : 0,
  };
}

export function ajustarVendaImposto(venda, mostrarImpostoTodasVendas) {
  const aplicarImposto = mostrarImpostoTodasVendas || vendaTemNotaFiscal(venda);
  if (aplicarImposto) {
    return {
      ...venda,
      imposto_aplicado: true,
      imposto_original: Number(venda?.imposto || 0),
    };
  }

  const impostoOriginal = Number(venda?.imposto || 0);
  if (temRentabilidadePendente(venda)) {
    return {
      ...venda,
      imposto_aplicado: false,
      imposto_original: impostoOriginal,
      imposto: 0,
      itens: Array.isArray(venda?.itens)
        ? venda.itens.map((item) => ajustarItemImposto(item, false))
        : [],
    };
  }
  const vendaBruta = Number(venda?.venda_bruta || 0);
  const custoProdutos = Number(venda?.custo_produtos || 0);
  const vendaLiquida = arredondarMoeda(Number(venda?.venda_liquida || 0) + impostoOriginal);
  const lucro = arredondarMoeda(Number(venda?.lucro || 0) + impostoOriginal);

  return {
    ...venda,
    imposto_aplicado: false,
    imposto_original: impostoOriginal,
    imposto: 0,
    venda_liquida: vendaLiquida,
    lucro,
    margem_sobre_venda: vendaBruta > 0 ? arredondarPercentual((lucro / vendaBruta) * 100) : 0,
    margem_sobre_custo: custoProdutos > 0 ? arredondarPercentual((lucro / custoProdutos) * 100) : 0,
    itens: Array.isArray(venda?.itens)
      ? venda.itens.map((item) => ajustarItemImposto(item, false))
      : [],
  };
}
