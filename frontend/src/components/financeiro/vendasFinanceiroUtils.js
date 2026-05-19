import writeExcelFile from "write-excel-file/browser";

export const COLUNAS_RELATORIO_VENDAS = [
  { key: "data_venda", label: "Data", value: (v) => v.data_venda || "" },
  { key: "numero_venda", label: "Codigo", value: (v) => v.numero_venda || "" },
  { key: "cliente_nome", label: "Cliente", value: (v) => v.cliente_nome || "" },
  { key: "status", label: "Status", value: (v) => v.status || "" },
  { key: "venda_bruta", label: "Venda Bruta", value: (v) => Number(v.venda_bruta || 0) },
  { key: "taxa_loja", label: "Taxa Loja", value: (v) => Number(v.taxa_loja || 0) },
  { key: "desconto", label: "Desconto", value: (v) => Number(v.desconto || 0) },
  { key: "taxa_entrega", label: "Taxa Entrega", value: (v) => Number(v.taxa_entrega || 0) },
  { key: "taxa_operacional", label: "Taxa Operac.", value: (v) => Number(v.taxa_operacional || 0) },
  { key: "taxa_cartao", label: "Taxa Cartao", value: (v) => Number(v.taxa_cartao || 0) },
  { key: "comissao", label: "Comissao", value: (v) => Number(v.comissao || 0) },
  { key: "imposto", label: "Imposto", value: (v) => Number(v.imposto || 0) },
  { key: "custo_campanha", label: "Custo Campanha", value: (v) => Number(v.custo_campanha || 0) },
  { key: "venda_liquida", label: "Venda Liquida", value: (v) => Number(v.venda_liquida || 0) },
  { key: "valor_recebido", label: "Valor Recebido", value: (v) => Number(v.valor_recebido || 0) },
  { key: "custo_produtos", label: "Custo Produtos", value: (v) => Number(v.custo_produtos || 0) },
  { key: "lucro", label: "Lucro", value: (v) => Number(v.lucro || 0) },
  {
    key: "margem_sobre_venda",
    label: "Margem sobre Venda %",
    value: (v) => Number(v.margem_sobre_venda || 0),
  },
  {
    key: "margem_sobre_custo",
    label: "Margem sobre Custo %",
    value: (v) => Number(v.margem_sobre_custo || 0),
  },
];

function normalizarValorExcel(valor) {
  if (valor === null || valor === undefined) return "";
  return valor;
}

function criarDadosExcel(linhas) {
  return linhas.map((linha, indice) =>
    linha.map((valor) => {
      const celula = { value: normalizarValorExcel(valor) };
      if (indice !== 0) return celula;

      return {
        ...celula,
        fontWeight: "bold",
        backgroundColor: "#DBEAFE",
      };
    }),
  );
}

function criarColunasExcel(linhas) {
  const totalColunas = Math.max(...linhas.map((linha) => linha.length), 0);
  return Array.from({ length: totalColunas }, (_, indice) => {
    const maiorTexto = linhas.reduce((maior, linha) => {
      const tamanho = String(normalizarValorExcel(linha[indice])).length;
      return Math.max(maior, tamanho);
    }, 0);
    return { width: Math.min(Math.max(maiorTexto + 2, 12), 42) };
  });
}

export async function exportarPlanilhasExcel(planilhas, nomeArquivo) {
  await writeExcelFile(
    planilhas.map(({ sheet, linhas }) => ({
      sheet,
      data: criarDadosExcel(linhas),
      columns: criarColunasExcel(linhas),
      stickyRowsCount: 1,
    })),
  ).toFile(nomeArquivo);
}

export function parseDataLocal(valor) {
  if (!valor) return null;

  if (valor instanceof Date) {
    return new Date(valor.getFullYear(), valor.getMonth(), valor.getDate());
  }

  if (typeof valor === "string") {
    const dataBase = valor.includes("T") ? valor.split("T")[0] : valor;
    const match = dataBase.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (match) {
      const [, ano, mes, dia] = match;
      return new Date(Number(ano), Number(mes) - 1, Number(dia));
    }
  }

  const data = new Date(valor);
  if (Number.isNaN(data.getTime())) return null;
  return data;
}

