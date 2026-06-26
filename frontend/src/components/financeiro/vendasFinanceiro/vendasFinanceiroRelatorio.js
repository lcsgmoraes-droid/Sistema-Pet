import { dataKeyLocal, parseDataLocal } from "./vendasFinanceiroDatas.js";

export function normalizarFormaPagamentoLabel(valor) {
  const texto = String(valor || "").trim();
  const lower = texto.toLowerCase();
  const mapa = {
    1: "Dinheiro",
    2: "Pix",
    3: "Cartao Debito",
    4: "Cartao Credito",
    5: "Cartao Credito",
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
    dadosFiltrados = dadosFiltrados.filter((item) => item.funcionario === filtroFuncionario);
  }

  if (filtroFormaPagamento && tipo === "formaPagamento") {
    dadosFiltrados = dadosFiltrados.filter((item) => item.forma_pagamento === filtroFormaPagamento);
  }

  if (filtroCategoria && tipo === "categoria") {
    dadosFiltrados = dadosFiltrados.filter((item) => item.categoria === filtroCategoria);
  }

  return dadosFiltrados;
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

export function calcularPeriodoComparacaoFinanceiro({ dataInicio, dataFim, periodoComparacao }) {
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
