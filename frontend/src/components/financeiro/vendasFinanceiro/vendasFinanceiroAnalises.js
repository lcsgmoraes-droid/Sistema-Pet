import { parseDataHoraLocal } from "./vendasFinanceiroDatas.js";
import { sanitizarNumero } from "./vendasFinanceiroRelatorio.js";
function arredondarMoeda(valor) {
  return Math.round((Number(valor) || 0) * 100) / 100;
}
function arredondarPercentual(valor) {
  return Math.round((Number(valor) || 0) * 10) / 10;
}
export function calcularAnaliseInteligenteVendas({
  produtosAnalise = [],
  resumo = {},
  resumoComparacao = {},
  vendasPorData = [],
} = {}) {
  if (!produtosAnalise || produtosAnalise.length === 0) {
    return {
      produtosMaisLucrativos: [],
      produtosPorCategoria: {},
      alertasInteligentesVendas: [],
      previsaoProximos7Dias: 0,
    };
  }

  const produtosComMargem = produtosAnalise.map((produto) => {
    const custo = sanitizarNumero(produto.custo_total);
    const preco = sanitizarNumero(produto.valor_total);
    const quantidade = sanitizarNumero(produto.quantidade) || 1;
    const lucro = preco - custo;
    const margem = custo > 0 ? (lucro / custo) * 100 : 0;

    return {
      nome: produto.nome || produto.produto || "Produto sem nome",
      marca: produto.marca || "-",
      quantidade,
      custo: sanitizarNumero(custo / quantidade),
      preco: sanitizarNumero(preco / quantidade),
      lucro_total: sanitizarNumero(lucro),
      margem: sanitizarNumero(margem),
      categoria: produto.categoria || "Sem Categoria",
    };
  });

  const produtosMaisLucrativos = [...produtosComMargem]
    .sort((a, b) => b.lucro_total - a.lucro_total)
    .slice(0, 20);
  const produtosPorCategoria = {};
  produtosComMargem.forEach((produto) => {
    const categoria = produto.categoria || "Sem Categoria";
    if (!produtosPorCategoria[categoria]) {
      produtosPorCategoria[categoria] = {
        quantidade: 0,
        total: 0,
        margens: [],
      };
    }
    produtosPorCategoria[categoria].quantidade += produto.quantidade;
    produtosPorCategoria[categoria].total += produto.preco * produto.quantidade;
    produtosPorCategoria[categoria].margens.push(produto.margem);
  });

  Object.keys(produtosPorCategoria).forEach((categoria) => {
    const margens = produtosPorCategoria[categoria].margens;
    const somaMargens = margens.reduce(
      (total, margem) => sanitizarNumero(total) + sanitizarNumero(margem),
      0,
    );
    produtosPorCategoria[categoria].margem_media = sanitizarNumero(
      margens.length > 0 ? somaMargens / margens.length : 0,
    );
    delete produtosPorCategoria[categoria].margens;
  });
  const alertasInteligentesVendas = [];

  const qtdAtual = sanitizarNumero(resumo.quantidade_vendas);
  const qtdAnterior = sanitizarNumero(resumoComparacao.quantidade_vendas);
  if (qtdAnterior > 0 && qtdAtual < qtdAnterior) {
    const queda = Number((((qtdAnterior - qtdAtual) / qtdAnterior) * 100).toFixed(1));
    alertasInteligentesVendas.push({
      id: "queda-vendas",
      tipo: "critico",
      titulo: "Queda de volume de vendas",
      mensagem: `As vendas cairam ${queda}% em relacao ao periodo comparativo.`,
      recomendacao:
        "Revise campanhas, produtos de entrada e politica de descontos para recuperar volume.",
    });
  }

  const liquidoAtual = sanitizarNumero(resumo.venda_liquida);
  const emAberto = sanitizarNumero(resumo.em_aberto);
  if (liquidoAtual > 0) {
    const percAberto = Number(((emAberto / liquidoAtual) * 100).toFixed(1));
    if (percAberto >= 20) {
      alertasInteligentesVendas.push({
        id: "recebiveis-abertos",
        tipo: "atencao",
        titulo: "Recebimento em aberto elevado",
        mensagem: `${percAberto}% da venda liquida ainda esta em aberto no periodo.`,
        recomendacao: "Priorize cobranca e revise condicoes de pagamento com maior prazo.",
      });
    }
  }

  const baixaMargem = produtosComMargem.filter((produto) => produto.margem < 20).length;
  if (baixaMargem >= 5) {
    alertasInteligentesVendas.push({
      id: "mix-baixa-margem",
      tipo: "atencao",
      titulo: "Muitos produtos com baixa margem",
      mensagem: `${baixaMargem} produtos vendidos estao com margem abaixo de 20%.`,
      recomendacao: "Reprecifique itens de baixo giro/margem e renegocie compra com fornecedor.",
    });
  }

  const altaMargemBaixoVolume = produtosComMargem
    .filter((produto) => produto.margem >= 45 && produto.quantidade <= 3)
    .slice(0, 3);
  if (altaMargemBaixoVolume.length > 0) {
    alertasInteligentesVendas.push({
      id: "oportunidade-upsell",
      tipo: "oportunidade",
      titulo: "Oportunidade de crescimento",
      mensagem: `Produtos com alta margem e baixo volume: ${altaMargemBaixoVolume
        .map((produto) => produto.nome)
        .join(", ")}.`,
      recomendacao:
        "Destacar esses itens no atendimento e criar combo promocional para aumentar giro.",
    });
  }

  const basePrevisao = (vendasPorData || []).slice(-14);
  const previsaoProximos7Dias =
    basePrevisao.length > 0
      ? sanitizarNumero(
          (basePrevisao.reduce((soma, item) => soma + sanitizarNumero(item.valor_liquido), 0) /
            basePrevisao.length) *
            7,
        )
      : 0;

  return {
    produtosMaisLucrativos,
    produtosPorCategoria,
    alertasInteligentesVendas,
    previsaoProximos7Dias,
  };
}