export function parseDataHoraLocal(valor) {
  if (!valor) return null;
  if (valor instanceof Date) {
    return Number.isNaN(valor.getTime()) ? null : valor;
  }

  if (typeof valor === "string") {
    const match = valor.match(
      /^(\d{4})-(\d{2})-(\d{2})[T\s](\d{2}):(\d{2})(?::(\d{2}))?/,
    );
    if (match) {
      const [, ano, mes, dia, hora, minuto, segundo] = match;
      return new Date(
        Number(ano),
        Number(mes) - 1,
        Number(dia),
        Number(hora),
        Number(minuto),
        Number(segundo || 0),
      );
    }
  }

  const data = new Date(valor);
  if (Number.isNaN(data.getTime())) return null;
  return data;
}

export function dataKeyLocal(valor) {
  const data = parseDataLocal(valor);
  if (!data) return "";
  const ano = data.getFullYear();
  const mes = String(data.getMonth() + 1).padStart(2, "0");
  const dia = String(data.getDate()).padStart(2, "0");
  return `${ano}-${mes}-${dia}`;
}

export function calcularFiltroRapidoPeriodoVendas(filtro, dataBase = new Date()) {
  const agora = parseDataLocal(dataBase);
  if (!agora) return null;

  const ano = agora.getFullYear();
  const mes = String(agora.getMonth() + 1).padStart(2, "0");
  const hoje = dataKeyLocal(agora);

  switch (filtro) {
    case "hoje":
      return { inicio: hoje, fim: hoje };
    case "ontem": {
      const ontem = new Date(agora);
      ontem.setDate(agora.getDate() - 1);
      const dataOntem = dataKeyLocal(ontem);
      return { inicio: dataOntem, fim: dataOntem };
    }
    case "esta_semana": {
      const diaSemana = agora.getDay();
      const diasDesdeSegunda = diaSemana === 0 ? 6 : diaSemana - 1;
      const primeiroDia = new Date(agora);
      primeiroDia.setDate(agora.getDate() - diasDesdeSegunda);
      return { inicio: dataKeyLocal(primeiroDia), fim: hoje };
    }
    case "este_mes":
      return { inicio: `${ano}-${mes}-01`, fim: hoje };
    case "mes_anterior": {
      const mesPassado = new Date(ano, agora.getMonth() - 1, 1);
      const ultimoDia = new Date(ano, agora.getMonth(), 0);
      const anoMesPassado = mesPassado.getFullYear();
      const numeroMesPassado = String(mesPassado.getMonth() + 1).padStart(2, "0");
      return {
        inicio: `${anoMesPassado}-${numeroMesPassado}-01`,
        fim: dataKeyLocal(ultimoDia),
      };
    }
    case "ultimos_7_dias": {
      const seteDias = new Date(agora);
      seteDias.setDate(agora.getDate() - 7);
      return { inicio: dataKeyLocal(seteDias), fim: hoje };
    }
    case "ultimos_30_dias": {
      const trintaDias = new Date(agora);
      trintaDias.setDate(agora.getDate() - 30);
      return { inicio: dataKeyLocal(trintaDias), fim: hoje };
    }
    case "este_ano":
      return { inicio: `${ano}-01-01`, fim: hoje };
    default:
      return null;
  }
}

export function normalizarFormaPagamentoLabel(valor) {
  const texto = String(valor || "").trim();
  const lower = texto.toLowerCase();
  const mapa = {
    "1": "Dinheiro",
    "2": "Pix",
    "3": "Cartao Debito",
    "4": "Cartao Credito",
    "5": "Cartao Credito",
    pix: "Pix",
    dinheiro: "Dinheiro",
    debito: "Cartao Debito",
    cartao_debito: "Cartao Debito",
    "cartao debito": "Cartao Debito",
    credito: "Cartao Credito",
    cartao_credito: "Cartao Credito",
    "cartao credito": "Cartao Credito",
    credito_parcelado: "Cartao Credito",
    credito_cliente: "Credito do Cliente",
    "credito cliente": "Credito do Cliente",
  };

  return mapa[lower] || texto || "Nao informado";
}

