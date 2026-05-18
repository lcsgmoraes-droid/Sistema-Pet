import writeExcelFile from "write-excel-file/browser";
import { formatMoneyCellValue, isZeroMoneyValue } from "../ui/MoneyCell";

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

export function filtrarVendasParaRelatorio({
  escopo,
  vendas,
  filtroFuncionario,
  filtroFormaPagamento,
  filtroCategoria,
  filtroStatusLista,
}) {
  const lista = Array.isArray(vendas) ? vendas : [];
  if (escopo === "geral") return [...lista];

  return lista.filter((venda) => {
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
  const copia = [...(Array.isArray(lista) ? lista : [])];
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

export function formatarMoeda(valor) {
  return formatMoneyCellValue(valor);
}

export function formatarMoedaOuTraco(valor) {
  return formatMoneyCellValue(valor, { zeroAsDash: true });
}

export function formatarMoedaComSinalOuTraco(valor, sinal) {
  return formatMoneyCellValue(valor, { sign: sinal, zeroAsDash: true });
}

export function formatarPercentualOuTraco(valor) {
  return isZeroMoneyValue(valor) ? "-" : `${valor}%`;
}

export function formatarDataLocal(valor, opcoes = {}) {
  const data = parseDataLocal(valor);
  if (!data) return "N/A";
  return data.toLocaleDateString("pt-BR", opcoes);
}

export function formatarData(dataStr) {
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

function adicionarDias(data, dias) {
  const proxima = new Date(data);
  proxima.setDate(proxima.getDate() + dias);
  return proxima;
}

function formatarDataIsoLocal(data) {
  const ano = data.getFullYear();
  const mes = String(data.getMonth() + 1).padStart(2, "0");
  const dia = String(data.getDate()).padStart(2, "0");
  return `${ano}-${mes}-${dia}`;
}

export function calcularPeriodoFiltroRapido(filtro, agora = new Date()) {
  const ano = agora.getFullYear();
  const mes = String(agora.getMonth() + 1).padStart(2, "0");
  const hoje = formatarDataIsoLocal(agora);

  let inicio;
  let fim;

  switch (filtro) {
    case "hoje":
      inicio = fim = hoje;
      break;
    case "ontem": {
      const dataOntem = new Date(agora);
      dataOntem.setDate(agora.getDate() - 1);
      inicio = fim = formatarDataIsoLocal(dataOntem);
      break;
    }
    case "esta_semana": {
      const diaSemana = agora.getDay();
      const diasDesdeSegunda = diaSemana === 0 ? 6 : diaSemana - 1;
      const primeiroDia = new Date(agora);
      primeiroDia.setDate(agora.getDate() - diasDesdeSegunda);
      inicio = formatarDataIsoLocal(primeiroDia);
      fim = hoje;
      break;
    }
    case "este_mes":
      inicio = `${ano}-${mes}-01`;
      fim = hoje;
      break;
    case "mes_anterior": {
      const mesPassado = new Date(agora.getFullYear(), agora.getMonth() - 1, 1);
      const ultimoDia = new Date(agora.getFullYear(), agora.getMonth(), 0);
      inicio = `${mesPassado.getFullYear()}-${String(mesPassado.getMonth() + 1).padStart(2, "0")}-01`;
      fim = formatarDataIsoLocal(ultimoDia);
      break;
    }
    case "ultimos_7_dias": {
      const sete = new Date(agora);
      sete.setDate(agora.getDate() - 7);
      inicio = formatarDataIsoLocal(sete);
      fim = hoje;
      break;
    }
    case "ultimos_30_dias": {
      const trinta = new Date(agora);
      trinta.setDate(agora.getDate() - 30);
      inicio = formatarDataIsoLocal(trinta);
      fim = hoje;
      break;
    }
    case "este_ano":
      inicio = `${ano}-01-01`;
      fim = hoje;
      break;
    default:
      return null;
  }

  return { inicio, fim };
}

export function calcularPeriodoComparacao({ dataInicio, dataFim, periodoComparacao }) {
  const [anoIni, mesIni, diaIni] = dataInicio.split("-").map(Number);
  const [anoFim, mesFim, diaFim] = dataFim.split("-").map(Number);

  const inicio = new Date(anoIni, mesIni - 1, diaIni);
  const fim = new Date(anoFim, mesFim - 1, diaFim);
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
    data_inicio: formatarDataIsoLocal(inicioComp),
    data_fim: formatarDataIsoLocal(fimComp),
  };
}

export function calcularVariacao(valorAtual, valorAnterior) {
  if (!valorAnterior || valorAnterior === 0) {
    return { valor: 0, percentual: 0 };
  }
  const diff = valorAtual - valorAnterior;
  const perc = ((diff / valorAnterior) * 100).toFixed(1);
  return { valor: diff, percentual: Number.parseFloat(perc) };
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

export function arredondarMoeda(valor) {
  return Math.round((Number(valor) || 0) * 100) / 100;
}

export function arredondarPercentual(valor) {
  return Math.round((Number(valor) || 0) * 10) / 10;
}

export function vendaTemNotaFiscal(venda) {
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