export function calcularDistribuicaoTemporalVendasFinanceiro(vendas = []) {
  const dias = [
    { chave: 1, nome: "Segunda", curto: "Seg" },
    { chave: 2, nome: "Terca", curto: "Ter" },
    { chave: 3, nome: "Quarta", curto: "Qua" },
    { chave: 4, nome: "Quinta", curto: "Qui" },
    { chave: 5, nome: "Sexta", curto: "Sex" },
    { chave: 6, nome: "Sabado", curto: "Sab" },
    { chave: 0, nome: "Domingo", curto: "Dom" },
  ];
  const mapaDias = new Map(
    dias.map((dia, ordem) => [
      dia.chave,
      {
        ...dia,
        ordem,
        quantidade: 0,
        valor_bruto: 0,
        valor_liquido: 0,
        ticket_medio: 0,
      },
    ]),
  );
  const horas = Array.from({ length: 24 }, (_, hora) => ({
    hora,
    faixa: `${String(hora).padStart(2, "0")}h`,
    quantidade: 0,
    valor_bruto: 0,
    valor_liquido: 0,
    ticket_medio: 0,
  }));

  (vendas || []).forEach((venda) => {
    const data = parseDataHoraLocal(venda.data_venda);
    if (!data) return;

    const dia = mapaDias.get(data.getDay());
    if (dia) {
      dia.quantidade += 1;
      dia.valor_bruto += Number(venda.venda_bruta || 0);
      dia.valor_liquido += Number(venda.venda_liquida || 0);
    }

    const hora = horas[data.getHours()];
    if (hora) {
      hora.quantidade += 1;
      hora.valor_bruto += Number(venda.venda_bruta || 0);
      hora.valor_liquido += Number(venda.venda_liquida || 0);
    }
  });

  const vendasPorDiaSemanaResumo = Array.from(mapaDias.values()).map((item) => ({
    ...item,
    ticket_medio: item.quantidade > 0 ? item.valor_liquido / item.quantidade : 0,
  }));
  const vendasPorHorarioResumo = horas.map((item) => ({
    ...item,
    ticket_medio: item.quantidade > 0 ? item.valor_liquido / item.quantidade : 0,
  }));
  const vendasPorHorarioComMovimento = vendasPorHorarioResumo.filter((item) => item.quantidade > 0);

  return {
    vendasPorDiaSemanaResumo,
    vendasPorHorarioResumo,
    vendasPorHorarioComMovimento,
    melhorDiaSemana: [...vendasPorDiaSemanaResumo].sort(
      (a, b) => Number(b.valor_liquido || 0) - Number(a.valor_liquido || 0),
    )[0],
    melhorHorario: [...vendasPorHorarioComMovimento].sort(
      (a, b) => Number(b.valor_liquido || 0) - Number(a.valor_liquido || 0),
    )[0],
  };
}