export function consolidarFormasRecebimentoFinanceiro(formasRecebimento = []) {
  const mapa = new Map();
  (formasRecebimento || []).forEach((item) => {
    const forma = normalizarFormaPagamentoLabel(item.forma_pagamento);
    const atual = mapa.get(forma) || {
      ...item,
      forma_pagamento: forma,
      valor_total: 0,
    };
    atual.valor_total += Number(item.valor_total || 0);
    mapa.set(forma, atual);
  });

  return Array.from(mapa.values()).sort(
    (a, b) => Number(b.valor_total || 0) - Number(a.valor_total || 0),
  );
}

export function filtrarDadosFinanceiroVendas(dados, tipo, filtros = {}) {
  if (!dados || dados.length === 0) return dados;

  let dadosFiltrados = [...dados];
  const { filtroFuncionario, filtroFormaPagamento, filtroCategoria } = filtros;

  if (filtroFuncionario && tipo === "funcionario") {
    dadosFiltrados = dadosFiltrados.filter(
      (item) => item.funcionario === filtroFuncionario,
    );
  }

  if (filtroFormaPagamento && tipo === "formaPagamento") {
    dadosFiltrados = dadosFiltrados.filter(
      (item) => item.forma_pagamento === filtroFormaPagamento,
    );
  }

  if (filtroCategoria && tipo === "categoria") {
    dadosFiltrados = dadosFiltrados.filter((item) => item.categoria === filtroCategoria);
  }

  return dadosFiltrados;
}

export function formatarDataLocal(valor, opcoes = {}) {
  const data = parseDataLocal(valor);
  if (!data) return "N/A";
  return data.toLocaleDateString("pt-BR", opcoes);
}

function adicionarDias(data, dias) {
  const proxima = new Date(data);
  proxima.setDate(proxima.getDate() + dias);
  return proxima;
}

export function listarDiasPeriodo(dataInicio, dataFim) {
  const inicio = parseDataLocal(dataInicio);
  const fim = parseDataLocal(dataFim);
  if (!inicio || !fim || inicio > fim) return [];

  const dias = [];
  for (let atual = new Date(inicio); atual <= fim; atual = adicionarDias(atual, 1)) {
    dias.push(new Date(atual));
  }
  return dias;
}

function calcularPascoa(ano) {
  const a = ano % 19;
  const b = Math.floor(ano / 100);
  const c = ano % 100;
  const d = Math.floor(b / 4);
  const e = b % 4;
  const f = Math.floor((b + 8) / 25);
  const g = Math.floor((b - f + 1) / 3);
  const h = (19 * a + b - d - g + 15) % 30;
  const i = Math.floor(c / 4);
  const k = c % 4;
  const l = (32 + 2 * e + 2 * i - h - k) % 7;
  const m = Math.floor((a + 11 * h + 22 * l) / 451);
  const mes = Math.floor((h + l - 7 * m + 114) / 31);
  const dia = ((h + l - 7 * m + 114) % 31) + 1;
  return new Date(ano, mes - 1, dia);
}

function feriadoMovel(ano, deslocamentoDias) {
  return dataKeyLocal(adicionarDias(calcularPascoa(ano), deslocamentoDias));
}

export function montarFeriadosPadrao(anos) {
  const feriados = {};
  anos.forEach((ano) => {
    Object.assign(feriados, {
      [`${ano}-01-01`]: "Confraternização Universal",
      [`${ano}-04-21`]: "Tiradentes",
      [`${ano}-05-01`]: "Dia do Trabalho",
      [`${ano}-09-07`]: "Independência do Brasil",
      [`${ano}-10-12`]: "Nossa Senhora Aparecida",
      [`${ano}-11-02`]: "Finados",
      [`${ano}-11-15`]: "Proclamação da República",
      [`${ano}-11-20`]: "Consciência Negra",
      [`${ano}-12-25`]: "Natal",
      [feriadoMovel(ano, -48)]: "Carnaval",
      [feriadoMovel(ano, -47)]: "Carnaval",
      [feriadoMovel(ano, -2)]: "Sexta-feira Santa",
      [feriadoMovel(ano, 60)]: "Corpus Christi",
    });
  });
  return feriados;
}