export function montarFluxoResultadoCardsFinanceiro(resumo = {}) {
  const taxaLoja = Number(resumo.taxa_loja_total || 0);
  const repasseEntrega = Number(resumo.taxa_entrega_repasse_total ?? resumo.taxa_entrega ?? 0);
  const taxaOperacional = Number(resumo.taxa_operacional_total || 0);
  const custoOperacional = repasseEntrega + taxaOperacional;
  const taxasCartao = Number(resumo.taxa_cartao_total || 0);
  const comissao = Number(resumo.comissao_total || 0);
  const imposto = Number(resumo.imposto_total || 0);
  const campanhas = Number(resumo.custo_campanha_total || 0);
  const custoProdutos = Number(resumo.custo_total || 0);
  const lucro = Number(resumo.lucro_total || 0);

  return [
    {
      sinal: "",
      titulo: "Venda Bruta",
      valor: Number(resumo.venda_bruta || 0),
      detalhe: "Produtos e servicos antes das deducoes.",
      cor: "border-emerald-200 bg-emerald-50 text-emerald-800",
    },
    {
      sinal: "+",
      titulo: "Tx Loja",
      valor: taxaLoja,
      detalhe: "Parte da entrega que fica como receita da loja.",
      cor: "border-blue-200 bg-blue-50 text-blue-800",
    },
    {
      sinal: "-",
      titulo: "Descontos",
      valor: Number(resumo.desconto || 0),
      detalhe: "Descontos de venda e itens.",
      cor: "border-amber-200 bg-amber-50 text-amber-800",
    },
    {
      sinal: "-",
      titulo: "Operacional",
      valor: custoOperacional,
      detalhe: "Repasse de entrega e custos operacionais.",
      cor: "border-orange-200 bg-orange-50 text-orange-800",
    },
    {
      sinal: "-",
      titulo: "Cartao",
      valor: taxasCartao,
      detalhe: "Taxas das operadoras de cartao.",
      cor: "border-purple-200 bg-purple-50 text-purple-800",
    },
    {
      sinal: "-",
      titulo: "Comissao",
      valor: comissao,
      detalhe: "Comissoes rateadas nas vendas.",
      cor: "border-indigo-200 bg-indigo-50 text-indigo-800",
    },
    {
      sinal: "-",
      titulo: "Impostos",
      valor: imposto,
      detalhe: "Imposto usado na rentabilidade.",
      cor: "border-rose-200 bg-rose-50 text-rose-800",
    },
    {
      sinal: "-",
      titulo: "Campanhas",
      valor: campanhas,
      detalhe: "Cashback, cupons e beneficios resgatados.",
      cor: "border-cyan-200 bg-cyan-50 text-cyan-800",
    },
    {
      sinal: "=",
      titulo: "Venda Liquida",
      valor: Number(resumo.venda_liquida || 0),
      detalhe: "Resultado antes do custo dos produtos.",
      cor: "border-sky-200 bg-sky-50 text-sky-800",
    },
    {
      sinal: "R$",
      titulo: "Valor Recebido",
      valor: Number(resumo.valor_recebido || 0),
      detalhe: "Total efetivamente baixado/recebido no periodo.",
      cor: "border-emerald-200 bg-emerald-50 text-emerald-800",
    },
    {
      sinal: "!",
      titulo: "Em Aberto",
      valor: Number(resumo.em_aberto || 0),
      detalhe: "Vendas pendentes de baixa no periodo.",
      cor: "border-red-200 bg-red-50 text-red-800",
      acao: "vendas_em_aberto",
    },
    {
      sinal: "-",
      titulo: "Custo Produtos",
      valor: custoProdutos,
      detalhe: "CMV dos produtos vendidos.",
      cor: "border-slate-200 bg-slate-50 text-slate-800",
    },
    {
      sinal: "=",
      titulo: "Lucro",
      valor: lucro,
      detalhe: "Venda liquida menos custo dos produtos.",
      cor:
        lucro >= 0
          ? "border-green-200 bg-green-50 text-green-800"
          : "border-red-200 bg-red-50 text-red-800",
    },
    {
      sinal: "%",
      titulo: "Margem",
      valor: Number(resumo.margem_media || 0),
      detalhe: "Lucro sobre a venda liquida.",
      percentual: true,
      cor: "border-teal-200 bg-teal-50 text-teal-800",
    },
  ];
}