export function montarFeriadosPeriodoFinanceiro({
  dataInicio,
  dataFim,
  feriadosCustomizados = [],
}) {
  const anos = new Set(
    listarDiasPeriodo(dataInicio, dataFim).map((dia) => dia.getFullYear()),
  );
  const feriados = montarFeriadosPadrao(Array.from(anos));

  feriadosCustomizados.forEach((feriado) => {
    if (feriado?.data) {
      feriados[feriado.data] = feriado.nome?.trim() || "Feriado cadastrado";
    }
  });

  return feriados;
}

export function montarVendasPorDataCalendarioFinanceiro({
  dataInicio,
  dataFim,
  vendasPorData = [],
  feriadosPorData = {},
  considerarSabadoDiaUtil = false,
}) {
  const vendasMap = new Map(
    (vendasPorData || []).map((item) => [dataKeyLocal(item.data), item]),
  );

  return listarDiasPeriodo(dataInicio, dataFim).map((dia) => {
    const key = dataKeyLocal(dia);
    const item = vendasMap.get(key) || {};
    const diaSemana = dia.getDay();
    const feriadoNome = feriadosPorData[key] || "";

    const quantidade = Number(item.quantidade || 0);
    const valorBruto = Number(item.valor_bruto || 0);
    const valorLiquido = Number(item.valor_liquido || 0);
    const temMovimento = quantidade > 0 || valorBruto > 0 || valorLiquido > 0;
    const sabado = diaSemana === 6;
    const domingo = diaSemana === 0;
    const sabadoUtil = sabado && considerarSabadoDiaUtil;
    const feriadoAberto = Boolean(feriadoNome && temMovimento);
    const fimDeSemana = domingo || (sabado && !sabadoUtil);
    const diaUtilBase = !domingo && (!sabado || sabadoUtil);
    const diaUtil = feriadoAberto || (diaUtilBase && !feriadoNome);

    return {
      data: key,
      quantidade,
      valor_bruto: valorBruto,
      taxa_entrega: Number(item.taxa_entrega || 0),
      desconto: Number(item.desconto || 0),
      percentual_desconto: Number(item.percentual_desconto || 0),
      valor_liquido: valorLiquido,
      valor_recebido: Number(item.valor_recebido || 0),
      saldo_aberto: Number(item.saldo_aberto || 0),
      ticket_medio: quantidade > 0 ? Number(item.ticket_medio || valorBruto / quantidade) : 0,
      dia_semana: formatarDataLocal(key, { weekday: "long" }),
      sabado,
      fim_de_semana: fimDeSemana,
      feriado_nome: feriadoNome,
      feriado_aberto: feriadoAberto,
      dia_util: diaUtil,
      sem_movimento: quantidade === 0 && valorLiquido === 0,
    };
  });
}

export function calcularResumoDiasPeriodoFinanceiro(vendasPorDataCalendario = []) {
  const diasUteis = vendasPorDataCalendario.filter((item) => item.dia_util);
  const diasTrabalhados = diasUteis.filter((item) => !item.sem_movimento);
  const diasUteisSemVenda = diasUteis.filter((item) => item.sem_movimento);
  const totalLiquidoDiasUteis = diasUteis.reduce(
    (sum, item) => sum + Number(item.valor_liquido || 0),
    0,
  );
  const totalLiquidoDiasTrabalhados = diasTrabalhados.reduce(
    (sum, item) => sum + Number(item.valor_liquido || 0),
    0,
  );

  return {
    totalDias: vendasPorDataCalendario.length,
    diasUteis: diasUteis.length,
    diasTrabalhados: diasTrabalhados.length,
    diasUteisSemVenda: diasUteisSemVenda.length,
    finsDeSemana: vendasPorDataCalendario.filter((item) => item.fim_de_semana).length,
    feriados: vendasPorDataCalendario.filter((item) => item.feriado_nome).length,
    mediaDiaUtil: diasUteis.length > 0 ? totalLiquidoDiasUteis / diasUteis.length : 0,
    mediaDiaTrabalhado:
      diasTrabalhados.length > 0 ? totalLiquidoDiasTrabalhados / diasTrabalhados.length : 0,
  };
}

export function getFeriadosStorageKey() {
  try {
    const tenant = JSON.parse(window.localStorage.getItem("selectedTenant") || "{}");
    return `financeiro:vendas:feriados-customizados:${tenant?.id || "global"}`;
  } catch {
    return "financeiro:vendas:feriados-customizados:global";
  }
}

export function carregarFeriadosCustomizados() {
  try {
    const salvo = window.localStorage.getItem(getFeriadosStorageKey());
    const parsed = salvo ? JSON.parse(salvo) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function getDiasUteisStorageKey() {
  try {
    const tenant = JSON.parse(window.localStorage.getItem("selectedTenant") || "{}");
    return `financeiro:vendas:dias-uteis:${tenant?.id || "global"}`;
  } catch {
    return "financeiro:vendas:dias-uteis:global";
  }
}

export function carregarConfigDiasUteis() {
  try {
    const salvo = window.localStorage.getItem(getDiasUteisStorageKey());
    const parsed = salvo ? JSON.parse(salvo) : {};
    return {
      considerarSabadoDiaUtil: Boolean(parsed?.considerarSabadoDiaUtil),
    };
  } catch {
    return { considerarSabadoDiaUtil: false };
  }
}

export function vendaEstaEmAberto(venda) {
  const status = String(venda?.status || "").toLowerCase();
  return !["finalizada", "pago_nf", "baixada", "paga", "cancelada"].includes(status);
}

export function calcularValorRecebidoVenda(venda) {
  const valorInformado = Number(venda?.valor_recebido || 0);
  if (valorInformado > 0) return valorInformado;

  const status = String(venda?.status || "").toLowerCase();
  if (["finalizada", "pago_nf", "baixada", "paga"].includes(status)) {
    return Number(venda?.venda_bruta || venda?.venda_liquida || 0);
  }

  return 0;
}

export function sanitizarNumero(valor) {
  if (
    valor === null ||
    valor === undefined ||
    Number.isNaN(Number(valor)) ||
    !Number.isFinite(Number(valor))
  ) {
    return 0;
  }
  return valor;
}

export function formatarDataVendaFinanceiro(dataStr) {
  if (!dataStr) return "N/A";
  const dataLocal = parseDataLocal(dataStr);
  if (dataLocal) return dataLocal.toLocaleDateString("pt-BR");
  try {
    if (dataStr instanceof Date) {
      return dataStr.toLocaleDateString("pt-BR");
    }

    if (typeof dataStr === "string" && dataStr.includes("T")) {
      const dateOnly = dataStr.split("T")[0];
      const [year, month, day] = dateOnly.split("-");
      return `${day}/${month}/${year}`;
    }

    const data = new Date(dataStr);
    if (Number.isNaN(data.getTime())) {
      return "N/A";
    }

    return data.toLocaleDateString("pt-BR");
  } catch {
    return "N/A";
  }
}

export function filtrarVendasRelatorio(
  vendas,
  {
    escopo = "filtrado",
    filtroFuncionario = "",
    filtroFormaPagamento = "",
    filtroCategoria = "",
    filtroStatusLista = "",
  } = {},
) {
  if (escopo === "geral") return [...(vendas || [])];

  return (vendas || []).filter((venda) => {
    const funcionario = String(venda.funcionario_nome || venda.funcionario || "");
    const formaPagamento = String(venda.forma_pagamento || venda.pagamento_principal || "");
    const categoria = String(venda.categoria || "");

    const okFuncionario = !filtroFuncionario || funcionario === filtroFuncionario;
    const okForma = !filtroFormaPagamento || formaPagamento === filtroFormaPagamento;
    const okCategoria = !filtroCategoria || categoria === filtroCategoria;
    const okStatus = filtroStatusLista !== "em_aberto" || vendaEstaEmAberto(venda);

    return okFuncionario && okForma && okCategoria && okStatus;
  });
}

export function ordenarVendasRelatorio(lista, ordenacao) {
  const copia = [...(lista || [])];
  switch (ordenacao) {
    case "data_asc":
      return copia.sort((a, b) => parseDataLocal(a.data_venda) - parseDataLocal(b.data_venda));
    case "bruta_desc":
      return copia.sort((a, b) => Number(b.venda_bruta || 0) - Number(a.venda_bruta || 0));
    case "bruta_asc":
      return copia.sort((a, b) => Number(a.venda_bruta || 0) - Number(b.venda_bruta || 0));
    case "lucro_desc":
      return copia.sort((a, b) => Number(b.lucro || 0) - Number(a.lucro || 0));
    case "lucro_asc":
      return copia.sort((a, b) => Number(a.lucro || 0) - Number(b.lucro || 0));
    case "data_desc":
    default:
      return copia.sort((a, b) => parseDataLocal(b.data_venda) - parseDataLocal(a.data_venda));
  }
}

export function getTextoComparacaoPeriodo(periodoComparacao) {
  switch (periodoComparacao) {
    case "periodo_anterior":
      return "mesmo período anterior";
    case "mes_anterior":
      return "mesmo período do mês anterior";
    case "ano_anterior":
      return "mesmo período do ano anterior";
    default:
      return "período anterior";
  }
}

export function calcularPeriodoComparacaoFinanceiro({
  dataInicio,
  dataFim,
  periodoComparacao,
}) {
  const inicio = parseDataLocal(dataInicio);
  const fim = parseDataLocal(dataFim);
  if (!inicio || !fim) return { data_inicio: "", data_fim: "" };

  const diffDias = Math.floor((fim - inicio) / (1000 * 60 * 60 * 24)) + 1;
  let inicioComp;
  let fimComp;

  switch (periodoComparacao) {
    case "periodo_anterior":
      inicioComp = new Date(inicio);
      inicioComp.setDate(inicio.getDate() - diffDias);
      fimComp = new Date(inicio);
      fimComp.setDate(inicio.getDate() - 1);
      break;
    case "mes_anterior":
      inicioComp = new Date(inicio);
      inicioComp.setMonth(inicio.getMonth() - 1);
      fimComp = new Date(fim);
      fimComp.setMonth(fim.getMonth() - 1);
      break;
    case "ano_anterior":
      inicioComp = new Date(inicio);
      inicioComp.setFullYear(inicio.getFullYear() - 1);
      fimComp = new Date(fim);
      fimComp.setFullYear(fim.getFullYear() - 1);
      break;
    default:
      return { data_inicio: "", data_fim: "" };
  }

  return {
    data_inicio: dataKeyLocal(inicioComp),
    data_fim: dataKeyLocal(fimComp),
  };
}

export function calcularVariacaoFinanceira(valorAtual, valorAnterior) {
  if (!valorAnterior || valorAnterior === 0) {
    return { valor: 0, percentual: 0 };
  }

  const diff = valorAtual - valorAnterior;
  const percentual = Number.parseFloat(((diff / valorAnterior) * 100).toFixed(1));
  return { valor: diff, percentual };
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
        recomendacao:
          "Priorize cobranca e revise condicoes de pagamento com maior prazo.",
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
      recomendacao:
        "Reprecifique itens de baixo giro/margem e renegocie compra com fornecedor.",
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
          (basePrevisao.reduce(
            (soma, item) => soma + sanitizarNumero(item.valor_liquido),
            0,
          ) /
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

export function getStatusVendaMeta(status) {
  const statusNormalizado = String(status || "").toLowerCase();
  if (statusNormalizado === "finalizada") {
    return { label: "Baixada", intent: "success" };
  }
  if (statusNormalizado === "pago_nf") {
    return { label: "Pago NF", intent: "success" };
  }
  if (statusNormalizado === "baixa_parcial") {
    return { label: "Parcial", intent: "info" };
  }
  if (statusNormalizado === "cancelada") {
    return { label: "Cancelada", intent: "danger" };
  }
  return { label: "Aberta", intent: "warning" };
}

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
    },
  );

  return {
    ...totais,
    margem_sobre_venda:
      totais.venda_bruta > 0 ? arredondarPercentual((totais.lucro / totais.venda_bruta) * 100) : 0,
    margem_sobre_custo:
      totais.custo_produtos > 0 ? arredondarPercentual((totais.lucro / totais.custo_produtos) * 100) : 0,
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
  const vendasPorHorarioComMovimento = vendasPorHorarioResumo.filter(
    (item) => item.quantidade > 0,
  );

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
  const repasseEntrega = Number(
    resumo.taxa_entrega_repasse_total ?? resumo.taxa_entrega ?? 0,
  );
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

function ajustarItemImposto(item, aplicarImposto) {
  if (aplicarImposto) return item;

  const impostoOriginal = Number(item?.imposto || 0);
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