export function calcularAnalisePromocoesFinanceiro(vendas = []) {
  const topProdutos = new Map();
  let vendasPromocao = 0;
  let vendasNormais = 0;
  let valorVendasPromocao = 0;
  let valorVendasNormais = 0;
  let valorItensPromocionais = 0;
  let descontoPromocional = 0;

  (vendas || []).forEach((venda) => {
    const itens = Array.isArray(venda.itens) ? venda.itens : [];
    const itensPromo = itens.filter((item) => item?.em_promocao);
    const vendaTemPromocao = Boolean(venda.tem_promocao || itensPromo.length > 0);
    const valorVenda = Number(venda.venda_liquida || venda.venda_bruta || 0);

    if (vendaTemPromocao) {
      vendasPromocao += 1;
      valorVendasPromocao += valorVenda;
    } else {
      vendasNormais += 1;
      valorVendasNormais += valorVenda;
    }

    itensPromo.forEach((item) => {
      const chave = item.produto_id || item.produto_nome;
      const atual = topProdutos.get(chave) || {
        produto_nome: item.produto_nome || "Produto removido",
        quantidade: 0,
        valor: 0,
        desconto: 0,
        origens: new Set(),
      };
      const valorItem = Number(
        item.valor_liquido || item.valor_promocional || item.venda_bruta || 0,
      );
      const descontoItem = Number(item.desconto_promocional || 0);

      atual.quantidade += Number(item.quantidade || 0);
      atual.valor += valorItem;
      atual.desconto += descontoItem;
      String(item.promocao_origem || "")
        .split(",")
        .map((origem) => origem.trim())
        .filter(Boolean)
        .forEach((origem) => atual.origens.add(origem));

      valorItensPromocionais += valorItem;
      descontoPromocional += descontoItem;
      topProdutos.set(chave, atual);
    });
  });

  const totalVendas = vendasPromocao + vendasNormais;
  return {
    totalVendas,
    vendasPromocao,
    vendasNormais,
    valorVendasPromocao,
    valorVendasNormais,
    valorItensPromocionais,
    descontoPromocional,
    percentualPromocao:
      totalVendas > 0 ? arredondarPercentual((vendasPromocao / totalVendas) * 100) : 0,
    comparativo: [
      { tipo: "Normais", quantidade: vendasNormais, valor: valorVendasNormais },
      { tipo: "Preco promocional", quantidade: vendasPromocao, valor: valorVendasPromocao },
    ],
    topProdutos: Array.from(topProdutos.values())
      .map((item) => ({
        ...item,
        origens: Array.from(item.origens),
        valor: arredondarMoeda(item.valor),
        desconto: arredondarMoeda(item.desconto),
      }))
      .sort((a, b) => b.valor - a.valor)
      .slice(0, 8),
  };
}
