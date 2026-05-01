import {
  ArrowDown,
  ArrowUp,
  BarChart3,
  Calendar,
  ChevronDown,
  ChevronRight,
  Copy,
  Download,
  ExternalLink,
  FileText,
  Filter,
} from "lucide-react";
import React, { useEffect, useMemo, useRef, useState } from "react";
import toast from "react-hot-toast";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import writeExcelFile from "write-excel-file/browser";
import api from "../api";
import { useAuth } from "../contexts/AuthContext";
import HistoricoVendasClienteTab from "../pages/Financeiro/HistoricoVendasClienteTab";

const COLUNAS_RELATORIO_VENDAS = [
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

async function exportarPlanilhasExcel(planilhas, nomeArquivo) {
  await writeExcelFile(
    planilhas.map(({ sheet, linhas }) => ({
      sheet,
      data: criarDadosExcel(linhas),
      columns: criarColunasExcel(linhas),
      stickyRowsCount: 1,
    })),
  ).toFile(nomeArquivo);
}

function parseDataLocal(valor) {
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

function parseDataHoraLocal(valor) {
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

function dataKeyLocal(valor) {
  const data = parseDataLocal(valor);
  if (!data) return "";
  const ano = data.getFullYear();
  const mes = String(data.getMonth() + 1).padStart(2, "0");
  const dia = String(data.getDate()).padStart(2, "0");
  return `${ano}-${mes}-${dia}`;
}

function normalizarFormaPagamentoLabel(valor) {
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

function formatarDataLocal(valor, opcoes = {}) {
  const data = parseDataLocal(valor);
  if (!data) return "N/A";
  return data.toLocaleDateString("pt-BR", opcoes);
}

function adicionarDias(data, dias) {
  const proxima = new Date(data);
  proxima.setDate(proxima.getDate() + dias);
  return proxima;
}

function listarDiasPeriodo(dataInicio, dataFim) {
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

function montarFeriadosPadrao(anos) {
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

function getFeriadosStorageKey() {
  try {
    const tenant = JSON.parse(window.localStorage.getItem("selectedTenant") || "{}");
    return `financeiro:vendas:feriados-customizados:${tenant?.id || "global"}`;
  } catch {
    return "financeiro:vendas:feriados-customizados:global";
  }
}

function carregarFeriadosCustomizados() {
  try {
    const salvo = window.localStorage.getItem(getFeriadosStorageKey());
    const parsed = salvo ? JSON.parse(salvo) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function getDiasUteisStorageKey() {
  try {
    const tenant = JSON.parse(window.localStorage.getItem("selectedTenant") || "{}");
    return `financeiro:vendas:dias-uteis:${tenant?.id || "global"}`;
  } catch {
    return "financeiro:vendas:dias-uteis:global";
  }
}

function carregarConfigDiasUteis() {
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

function vendaEstaEmAberto(venda) {
  const status = String(venda?.status || "").toLowerCase();
  return !["finalizada", "pago_nf", "cancelada"].includes(status);
}

function getStatusVendaMeta(status) {
  const statusNormalizado = String(status || "").toLowerCase();
  if (statusNormalizado === "finalizada") {
    return { label: "Baixada", className: "bg-green-100 text-green-800" };
  }
  if (statusNormalizado === "pago_nf") {
    return { label: "Pago NF", className: "bg-emerald-100 text-emerald-800" };
  }
  if (statusNormalizado === "baixa_parcial") {
    return { label: "Parcial", className: "bg-blue-100 text-blue-800" };
  }
  if (statusNormalizado === "cancelada") {
    return { label: "Cancelada", className: "bg-slate-200 text-slate-700" };
  }
  return { label: "Aberta", className: "bg-yellow-100 text-yellow-800" };
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

function ajustarVendaImposto(venda, mostrarImpostoTodasVendas) {
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

export default function VendasFinanceiro() {
  const { user } = useAuth();
  const userPermissions = user?.permissions || [];
  const podeVerFinanceiroCompleto =
    user?.is_admin === true || userPermissions.includes("relatorios.financeiro");
  const [loading, setLoading] = useState(false);
  const [abaAtiva, setAbaAtiva] = useState("resumo");
  const [dataInicio, setDataInicio] = useState("");
  const [dataFim, setDataFim] = useState("");
  const [filtroSelecionado, setFiltroSelecionado] = useState("");
  const [modoComparacao, setModoComparacao] = useState(false);
  const [periodoComparacao, setPeriodoComparacao] = useState("mes_anterior");

  // Filtros avançados
  const [filtroFuncionario, setFiltroFuncionario] = useState("");
  const [filtroFormaPagamento, setFiltroFormaPagamento] = useState("");
  const [filtroCategoria, setFiltroCategoria] = useState("");
  const [mostrarGraficos, setMostrarGraficos] = useState(true);
  const [tipoComparacao, setTipoComparacao] = useState("financeiro"); // financeiro, formas_pagamento, produtos, funcionarios

  // Estados dos dados
  const [resumo, setResumo] = useState({
    venda_bruta: 0,
    taxa_entrega: 0,
    desconto: 0,
    venda_liquida: 0,
    em_aberto: 0,
    quantidade_vendas: 0,
  });

  const [resumoComparacao, setResumoComparacao] = useState({
    venda_bruta: 0,
    taxa_entrega: 0,
    desconto: 0,
    venda_liquida: 0,
    em_aberto: 0,
    quantidade_vendas: 0,
  });

  const [vendasPorData, setVendasPorData] = useState([]);
  const [formasRecebimento, setFormasRecebimento] = useState([]);
  const [vendasPorFuncionario, setVendasPorFuncionario] = useState([]);
  const [vendasPorTipo, setVendasPorTipo] = useState([]);
  const [vendasPorGrupo, setVendasPorGrupo] = useState([]);
  const [produtosDetalhados, setProdutosDetalhados] = useState([]);
  const [listaVendas, setListaVendas] = useState([]);
  const [vendasExpandidas, setVendasExpandidas] = useState(new Set());

  // Dados de comparação estendidos
  const [formasRecebimentoComparacao, setFormasRecebimentoComparacao] =
    useState([]);
  const [vendasPorGrupoComparacao, setVendasPorGrupoComparacao] = useState([]);
  const [vendasPorFuncionarioComparacao, setVendasPorFuncionarioComparacao] =
    useState([]);

  // Estados para Análise Inteligente
  const [produtosMaisLucrativos, setProdutosMaisLucrativos] = useState([]);
  const [produtosPorCategoria, setProdutosPorCategoria] = useState({});
  const [produtosAnalise, setProdutosAnalise] = useState([]);
  const [alertasInteligentesVendas, setAlertasInteligentesVendas] = useState(
    [],
  );
  const [previsaoProximos7Dias, setPrevisaoProximos7Dias] = useState(0);
  const menuRelatoriosRef = useRef(null);
  const [menuRelatoriosAberto, setMenuRelatoriosAberto] = useState(false);
  const [modalRelatorioAberto, setModalRelatorioAberto] = useState(false);
  const [filtroStatusLista, setFiltroStatusLista] = useState("");
  const [mostrarImpostoTodasVendas, setMostrarImpostoTodasVendas] = useState(true);
  const [mostrarConfigFeriados, setMostrarConfigFeriados] = useState(false);
  const [feriadosCustomizados, setFeriadosCustomizados] = useState(
    carregarFeriadosCustomizados,
  );
  const [configDiasUteis, setConfigDiasUteis] = useState(carregarConfigDiasUteis);
  const [novoFeriadoData, setNovoFeriadoData] = useState("");
  const [novoFeriadoNome, setNovoFeriadoNome] = useState("");
  const [ordenacaoRelatorio, setOrdenacaoRelatorio] = useState("data_desc");
  const [colunasRelatorio, setColunasRelatorio] = useState([
    "data_venda",
    "numero_venda",
    "cliente_nome",
    "venda_bruta",
    "venda_liquida",
    "lucro",
    "status",
  ]);

  const toggleVendaExpandida = (vendaId) => {
    const novoSet = new Set(vendasExpandidas);
    if (novoSet.has(vendaId)) {
      novoSet.delete(vendaId);
    } else {
      novoSet.add(vendaId);
    }
    setVendasExpandidas(novoSet);
  };

  const criarUrlPdvVenda = (venda) => `/pdv?venda_id=${encodeURIComponent(venda.id)}`;

  const copiarNumeroVenda = async (event, numeroVenda) => {
    event.stopPropagation();

    if (!numeroVenda) {
      toast.error("Numero da venda nao disponivel.");
      return;
    }

    try {
      await navigator.clipboard.writeText(String(numeroVenda));
      toast.success(`Venda ${numeroVenda} copiada.`);
    } catch (_error) {
      toast.error("Nao foi possivel copiar o numero da venda.");
    }
  };

  const formatarMoeda = (valor) => {
    return new Intl.NumberFormat("pt-BR", {
      style: "currency",
      currency: "BRL",
    }).format(valor || 0);
  };

  // Helper para garantir números válidos
  const sanitizarNumero = (valor) => {
    if (
      valor === null ||
      valor === undefined ||
      Number.isNaN(Number(valor)) ||
      !Number.isFinite(Number(valor))
    ) {
      return 0;
    }
    return valor;
  };

  const formatarData = (dataStr) => {
    if (!dataStr) return "N/A";
    const dataLocal = parseDataLocal(dataStr);
    if (dataLocal) return dataLocal.toLocaleDateString("pt-BR");
    try {
      // Se já é um objeto Date
      if (dataStr instanceof Date) {
        return dataStr.toLocaleDateString("pt-BR");
      }

      // Se é string ISO (ex: 2026-02-13T23:14:22-03:00)
      // Extrair apenas a parte da data sem fazer conversões de timezone
      if (typeof dataStr === "string" && dataStr.includes("T")) {
        const dateOnly = dataStr.split("T")[0]; // "2026-02-13"
        const [year, month, day] = dateOnly.split("-");
        return `${day}/${month}/${year}`;
      }

      // Tentar parse de ISO string ou formato YYYY-MM-DD
      const data = new Date(dataStr);

      // Verificar se é uma data válida
      if (Number.isNaN(data.getTime())) {
        return "N/A";
      }

      return data.toLocaleDateString("pt-BR");
    } catch {
      return "N/A";
    }
  };

  const listaVendasComImpostoAjustado = useMemo(
    () => listaVendas.map((venda) => ajustarVendaImposto(venda, mostrarImpostoTodasVendas)),
    [listaVendas, mostrarImpostoTodasVendas],
  );

  const filtrarVendasParaRelatorio = (escopo) => {
    if (escopo === "geral") return [...listaVendasComImpostoAjustado];

    return listaVendasComImpostoAjustado.filter((venda) => {
      const funcionario = String(venda.funcionario_nome || venda.funcionario || "");
      const formaPagamento = String(venda.forma_pagamento || venda.pagamento_principal || "");
      const categoria = String(venda.categoria || "");

      const okFuncionario = !filtroFuncionario || funcionario === filtroFuncionario;
      const okForma = !filtroFormaPagamento || formaPagamento === filtroFormaPagamento;
      const okCategoria = !filtroCategoria || categoria === filtroCategoria;
      const okStatus = filtroStatusLista !== "em_aberto" || vendaEstaEmAberto(venda);

      return okFuncionario && okForma && okCategoria && okStatus;
    });
  };

  const ordenarVendasRelatorio = (lista, ordenacao) => {
    const copia = [...lista];
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
  };

  const exportarRelatorioListaVendas = async ({ escopo }) => {
    const dadosFiltrados = filtrarVendasParaRelatorio(escopo);

    if (!dadosFiltrados.length) {
      toast.error("Nao ha vendas para exportar neste relatorio.");
      return;
    }

    const dadosOrdenados = ordenarVendasRelatorio(dadosFiltrados, ordenacaoRelatorio);
    const chaves = colunasRelatorio;
    const colunas = COLUNAS_RELATORIO_VENDAS.filter((coluna) => chaves.includes(coluna.key));

    if (!colunas.length) {
      toast.error("Selecione pelo menos uma coluna para exportar.");
      return;
    }

    const linhas = dadosOrdenados.map((venda) =>
      colunas.map((coluna) => {
        const bruto = coluna.value(venda);
        return coluna.key === "data_venda" ? formatarData(bruto) : bruto;
      }),
    );

    const dataArquivo = new Date().toISOString().slice(0, 10);
    const sufixo = escopo === "geral" ? "geral" : "filtrado";
    try {
      await exportarPlanilhasExcel(
        [
          {
            sheet: "Lista de Vendas",
            linhas: [colunas.map((coluna) => coluna.label), ...linhas],
          },
        ],
        `vendas_${sufixo}_${dataArquivo}.xlsx`,
      );
      toast.success(`Relatorio gerado com ${linhas.length} venda(s).`);
    } catch (error) {
      console.error("Erro ao exportar relatorio de vendas:", error);
      toast.error("Nao foi possivel gerar o arquivo Excel.");
    }
  };

  const toggleColunaRelatorio = (key) => {
    setColunasRelatorio((prev) =>
      prev.includes(key) ? prev.filter((item) => item !== key) : [...prev, key],
    );
  };

  const abrirVendasEmAberto = () => {
    setFiltroStatusLista("em_aberto");
    setAbaAtiva("lista");
  };

  const limparFiltroStatusLista = () => {
    setFiltroStatusLista("");
  };

  const adicionarFeriadoCustomizado = () => {
    if (!novoFeriadoData) {
      toast.error("Informe a data do feriado.");
      return;
    }

    setFeriadosCustomizados((prev) => {
      const semDuplicado = prev.filter((feriado) => feriado.data !== novoFeriadoData);
      return [
        ...semDuplicado,
        {
          data: novoFeriadoData,
          nome: novoFeriadoNome.trim() || "Feriado local",
        },
      ].sort((a, b) => a.data.localeCompare(b.data));
    });
    setNovoFeriadoData("");
    setNovoFeriadoNome("");
    toast.success("Feriado salvo para a contagem de dias úteis.");
  };

  const removerFeriadoCustomizado = (data) => {
    setFeriadosCustomizados((prev) => prev.filter((feriado) => feriado.data !== data));
  };

  const CORES_GRAFICOS = [
    "#3B82F6",
    "#10B981",
    "#F59E0B",
    "#EF4444",
    "#8B5CF6",
    "#EC4899",
    "#14B8A6",
    "#F97316",
  ];

  // Funções de filtragem
  const aplicarFiltros = (dados, tipo) => {
    if (!dados || dados.length === 0) return dados;

    let dadosFiltrados = [...dados];

    // Filtro por funcionário
    if (filtroFuncionario && tipo === "funcionario") {
      dadosFiltrados = dadosFiltrados.filter(
        (item) => item.funcionario === filtroFuncionario,
      );
    }

    // Filtro por forma de pagamento
    if (filtroFormaPagamento && tipo === "formaPagamento") {
      dadosFiltrados = dadosFiltrados.filter(
        (item) => item.forma_pagamento === filtroFormaPagamento,
      );
    }

    // Filtro por categoria
    if (filtroCategoria && tipo === "categoria") {
      dadosFiltrados = dadosFiltrados.filter(
        (item) => item.categoria === filtroCategoria,
      );
    }

    return dadosFiltrados;
  };

  const formasRecebimentoConsolidadas = useMemo(() => {
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
  }, [formasRecebimento]);

  const formasRecebimentoComparacaoConsolidadas = useMemo(() => {
    const mapa = new Map();
    (formasRecebimentoComparacao || []).forEach((item) => {
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
  }, [formasRecebimentoComparacao]);

  const formasRecebimentoFiltradas = aplicarFiltros(
    formasRecebimentoConsolidadas,
    "formaPagamento",
  );
  const vendasPorFuncionarioFiltradas = aplicarFiltros(
    vendasPorFuncionario,
    "funcionario",
  );
  const produtosDetalhadosFiltrados = aplicarFiltros(
    produtosDetalhados,
    "categoria",
  );

  const feriadosPorData = useMemo(() => {
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
  }, [dataInicio, dataFim, feriadosCustomizados]);

  const vendasPorDataCalendario = useMemo(() => {
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
      const sabadoUtil = sabado && configDiasUteis.considerarSabadoDiaUtil;
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
  }, [configDiasUteis.considerarSabadoDiaUtil, dataInicio, dataFim, feriadosPorData, vendasPorData]);

  const resumoDiasPeriodo = useMemo(() => {
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
      mediaDiaTrabalhado: diasTrabalhados.length > 0 ? totalLiquidoDiasTrabalhados / diasTrabalhados.length : 0,
    };
  }, [vendasPorDataCalendario]);

  const listaVendasVisiveis = useMemo(
    () =>
      listaVendasComImpostoAjustado.filter(
        (venda) => String(venda?.status || "").toLowerCase() !== "cancelada",
      ),
    [listaVendasComImpostoAjustado],
  );

  const listaVendasFiltrada = useMemo(() => {
    if (filtroStatusLista !== "em_aberto") return listaVendasVisiveis;
    return listaVendasVisiveis.filter(vendaEstaEmAberto);
  }, [filtroStatusLista, listaVendasVisiveis]);

  const vendasResumoPeriodo = useMemo(() => listaVendasVisiveis, [listaVendasVisiveis]);

  const fluxoResultadoCards = useMemo(() => {
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
        valor: Number(resumo.lucro_total || 0),
        detalhe: "Venda liquida menos custo dos produtos.",
        cor:
          Number(resumo.lucro_total || 0) >= 0
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
  }, [resumo]);

  const vendasPorDiaSemanaResumo = useMemo(() => {
    const dias = [
      { chave: 1, nome: "Segunda", curto: "Seg" },
      { chave: 2, nome: "Terca", curto: "Ter" },
      { chave: 3, nome: "Quarta", curto: "Qua" },
      { chave: 4, nome: "Quinta", curto: "Qui" },
      { chave: 5, nome: "Sexta", curto: "Sex" },
      { chave: 6, nome: "Sabado", curto: "Sab" },
      { chave: 0, nome: "Domingo", curto: "Dom" },
    ];
    const mapa = new Map(
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

    vendasResumoPeriodo.forEach((venda) => {
      const data = parseDataHoraLocal(venda.data_venda);
      if (!data) return;
      const item = mapa.get(data.getDay());
      if (!item) return;
      item.quantidade += 1;
      item.valor_bruto += Number(venda.venda_bruta || 0);
      item.valor_liquido += Number(venda.venda_liquida || 0);
    });

    return Array.from(mapa.values()).map((item) => ({
      ...item,
      ticket_medio: item.quantidade > 0 ? item.valor_liquido / item.quantidade : 0,
    }));
  }, [vendasResumoPeriodo]);

  const vendasPorHorarioResumo = useMemo(() => {
    const horas = Array.from({ length: 24 }, (_, hora) => ({
      hora,
      faixa: `${String(hora).padStart(2, "0")}h`,
      quantidade: 0,
      valor_bruto: 0,
      valor_liquido: 0,
      ticket_medio: 0,
    }));

    vendasResumoPeriodo.forEach((venda) => {
      const data = parseDataHoraLocal(venda.data_venda);
      if (!data) return;
      const item = horas[data.getHours()];
      item.quantidade += 1;
      item.valor_bruto += Number(venda.venda_bruta || 0);
      item.valor_liquido += Number(venda.venda_liquida || 0);
    });

    return horas.map((item) => ({
      ...item,
      ticket_medio: item.quantidade > 0 ? item.valor_liquido / item.quantidade : 0,
    }));
  }, [vendasResumoPeriodo]);

  const vendasPorHorarioComMovimento = useMemo(
    () => vendasPorHorarioResumo.filter((item) => item.quantidade > 0),
    [vendasPorHorarioResumo],
  );

  const melhorDiaSemana = useMemo(
    () =>
      [...vendasPorDiaSemanaResumo].sort(
        (a, b) => Number(b.valor_liquido || 0) - Number(a.valor_liquido || 0),
      )[0],
    [vendasPorDiaSemanaResumo],
  );

  const melhorHorario = useMemo(
    () =>
      [...vendasPorHorarioComMovimento].sort(
        (a, b) => Number(b.valor_liquido || 0) - Number(a.valor_liquido || 0),
      )[0],
    [vendasPorHorarioComMovimento],
  );

  const analisePromocoes = useMemo(() => {
    const topProdutos = new Map();
    let vendasPromocao = 0;
    let vendasNormais = 0;
    let valorVendasPromocao = 0;
    let valorVendasNormais = 0;
    let valorItensPromocionais = 0;
    let descontoPromocional = 0;

    vendasResumoPeriodo.forEach((venda) => {
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
  }, [vendasResumoPeriodo]);

  const totalizadoresListaVendas = useMemo(() => {
    const totais = listaVendasFiltrada.reduce(
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
  }, [listaVendasFiltrada]);

  const formatarDeducaoTotalizador = (valor) =>
    Number(valor || 0) > 0 ? `-${formatarMoeda(valor)}` : formatarMoeda(0);

  const cardsTotalizadoresLista = [
    { label: "Vendas", value: totalizadoresListaVendas.quantidade.toLocaleString("pt-BR") },
    { label: "Com NF", value: totalizadoresListaVendas.com_nf.toLocaleString("pt-BR") },
    { label: "Venda Bruta", value: formatarMoeda(totalizadoresListaVendas.venda_bruta) },
    { label: "Tx Loja", value: `+${formatarMoeda(totalizadoresListaVendas.taxa_loja)}` },
    { label: "Desconto", value: formatarDeducaoTotalizador(totalizadoresListaVendas.desconto) },
    { label: "Tx. Entrega", value: formatarDeducaoTotalizador(totalizadoresListaVendas.taxa_entrega) },
    { label: "Tx. Operac.", value: formatarDeducaoTotalizador(totalizadoresListaVendas.taxa_operacional) },
    { label: "Tx. Cartao", value: formatarDeducaoTotalizador(totalizadoresListaVendas.taxa_cartao) },
    { label: "Comissao", value: formatarDeducaoTotalizador(totalizadoresListaVendas.comissao) },
    { label: "Imposto", value: formatarDeducaoTotalizador(totalizadoresListaVendas.imposto) },
    { label: "Custo Camp.", value: formatarDeducaoTotalizador(totalizadoresListaVendas.custo_campanha) },
    { label: "Liquida", value: formatarMoeda(totalizadoresListaVendas.venda_liquida) },
    { label: "Custo", value: formatarDeducaoTotalizador(totalizadoresListaVendas.custo_produtos) },
    { label: "Lucro", value: formatarMoeda(totalizadoresListaVendas.lucro) },
    { label: "MG Venda", value: `${totalizadoresListaVendas.margem_sobre_venda}%` },
    { label: "MG Custo", value: `${totalizadoresListaVendas.margem_sobre_custo}%` },
  ];

  const getTextoComparacao = () => {
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
  };

  const exportarParaPDF = async () => {
    if (!dataInicio || !dataFim) {
      toast.error("Selecione um período para gerar o relatório");
      return;
    }

    try {
      toast.loading("Gerando PDF...", { id: "pdf" });

      const params = new URLSearchParams({
        data_inicio: dataInicio,
        data_fim: dataFim,
      });

      if (filtroFuncionario) params.append("funcionario", filtroFuncionario);
      if (filtroFormaPagamento)
        params.append("forma_pagamento", filtroFormaPagamento);
      if (filtroCategoria) params.append("categoria", filtroCategoria);

      const response = await api.get(
        `/relatorios/vendas/export/pdf?${params.toString()}`,
        {
          responseType: "blob",
        },
      );

      const url = globalThis.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute(
        "download",
        `relatorio_vendas_${dataInicio}_${dataFim}.pdf`,
      );
      document.body.appendChild(link);
      link.click();
      link.remove();

      toast.success("📄 PDF exportado com sucesso!", { id: "pdf" });
    } catch (error) {
      console.error("Erro ao exportar PDF:", error);
      toast.error("Erro ao exportar PDF", { id: "pdf" });
    }
  };

  const exportarParaExcel = async () => {
    // Aba Resumo
    const resumoData = [
      ["RELATÓRIO DE VENDAS"],
      ["Período:", `${formatarData(dataInicio)} até ${formatarData(dataFim)}`],
      [""],
      ["Métrica", "Valor"],
      ["Venda Bruta", resumo.venda_bruta],
      ["Taxa de Entrega", resumo.taxa_entrega],
      ["Desconto", resumo.desconto],
      ["Venda Líquida", resumo.venda_liquida],
      ["Em Aberto", resumo.em_aberto],
      ["Quantidade de Vendas", resumo.quantidade_vendas],
    ];
    const planilhas = [
      {
        sheet: "Resumo",
        linhas: resumoData,
      },
    ];

    // Aba Vendas por Data
    if (vendasPorDataCalendario.length > 0) {
      const vendasData = [
        [
          "Data",
          "Dia",
          "Qtd",
          "Tkt. Médio",
          "Vl. bruto",
          "Taxa entrega",
          "Desconto",
          "(%)",
          "Vl. líquido",
          "Vl. recebido",
          "Saldo aberto",
        ],
        ...vendasPorDataCalendario.map((v) => [
          formatarData(v.data),
          v.feriado_nome || v.dia_semana,
          v.quantidade,
          v.ticket_medio,
          v.valor_bruto,
          v.taxa_entrega,
          v.desconto,
          v.percentual_desconto,
          v.valor_liquido,
          v.valor_recebido,
          v.saldo_aberto,
        ]),
      ];
      planilhas.push({
        sheet: "Vendas por Data",
        linhas: vendasData,
      });
    }

    // Aba Formas de Recebimento
    if (formasRecebimentoFiltradas.length > 0) {
      const formasData = [
        ["Forma", "Valor pago"],
        ...formasRecebimentoFiltradas.map((f) => [
          f.forma_pagamento,
          f.valor_total,
        ]),
      ];
      planilhas.push({
        sheet: "Formas Pagamento",
        linhas: formasData,
      });
    }

    const fileName = `relatorio_vendas_${dataInicio}_${dataFim}.xlsx`;
    try {
      await exportarPlanilhasExcel(planilhas, fileName);
      toast.success("Excel exportado com sucesso!");
    } catch (error) {
      console.error("Erro ao exportar Excel:", error);
      toast.error("Erro ao exportar Excel");
    }
  };

  const aplicarFiltroRapido = (filtro) => {
    // Obter data atual sem conversão de timezone
    const agora = new Date();
    const ano = agora.getFullYear();
    const mes = String(agora.getMonth() + 1).padStart(2, "0");
    const dia = String(agora.getDate()).padStart(2, "0");
    const hoje = `${ano}-${mes}-${dia}`;

    let inicio, fim;

    switch (filtro) {
      case "hoje":
        inicio = fim = hoje;
        break;
      case "ontem": {
        const dataOntem = new Date(agora);
        dataOntem.setDate(agora.getDate() - 1);
        const anoOntem = dataOntem.getFullYear();
        const mesOntem = String(dataOntem.getMonth() + 1).padStart(2, "0");
        const diaOntem = String(dataOntem.getDate()).padStart(2, "0");
        inicio = fim = `${anoOntem}-${mesOntem}-${diaOntem}`;
        break;
      }
      case "esta_semana": {
        const diaSemana = agora.getDay(); // 0=domingo, 1=segunda, ..., 6=sábado
        const diasDesdeSegunda = diaSemana === 0 ? 6 : diaSemana - 1; // Se domingo, volta 6 dias; senão volta (dia-1)
        const primeiroDia = new Date(agora);
        primeiroDia.setDate(agora.getDate() - diasDesdeSegunda);
        const anoPri = primeiroDia.getFullYear();
        const mesPri = String(primeiroDia.getMonth() + 1).padStart(2, "0");
        const diaPri = String(primeiroDia.getDate()).padStart(2, "0");
        inicio = `${anoPri}-${mesPri}-${diaPri}`;
        fim = hoje;
        break;
      }
      case "este_mes":
        inicio = `${ano}-${mes}-01`;
        fim = hoje;
        break;
      case "mes_anterior": {
        const mesPassado = new Date(
          agora.getFullYear(),
          agora.getMonth() - 1,
          1,
        );
        const ultimoDia = new Date(agora.getFullYear(), agora.getMonth(), 0);
        const anoMesPass = mesPassado.getFullYear();
        const numeroMesPass = String(mesPassado.getMonth() + 1).padStart(
          2,
          "0",
        );
        const anoUltDia = ultimoDia.getFullYear();
        const mesUltDia = String(ultimoDia.getMonth() + 1).padStart(2, "0");
        const diaUltDia = String(ultimoDia.getDate()).padStart(2, "0");
        inicio = `${anoMesPass}-${numeroMesPass}-01`;
        fim = `${anoUltDia}-${mesUltDia}-${diaUltDia}`;
        break;
      }
      case "ultimos_7_dias": {
        const sete = new Date(agora);
        sete.setDate(agora.getDate() - 7);
        const anoSete = sete.getFullYear();
        const mesSete = String(sete.getMonth() + 1).padStart(2, "0");
        const diaSete = String(sete.getDate()).padStart(2, "0");
        inicio = `${anoSete}-${mesSete}-${diaSete}`;
        fim = hoje;
        break;
      }
      case "ultimos_30_dias": {
        const trinta = new Date(agora);
        trinta.setDate(agora.getDate() - 30);
        const anoTrinta = trinta.getFullYear();
        const mesTrinta = String(trinta.getMonth() + 1).padStart(2, "0");
        const diaTrinta = String(trinta.getDate()).padStart(2, "0");
        inicio = `${anoTrinta}-${mesTrinta}-${diaTrinta}`;
        fim = hoje;
        break;
      }
      case "este_ano":
        inicio = `${ano}-01-01`;
        fim = hoje;
        break;
      default:
        return;
    }

    setDataInicio(inicio);
    setDataFim(fim);
    setFiltroSelecionado(filtro);
  };

  const calcularPeriodoComparacao = () => {
    // Parse manual das datas para evitar problemas de timezone
    const [anoIni, mesIni, diaIni] = dataInicio.split("-").map(Number);
    const [anoFim, mesFim, diaFim] = dataFim.split("-").map(Number);

    const inicio = new Date(anoIni, mesIni - 1, diaIni);
    const fim = new Date(anoFim, mesFim - 1, diaFim);
    const diffDias = Math.floor((fim - inicio) / (1000 * 60 * 60 * 24)) + 1;

    let inicioComp, fimComp;

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

    // Formatar manualmente para evitar problemas de timezone
    const anoIniComp = inicioComp.getFullYear();
    const mesIniComp = String(inicioComp.getMonth() + 1).padStart(2, "0");
    const diaIniComp = String(inicioComp.getDate()).padStart(2, "0");

    const anoFimComp = fimComp.getFullYear();
    const mesFimComp = String(fimComp.getMonth() + 1).padStart(2, "0");
    const diaFimComp = String(fimComp.getDate()).padStart(2, "0");

    return {
      data_inicio: `${anoIniComp}-${mesIniComp}-${diaIniComp}`,
      data_fim: `${anoFimComp}-${mesFimComp}-${diaFimComp}`,
    };
  };

  const calcularVariacao = (valorAtual, valorAnterior) => {
    if (!valorAnterior || valorAnterior === 0)
      return { valor: 0, percentual: 0 };
    const diff = valorAtual - valorAnterior;
    const perc = ((diff / valorAnterior) * 100).toFixed(1);
    return { valor: diff, percentual: Number.parseFloat(perc) };
  };

  const carregarDados = async () => {
    if (!podeVerFinanceiroCompleto) return;
    if (!dataInicio || !dataFim) return;

    setLoading(true);

    try {
      const response = await api.get("/relatorios/vendas/relatorio", {
        params: { data_inicio: dataInicio, data_fim: dataFim },
      });
      const data = response.data;

      setResumo(data.resumo || {});
      setVendasPorData(data.vendas_por_data || []);
      setFormasRecebimento(data.formas_recebimento || []);
      setVendasPorFuncionario(data.vendas_por_funcionario || []);
      setVendasPorTipo(data.vendas_por_tipo || []);
      setVendasPorGrupo(data.vendas_por_grupo || []);
      setProdutosDetalhados(data.produtos_detalhados || []);
      setProdutosAnalise(data.produtos_analise || []);
      setListaVendas(data.lista_vendas || []);

      if (modoComparacao || abaAtiva === "comparacao") {
        const periodoComp = calcularPeriodoComparacao();
        const responseComp = await api.get("/relatorios/vendas/relatorio", {
          params: periodoComp,
        });
        setResumoComparacao(responseComp.data.resumo || {});
        setFormasRecebimentoComparacao(
          responseComp.data.formas_recebimento || [],
        );
        setVendasPorGrupoComparacao(responseComp.data.vendas_por_grupo || []);
        setVendasPorFuncionarioComparacao(
          responseComp.data.vendas_por_funcionario || [],
        );
      } else {
        // Limpar dados de comparação quando desativado
        setResumoComparacao({
          venda_bruta: 0,
          taxa_entrega: 0,
          desconto: 0,
          venda_liquida: 0,
          em_aberto: 0,
          quantidade_vendas: 0,
        });
      }
    } catch (error) {
      console.error("Erro ao carregar relatório:", error);
    } finally {
      setLoading(false);
    }
  };

  // Função para calcular análise inteligente
  const calcularAnaliseInteligente = () => {
    if (!produtosAnalise || produtosAnalise.length === 0) {
      setProdutosMaisLucrativos([]);
      setProdutosPorCategoria({});
      setAlertasInteligentesVendas([]);
      setPrevisaoProximos7Dias(0);
      return;
    }

    // Calcular produtos mais lucrativos com margem
    const produtosComMargem = produtosAnalise.map((produto) => {
      const custo = sanitizarNumero(produto.custo_total);
      const preco = sanitizarNumero(produto.valor_total);
      const quantidade = sanitizarNumero(produto.quantidade) || 1;
      const lucro = preco - custo;
      const margem = custo > 0 ? (lucro / custo) * 100 : 0;

      return {
        nome: produto.nome || produto.produto || "Produto sem nome",
        marca: produto.marca || "-",
        quantidade: quantidade,
        custo: sanitizarNumero(custo / quantidade),
        preco: sanitizarNumero(preco / quantidade),
        lucro_total: sanitizarNumero(lucro),
        margem: sanitizarNumero(margem),
        categoria: produto.categoria || "Sem Categoria",
      };
    });

    // Ordenar por lucro total decrescente
    const produtosOrdenadosPorLucro = [...produtosComMargem];
    produtosOrdenadosPorLucro.sort((a, b) => b.lucro_total - a.lucro_total);
    const topProdutos = produtosOrdenadosPorLucro.slice(0, 20);

    setProdutosMaisLucrativos(topProdutos);

    // Agrupar por categoria
    const porCategoria = {};
    produtosComMargem.forEach((produto) => {
      const cat = produto.categoria || "Sem Categoria";
      if (!porCategoria[cat]) {
        porCategoria[cat] = {
          quantidade: 0,
          total: 0,
          margens: [],
        };
      }
      porCategoria[cat].quantidade += produto.quantidade;
      porCategoria[cat].total += produto.preco * produto.quantidade;
      porCategoria[cat].margens.push(produto.margem);
    });

    // Calcular margem média por categoria
    Object.keys(porCategoria).forEach((cat) => {
      const margens = porCategoria[cat].margens;
      const somaMargens = margens.reduce(
        (a, b) => sanitizarNumero(a) + sanitizarNumero(b),
        0,
      );
      porCategoria[cat].margem_media = sanitizarNumero(
        margens.length > 0 ? somaMargens / margens.length : 0,
      );
      delete porCategoria[cat].margens;
    });

    setProdutosPorCategoria(porCategoria);

    const alertas = [];

    const qtdAtual = sanitizarNumero(resumo.quantidade_vendas);
    const qtdAnterior = sanitizarNumero(resumoComparacao.quantidade_vendas);
    if (qtdAnterior > 0 && qtdAtual < qtdAnterior) {
      const queda = Number((((qtdAnterior - qtdAtual) / qtdAnterior) * 100).toFixed(1));
      alertas.push({
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
        alertas.push({
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
      alertas.push({
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
      alertas.push({
        id: "oportunidade-upsell",
        tipo: "oportunidade",
        titulo: "Oportunidade de crescimento",
        mensagem: `Produtos com alta margem e baixo volume: ${altaMargemBaixoVolume.map((p) => p.nome).join(", ")}.`,
        recomendacao:
          "Destacar esses itens no atendimento e criar combo promocional para aumentar giro.",
      });
    }

    const basePrevisao = (vendasPorData || []).slice(-14);
    if (basePrevisao.length > 0) {
      const mediaDiaria =
        basePrevisao.reduce(
          (soma, item) => soma + sanitizarNumero(item.valor_liquido),
          0,
        ) / basePrevisao.length;
      setPrevisaoProximos7Dias(sanitizarNumero(mediaDiaria * 7));
    } else {
      setPrevisaoProximos7Dias(0);
    }

    setAlertasInteligentesVendas(alertas);
  };

  // Recalcular análise quando produtos mudarem
  useEffect(() => {
    if (abaAtiva === "analise") {
      calcularAnaliseInteligente();
    }
  }, [produtosAnalise, abaAtiva, resumo, resumoComparacao, vendasPorData]);

  useEffect(() => {
    if (podeVerFinanceiroCompleto) {
      carregarDados();
    }
  }, [
    dataInicio,
    dataFim,
    modoComparacao,
    periodoComparacao,
    abaAtiva,
    podeVerFinanceiroCompleto,
  ]);

  useEffect(() => {
    if (!podeVerFinanceiroCompleto) {
      setAbaAtiva("historico-cliente");
      setModoComparacao(false);
    }
  }, [podeVerFinanceiroCompleto]);

  useEffect(() => {
    window.localStorage.setItem(
      getFeriadosStorageKey(),
      JSON.stringify(feriadosCustomizados),
    );
  }, [feriadosCustomizados]);

  useEffect(() => {
    window.localStorage.setItem(
      getDiasUteisStorageKey(),
      JSON.stringify(configDiasUteis),
    );
  }, [configDiasUteis]);

  useEffect(() => {
    const fecharMenuAoClicarFora = (event) => {
      if (
        menuRelatoriosRef.current &&
        !menuRelatoriosRef.current.contains(event.target)
      ) {
        setMenuRelatoriosAberto(false);
      }
    };

    document.addEventListener("mousedown", fecharMenuAoClicarFora);
    return () => document.removeEventListener("mousedown", fecharMenuAoClicarFora);
  }, []);

  // Aplicar filtro "Este mês" ao carregar componente pela primeira vez
  useEffect(() => {
    aplicarFiltroRapido("este_mes");
  }, []); // Roda apenas uma vez ao montar o componente

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      {/* Cabeçalho com Filtros */}
      <div className="mb-6 bg-white p-4 rounded-lg shadow">
        <div className="flex justify-between items-center mb-4">
          <h1 className="text-2xl font-bold text-gray-800">
            Consulta de Vendas
          </h1>

          {podeVerFinanceiroCompleto ? (
            <div className="flex items-center gap-4">
            <div className="relative" ref={menuRelatoriosRef}>
              <button
                onClick={() => setMenuRelatoriosAberto((prev) => !prev)}
                className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
              >
                <FileText className="w-4 h-4" />
                <span className="font-medium">Relatorios</span>
              </button>

              {menuRelatoriosAberto && (
                <div className="absolute right-0 mt-2 w-72 bg-white rounded-lg shadow-lg border border-gray-200 z-40">
                  <button
                    onClick={() => {
                      setMenuRelatoriosAberto(false);
                      exportarRelatorioListaVendas({ escopo: "geral" });
                    }}
                    className="w-full text-left px-4 py-3 text-sm hover:bg-gray-50"
                  >
                    Relatorio geral da lista de vendas
                  </button>
                  <button
                    onClick={() => {
                      setMenuRelatoriosAberto(false);
                      exportarRelatorioListaVendas({ escopo: "filtrado" });
                    }}
                    className="w-full text-left px-4 py-3 text-sm hover:bg-gray-50 border-t border-gray-100"
                  >
                    Relatorio do que filtrei
                  </button>
                  <button
                    onClick={() => {
                      setMenuRelatoriosAberto(false);
                      setModalRelatorioAberto(true);
                    }}
                    className="w-full text-left px-4 py-3 text-sm hover:bg-gray-50 border-t border-gray-100"
                  >
                    Relatorio personalizado
                  </button>
                </div>
              )}
            </div>
            {/* Botão Exportar PDF */}
            <button
              onClick={exportarParaPDF}
              disabled={!dataInicio || !dataFim}
              title={
                dataInicio && dataFim
                  ? `Exportar PDF de ${formatarData(dataInicio)} até ${formatarData(dataFim)}`
                  : "Selecione um período"
              }
              className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
            >
              <FileText className="w-4 h-4" />
              <div className="flex flex-col items-start">
                <span className="font-medium">Exportar PDF</span>
                {dataInicio && dataFim && (
                  <span className="text-xs opacity-90">
                    ({formatarData(dataInicio)} - {formatarData(dataFim)})
                  </span>
                )}
              </div>
            </button>

            {/* Botão Exportar Excel */}
            <button
              onClick={exportarParaExcel}
              disabled={!dataInicio || !dataFim}
              title={
                dataInicio && dataFim
                  ? `Exportar dados de ${formatarData(dataInicio)} até ${formatarData(dataFim)}`
                  : "Selecione um período"
              }
              className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
            >
              <Download className="w-4 h-4" />
              <div className="flex flex-col items-start">
                <span className="font-medium">Exportar Excel</span>
                {dataInicio && dataFim && (
                  <span className="text-xs opacity-90">
                    ({formatarData(dataInicio)} - {formatarData(dataFim)})
                  </span>
                )}
              </div>
            </button>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={modoComparacao}
                onChange={(e) => setModoComparacao(e.target.checked)}
                className="w-4 h-4 text-blue-600 rounded"
              />
              <span className="text-sm font-medium text-gray-700">
                Comparar com:
              </span>
            </label>

            {modoComparacao && (
              <select
                value={periodoComparacao}
                onChange={(e) => setPeriodoComparacao(e.target.value)}
                className="border rounded px-3 py-2 text-sm bg-blue-50 font-medium"
              >
                <option value="periodo_anterior">
                  Período imediatamente anterior (mesmo nº de dias)
                </option>
                <option value="mes_anterior">
                  Mesmo período do mês passado
                </option>
                <option value="ano_anterior">
                  Mesmo período do ano passado
                </option>
              </select>
            )}
            </div>
          ) : null}
        </div>

        {!podeVerFinanceiroCompleto && (
          <div className="mb-4 rounded-lg border border-indigo-200 bg-indigo-50 p-3 text-sm text-indigo-700">
            Acesso limitado: você pode consultar apenas a aba Histórico por Cliente.
          </div>
        )}

        {podeVerFinanceiroCompleto && (
          <div className="flex flex-wrap gap-2 mb-4">
          {[
            { id: "hoje", label: "Hoje" },
            { id: "ontem", label: "Ontem" },
            { id: "esta_semana", label: "Esta semana" },
            { id: "este_mes", label: "Este mês" },
            { id: "mes_anterior", label: "Mês anterior" },
            { id: "ultimos_7_dias", label: "Últimos 7 dias" },
            { id: "ultimos_30_dias", label: "Últimos 30 dias" },
            { id: "este_ano", label: "Este ano" },
            { id: "personalizado", label: "Personalizado" },
          ].map((filtro) => (
            <button
              key={filtro.id}
              onClick={() => {
                if (filtro.id === "personalizado") {
                  setFiltroSelecionado("personalizado");
                } else {
                  aplicarFiltroRapido(filtro.id);
                }
              }}
              className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                filtroSelecionado === filtro.id
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
            >
              {filtro.label}
            </button>
          ))}
          </div>
        )}

        {podeVerFinanceiroCompleto && filtroSelecionado === "personalizado" && (
          <div className="flex gap-2 items-center mb-4 p-3 bg-gray-50 rounded">
            <Calendar className="w-5 h-5 text-gray-500" />
            <input
              type="date"
              value={dataInicio}
              onChange={(e) => setDataInicio(e.target.value)}
              className="border rounded px-3 py-2"
            />
            <span className="text-gray-600">até</span>
            <input
              type="date"
              value={dataFim}
              onChange={(e) => setDataFim(e.target.value)}
              className="border rounded px-3 py-2"
            />
          </div>
        )}

        {/* Filtros Avançados */}
        {podeVerFinanceiroCompleto && (
          <div className="flex gap-2 items-center mb-4 p-3 bg-blue-50 rounded border border-blue-200">
          <Filter className="w-5 h-5 text-blue-600" />
          <span className="text-sm font-medium text-gray-700">
            Filtros Avançados:
          </span>

          <select
            value={filtroFuncionario}
            onChange={(e) => setFiltroFuncionario(e.target.value)}
            className="border rounded px-3 py-2 text-sm"
          >
            <option value="">Todos os funcionários</option>
            {vendasPorFuncionario.map((f) => (
              <option key={`func-${f.funcionario || "sem-nome"}`} value={f.funcionario}>
                {f.funcionario}
              </option>
            ))}
          </select>

          <select
            value={filtroFormaPagamento}
            onChange={(e) => setFiltroFormaPagamento(e.target.value)}
            className="border rounded px-3 py-2 text-sm"
          >
            <option value="">Todas as formas</option>
            {formasRecebimentoConsolidadas.map((f) => (
              <option key={`forma-${f.forma_pagamento || "sem-forma"}`} value={f.forma_pagamento}>
                {f.forma_pagamento}
              </option>
            ))}
          </select>

          <select
            value={filtroCategoria}
            onChange={(e) => setFiltroCategoria(e.target.value)}
            className="border rounded px-3 py-2 text-sm"
          >
            <option value="">Todas as categorias</option>
            {produtosDetalhados.map((cat) => (
              <option key={`cat-${cat.categoria || "sem-categoria"}`} value={cat.categoria}>
                {cat.categoria}
              </option>
            ))}
          </select>

          <button
            onClick={() => {
              setFiltroFuncionario("");
              setFiltroFormaPagamento("");
              setFiltroCategoria("");
            }}
            className="px-3 py-2 bg-gray-200 text-gray-700 rounded text-sm hover:bg-gray-300 transition-colors"
          >
            Limpar Filtros
          </button>

          <button
            onClick={() => setMostrarGraficos(!mostrarGraficos)}
            className="ml-auto px-3 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 transition-colors flex items-center gap-2"
          >
            <BarChart3 className="w-4 h-4" />
            {mostrarGraficos ? "Ocultar" : "Mostrar"} Gráficos
          </button>
          </div>
        )}

        {/* Abas */}
        <div className="flex gap-2 border-b">
          {podeVerFinanceiroCompleto && (
            <button
              onClick={() => setAbaAtiva("resumo")}
              className={`px-4 py-2 font-medium ${
                abaAtiva === "resumo"
                  ? "border-b-2 border-blue-500 text-blue-600"
                  : "text-gray-600 hover:text-gray-800"
              }`}
            >
              Resumo
            </button>
          )}
          <button
            onClick={() => setAbaAtiva("historico-cliente")}
            className={`px-4 py-2 font-medium ${
              abaAtiva === "historico-cliente"
                ? "border-b-2 border-purple-500 text-purple-600"
                : "text-gray-600 hover:text-gray-800"
            }`}
          >
            Histórico por Cliente
          </button>
          {podeVerFinanceiroCompleto && (
            <>
              <button
                onClick={() => setAbaAtiva("produtos")}
                className={`px-4 py-2 font-medium ${
                  abaAtiva === "produtos"
                    ? "border-b-2 border-blue-500 text-blue-600"
                    : "text-gray-600 hover:text-gray-800"
                }`}
              >
                Totais por produto/serviço
              </button>
              <button
                onClick={() => setAbaAtiva("lista")}
                className={`px-4 py-2 font-medium ${
                  abaAtiva === "lista"
                    ? "border-b-2 border-blue-500 text-blue-600"
                    : "text-gray-600 hover:text-gray-800"
                }`}
              >
                Lista de Vendas
              </button>
              <button
                onClick={() => setAbaAtiva("comparacao")}
                className={`px-4 py-2 font-medium ${
                  abaAtiva === "comparacao"
                    ? "border-b-2 border-blue-500 text-blue-600"
                    : "text-gray-600 hover:text-gray-800"
                }`}
              >
                Comparação de Períodos
              </button>
              <button
                onClick={() => setAbaAtiva("analise")}
                className={`px-4 py-2 font-medium ${
                  abaAtiva === "analise"
                    ? "border-b-2 border-blue-500 text-blue-600"
                    : "text-gray-600 hover:text-gray-800"
                }`}
              >
                Análise Inteligente
              </button>
            </>
          )}
        </div>
      </div>

      {/* Conteúdo das Abas */}
      {abaAtiva === "resumo" && (
        <div>
          {/* Banner de Comparação */}
          {modoComparacao && (
            <div className="bg-blue-50 border-l-4 border-blue-500 p-4 mb-6 rounded">
              <div className="flex items-center gap-2">
                <svg
                  className="w-5 h-5 text-blue-500"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                    clipRule="evenodd"
                  />
                </svg>
                <div className="text-sm">
                  <span className="font-semibold text-blue-800">
                    Modo Comparação Ativo:
                  </span>
                  <span className="text-blue-700 ml-2">
                    Comparando{" "}
                    <span className="font-medium">
                      {formatarData(dataInicio)} até {formatarData(dataFim)}
                    </span>{" "}
                    com{" "}
                    <span className="font-medium">{getTextoComparacao()}</span>
                  </span>
                </div>
              </div>
            </div>
          )}

          <div className="mb-6 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <div className="mb-3 flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <h3 className="text-lg font-semibold text-gray-800">
                  Composicao do resultado
                </h3>
                <p className="text-sm text-gray-500">
                  Sequencia da venda bruta ate o lucro do periodo filtrado.
                </p>
              </div>
              <div className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
                {formatarMoeda(resumo.venda_liquida || 0)} liquido antes do CMV
              </div>
            </div>
            <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-5 2xl:grid-cols-6">
              {fluxoResultadoCards.map((card) => {
                const clicavel = card.acao === "vendas_em_aberto";
                const Container = clicavel ? "button" : "div";
                const ativo =
                  clicavel &&
                  abaAtiva === "lista" &&
                  filtroStatusLista === "em_aberto";

                return (
                  <Container
                    key={card.titulo}
                    type={clicavel ? "button" : undefined}
                    onClick={clicavel ? abrirVendasEmAberto : undefined}
                    className={`min-h-[116px] rounded-lg border p-3 text-left shadow-sm transition ${card.cor} ${
                      clicavel
                        ? "hover:brightness-95 focus:outline-none focus:ring-4 focus:ring-red-100"
                        : ""
                    } ${ativo ? "ring-4 ring-red-100" : ""}`}
                  >
                    <div className="mb-2 flex items-center justify-between gap-2">
                      <span className="text-xs font-semibold uppercase tracking-wide">
                        {card.titulo}
                      </span>
                      <span className="rounded-full bg-white/70 px-2 py-0.5 text-xs font-bold">
                        {card.sinal || "R$"}
                      </span>
                    </div>
                    <div className="text-xl font-bold">
                      {card.percentual ? `${card.valor}%` : formatarMoeda(card.valor)}
                    </div>
                    <p className="mt-2 text-xs opacity-75">{card.detalhe}</p>
                    {clicavel ? (
                      <p className="mt-1 text-xs font-semibold opacity-80">
                        Clique para ver as vendas em aberto.
                      </p>
                    ) : null}
                  </Container>
                );
              })}
            </div>
          </div>

          <div className="mb-6 rounded-lg border border-blue-100 bg-white p-4 shadow-sm">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <h3 className="text-lg font-semibold text-gray-800">
                  Dias úteis e média operacional
                </h3>
                <p className="text-sm text-gray-500">
                  Configure se sábado entra na média. Feriado com faturamento vira dia útil automaticamente.
                </p>
              </div>
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
                <label className="inline-flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-semibold text-emerald-700">
                  <input
                    type="checkbox"
                    checked={configDiasUteis.considerarSabadoDiaUtil}
                    onChange={(event) =>
                      setConfigDiasUteis((prev) => ({
                        ...prev,
                        considerarSabadoDiaUtil: event.target.checked,
                      }))
                    }
                    className="h-4 w-4 rounded border-emerald-300 text-emerald-600 focus:ring-emerald-500"
                  />
                  Sábado conta como dia útil
                </label>
                <button
                  type="button"
                  onClick={() => setMostrarConfigFeriados((prev) => !prev)}
                  className="inline-flex items-center gap-2 rounded-lg border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-semibold text-blue-700 transition hover:bg-blue-100"
                >
                  <Calendar className="h-4 w-4" />
                  Configurar feriados
                </button>
              </div>
            </div>

            <div className="mt-4 grid gap-3 md:grid-cols-4">
              <div className="rounded-xl bg-slate-50 p-3">
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Dias úteis
                </div>
                <div className="mt-1 text-2xl font-bold text-slate-900">
                  {resumoDiasPeriodo.diasUteis}
                </div>
                <div className="text-xs text-slate-500">
                  {resumoDiasPeriodo.totalDias} dia(s) no período
                </div>
              </div>
              <div className="rounded-xl bg-emerald-50 p-3">
                <div className="text-xs font-semibold uppercase tracking-wide text-emerald-600">
                  Dias trabalhados
                </div>
                <div className="mt-1 text-2xl font-bold text-emerald-700">
                  {resumoDiasPeriodo.diasTrabalhados}
                </div>
                <div className="text-xs text-emerald-600">
                  Dia útil com venda registrada
                </div>
              </div>
              <div className="rounded-xl bg-amber-50 p-3">
                <div className="text-xs font-semibold uppercase tracking-wide text-amber-700">
                  Dias úteis sem venda
                </div>
                <div className="mt-1 text-2xl font-bold text-amber-700">
                  {resumoDiasPeriodo.diasUteisSemVenda}
                </div>
                <div className="text-xs text-amber-700">
                  Fora fins de semana/feriados
                </div>
              </div>
              <div className="rounded-xl bg-blue-50 p-3">
                <div className="text-xs font-semibold uppercase tracking-wide text-blue-700">
                  Média por dia útil
                </div>
                <div className="mt-1 text-2xl font-bold text-blue-700">
                  {formatarMoeda(resumoDiasPeriodo.mediaDiaUtil)}
                </div>
                <div className="text-xs text-blue-700">
                  {resumoDiasPeriodo.feriados} feriado(s), {resumoDiasPeriodo.finsDeSemana} fim(ns) de semana
                </div>
              </div>
            </div>

            {mostrarConfigFeriados && (
              <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
                <div className="grid gap-3 md:grid-cols-[180px_1fr_auto]">
                  <input
                    type="date"
                    value={novoFeriadoData}
                    onChange={(event) => setNovoFeriadoData(event.target.value)}
                    className="rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                  />
                  <input
                    type="text"
                    value={novoFeriadoNome}
                    onChange={(event) => setNovoFeriadoNome(event.target.value)}
                    placeholder="Nome do feriado local, municipal ou data sem expediente"
                    className="rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                  />
                  <button
                    type="button"
                    onClick={adicionarFeriadoCustomizado}
                    className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-700"
                  >
                    Salvar feriado
                  </button>
                </div>

                {feriadosCustomizados.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {feriadosCustomizados.map((feriado) => (
                      <span
                        key={feriado.data}
                        className="inline-flex items-center gap-2 rounded-full bg-white px-3 py-1 text-xs font-medium text-slate-700 shadow-sm"
                      >
                        {formatarData(feriado.data)} - {feriado.nome}
                        <button
                          type="button"
                          onClick={() => removerFeriadoCustomizado(feriado.data)}
                          className="text-rose-600 hover:text-rose-700"
                        >
                          remover
                        </button>
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Gráficos */}
          {mostrarGraficos && (
            <div className="grid grid-cols-2 gap-6 mb-6">
              {/* Gráfico de Vendas por Período */}
              <div className="bg-white rounded-lg shadow p-4">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">
                  Vendas no Período
                </h3>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={vendasPorDataCalendario}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="data"
                      tickFormatter={(value) =>
                        formatarDataLocal(value, { day: "2-digit", month: "2-digit" })
                      }
                    />
                    <YAxis
                      tickFormatter={(value) =>
                        `R$ ${(value / 1000).toFixed(0)}k`
                      }
                    />
                    <Tooltip
                      formatter={(value) => formatarMoeda(value)}
                      labelFormatter={(label) => formatarData(label)}
                    />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="valor_bruto"
                      stroke="#3B82F6"
                      strokeWidth={2}
                      name="Venda Bruta"
                    />
                    <Line
                      type="monotone"
                      dataKey="valor_liquido"
                      stroke="#10B981"
                      strokeWidth={2}
                      name="Venda Líquida"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              {/* Gráfico de Formas de Pagamento - Barras Horizontais */}
              <div className="bg-white rounded-lg shadow p-4">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">
                  Formas de Pagamento
                </h3>
                <ResponsiveContainer width="100%" height={350}>
                  <BarChart
                    data={formasRecebimentoFiltradas}
                    layout="vertical"
                    margin={{ top: 5, right: 30, left: 120, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      type="number"
                      tickFormatter={(value) => formatarMoeda(value)}
                    />
                    <YAxis
                      type="category"
                      dataKey="forma_pagamento"
                      width={110}
                      style={{ fontSize: "12px" }}
                    />
                    <Tooltip
                      formatter={(value, name, props) => {
                        const total = formasRecebimentoFiltradas.reduce(
                          (sum, item) => sum + item.valor_total,
                          0,
                        );
                        const percent = ((value / total) * 100).toFixed(1);
                        return [
                          `${formatarMoeda(value)} (${percent}%)`,
                          "Valor",
                        ];
                      }}
                      contentStyle={{
                        backgroundColor: "white",
                        border: "1px solid #ccc",
                        borderRadius: "4px",
                        padding: "8px",
                      }}
                    />
                    <Bar
                      dataKey="valor_total"
                      fill="#3B82F6"
                      radius={[0, 8, 8, 0]}
                      label={{
                        position: "right",
                        formatter: (value) => {
                          const total = formasRecebimentoFiltradas.reduce(
                            (sum, item) => sum + item.valor_total,
                            0,
                          );
                          const percent = ((value / total) * 100).toFixed(1);
                          return `${percent}%`;
                        },
                        style: { fontSize: "11px", fontWeight: "bold" },
                      }}
                    >
                      {formasRecebimentoFiltradas.map((entry, index) => (
                        <Cell
                          key={`cell-forma-${entry.forma_pagamento || entry.name || index}`}
                          fill={CORES_GRAFICOS[index % CORES_GRAFICOS.length]}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Gráfico de Barras - Top 10 Produtos */}
              <div className="bg-white rounded-lg shadow p-4 col-span-2">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">
                  Top 10 Categorias de Produtos
                </h3>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={produtosDetalhadosFiltrados.slice(0, 10)}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="categoria" />
                    <YAxis
                      tickFormatter={(value) =>
                        `R$ ${(value / 1000).toFixed(0)}k`
                      }
                    />
                    <Tooltip formatter={(value) => formatarMoeda(value)} />
                    <Legend />
                    <Bar
                      dataKey="total_liquido"
                      fill="#3B82F6"
                      name="Valor Líquido"
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="bg-white rounded-lg shadow p-4">
                <div className="mb-4">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-800">
                      Vendas por dia da semana
                    </h3>
                    <p className="mt-1 flex flex-wrap items-center gap-2 text-sm text-gray-500">
                      <span>
                        Melhor dia: {melhorDiaSemana?.nome || "-"} com {formatarMoeda(melhorDiaSemana?.valor_liquido || 0)}.
                      </span>
                      <span className="rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-semibold text-blue-700">
                        {melhorDiaSemana?.quantidade || 0} venda(s)
                      </span>
                    </p>
                  </div>
                </div>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={vendasPorDiaSemanaResumo}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="curto" />
                    <YAxis tickFormatter={(value) => `R$ ${(value / 1000).toFixed(0)}k`} />
                    <Tooltip
                      formatter={(value, name, props) => {
                        const isQuantidade = props?.dataKey === "quantidade" || name === "Vendas";
                        return [
                          isQuantidade ? value : formatarMoeda(value),
                          isQuantidade ? "Vendas" : "Valor liquido",
                        ];
                      }}
                      labelFormatter={(label) => {
                        const dia = vendasPorDiaSemanaResumo.find((item) => item.curto === label);
                        return dia?.nome || label;
                      }}
                    />
                    <Legend />
                    <Bar dataKey="valor_liquido" fill="#14B8A6" name="Valor liquido" radius={[6, 6, 0, 0]} />
                    <Bar dataKey="quantidade" fill="#94A3B8" name="Vendas" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="bg-white rounded-lg shadow p-4">
                <div className="mb-4">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-800">
                      Vendas por horario
                    </h3>
                    <p className="mt-1 flex flex-wrap items-center gap-2 text-sm text-gray-500">
                      <span>
                        Pico: {melhorHorario?.faixa || "-"} com {formatarMoeda(melhorHorario?.valor_liquido || 0)}.
                      </span>
                      <span className="rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700">
                        {melhorHorario?.quantidade || 0} venda(s)
                      </span>
                    </p>
                  </div>
                </div>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={vendasPorHorarioComMovimento}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="faixa" />
                    <YAxis tickFormatter={(value) => `R$ ${(value / 1000).toFixed(0)}k`} />
                    <Tooltip
                      formatter={(value, name, props) => {
                        const isQuantidade = props?.dataKey === "quantidade" || name === "Vendas";
                        return [
                          isQuantidade ? value : formatarMoeda(value),
                          isQuantidade ? "Vendas" : "Valor liquido",
                        ];
                      }}
                    />
                    <Legend />
                    <Bar dataKey="valor_liquido" fill="#3B82F6" name="Valor liquido" radius={[6, 6, 0, 0]} />
                    <Bar dataKey="quantidade" fill="#F59E0B" name="Vendas" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          <div className="mb-6 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <div className="mb-4 flex flex-col gap-2 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <h3 className="text-lg font-semibold text-gray-800">
                  Vendas normais x preco promocional
                </h3>
                <p className="text-sm text-gray-500">
                  Itens vendidos pelo preco promocional ativo no ERP, ecommerce ou app.
                </p>
              </div>
              <div className="rounded-full bg-cyan-50 px-3 py-1 text-xs font-semibold text-cyan-700">
                {analisePromocoes.percentualPromocao}% das vendas com promocao
              </div>
            </div>

            <div className="grid gap-3 md:grid-cols-4">
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <p className="text-xs font-semibold uppercase text-slate-500">
                  Vendas normais
                </p>
                <p className="mt-1 text-2xl font-bold text-slate-900">
                  {analisePromocoes.vendasNormais}
                </p>
                <p className="text-xs text-slate-500">
                  {formatarMoeda(analisePromocoes.valorVendasNormais)}
                </p>
              </div>
              <div className="rounded-lg border border-cyan-200 bg-cyan-50 p-3">
                <p className="text-xs font-semibold uppercase text-cyan-700">
                  Com preco promocional
                </p>
                <p className="mt-1 text-2xl font-bold text-cyan-800">
                  {analisePromocoes.vendasPromocao}
                </p>
                <p className="text-xs text-cyan-700">
                  {formatarMoeda(analisePromocoes.valorVendasPromocao)}
                </p>
              </div>
              <div className="rounded-lg border border-blue-200 bg-blue-50 p-3">
                <p className="text-xs font-semibold uppercase text-blue-700">
                  Itens promocionais
                </p>
                <p className="mt-1 text-2xl font-bold text-blue-800">
                  {formatarMoeda(analisePromocoes.valorItensPromocionais)}
                </p>
                <p className="text-xs text-blue-700">
                  Valor dos itens identificados
                </p>
              </div>
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
                <p className="text-xs font-semibold uppercase text-amber-700">
                  Economia promocional
                </p>
                <p className="mt-1 text-2xl font-bold text-amber-800">
                  {formatarMoeda(analisePromocoes.descontoPromocional)}
                </p>
                <p className="text-xs text-amber-700">
                  Soma estimada nos itens marcados
                </p>
              </div>
            </div>

            <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
              <div className="h-[260px] rounded-lg border border-slate-100 p-3">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={analisePromocoes.comparativo}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="tipo" />
                    <YAxis tickFormatter={(value) => `R$ ${(value / 1000).toFixed(0)}k`} />
                    <Tooltip formatter={(value, name, props) => {
                      const isQuantidade = props?.dataKey === "quantidade" || name === "Vendas";
                      return [
                        isQuantidade ? value : formatarMoeda(value),
                        isQuantidade ? "Vendas" : "Valor",
                      ];
                    }} />
                    <Legend />
                    <Bar dataKey="valor" name="Valor" fill="#06B6D4" radius={[6, 6, 0, 0]} />
                    <Bar dataKey="quantidade" name="Vendas" fill="#64748B" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="overflow-x-auto rounded-lg border border-slate-100">
                <table className="w-full text-sm">
                  <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                    <tr>
                      <th className="px-3 py-2 text-left">Produto</th>
                      <th className="px-3 py-2 text-right">Qtd</th>
                      <th className="px-3 py-2 text-right">Valor</th>
                      <th className="px-3 py-2 text-right">Desconto</th>
                      <th className="px-3 py-2 text-left">Origem</th>
                    </tr>
                  </thead>
                  <tbody>
                    {analisePromocoes.topProdutos.length === 0 ? (
                      <tr>
                        <td colSpan="5" className="px-3 py-6 text-center text-sm text-slate-500">
                          Nenhum item promocional identificado no periodo.
                        </td>
                      </tr>
                    ) : (
                      analisePromocoes.topProdutos.map((produto) => (
                        <tr key={produto.produto_nome} className="border-t border-slate-100">
                          <td className="px-3 py-2 font-medium text-slate-800">
                            {produto.produto_nome}
                          </td>
                          <td className="px-3 py-2 text-right">
                            {produto.quantidade}
                          </td>
                          <td className="px-3 py-2 text-right font-semibold">
                            {formatarMoeda(produto.valor)}
                          </td>
                          <td className="px-3 py-2 text-right text-amber-700">
                            {formatarMoeda(produto.desconto)}
                          </td>
                          <td className="px-3 py-2 text-slate-600">
                            {produto.origens.join(", ") || "-"}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* Vendas por Data */}
          <div className="bg-white rounded-lg shadow mb-6">
            <div className="bg-gray-600 text-white px-4 py-2 rounded-t-lg font-semibold">
              Vendas por data
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-100">
                  <tr>
                    <th className="px-4 py-2 text-left">Data</th>
                    <th className="px-4 py-2 text-left">Dia</th>
                    <th className="px-4 py-2 text-right">Qtd</th>
                    <th className="px-4 py-2 text-right">Tkt. Médio</th>
                    <th className="px-4 py-2 text-right">Vl. bruto</th>
                    <th className="px-4 py-2 text-right">Taxa entrega</th>
                    <th className="px-4 py-2 text-right">Desconto</th>
                    <th className="px-4 py-2 text-right">(%)</th>
                    <th className="px-4 py-2 text-right">Vl. líquido</th>
                    <th className="px-4 py-2 text-right">Vl. recebido</th>
                    <th className="px-4 py-2 text-right">Saldo aberto</th>
                  </tr>
                </thead>
                <tbody>
                  {vendasPorDataCalendario.map((item, idx) => (
                    <tr
                      key={`dia-${item.data || idx}`}
                      className={`border-b hover:bg-gray-50 ${
                        item.sem_movimento ? "bg-slate-50/60 text-slate-500" : ""
                      }`}
                    >
                      <td className="px-4 py-2">{formatarData(item.data)}</td>
                      <td className="px-4 py-2">
                        <div className="flex flex-wrap gap-1">
                          <span
                            className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                              item.feriado_aberto
                                ? "bg-emerald-100 text-emerald-700"
                                : item.fim_de_semana
                                ? "bg-purple-100 text-purple-700"
                                : item.feriado_nome
                                  ? "bg-amber-100 text-amber-700"
                                  : "bg-emerald-100 text-emerald-700"
                            }`}
                          >
                            {item.feriado_nome || item.dia_semana}
                          </span>
                          {item.sem_movimento && item.dia_util && (
                            <span className="rounded-full bg-rose-100 px-2 py-0.5 text-xs font-semibold text-rose-700">
                              Sem venda
                            </span>
                          )}
                          {item.feriado_aberto && (
                            <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-700">
                              Aberto
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-2 text-right">
                        {item.quantidade}
                      </td>
                      <td className="px-4 py-2 text-right">
                        {formatarMoeda(item.ticket_medio)}
                      </td>
                      <td className="px-4 py-2 text-right">
                        {formatarMoeda(item.valor_bruto)}
                      </td>
                      <td className="px-4 py-2 text-right">
                        {formatarMoeda(item.taxa_entrega)}
                      </td>
                      <td className="px-4 py-2 text-right">
                        {formatarMoeda(item.desconto)}
                      </td>
                      <td className="px-4 py-2 text-right">
                        {item.percentual_desconto}%
                      </td>
                      <td className="px-4 py-2 text-right">
                        {formatarMoeda(item.valor_liquido)}
                      </td>
                      <td className="px-4 py-2 text-right">
                        {formatarMoeda(item.valor_recebido)}
                      </td>
                      <td className="px-4 py-2 text-right">
                        {formatarMoeda(item.saldo_aberto)}
                      </td>
                    </tr>
                  ))}
                  {/* TOTAL */}
                  {vendasPorDataCalendario.length > 0 &&
                    (() => {
                      const totalQtd = vendasPorDataCalendario.reduce(
                        (sum, item) => sum + item.quantidade,
                        0,
                      );
                      const totalBruto = vendasPorDataCalendario.reduce(
                        (sum, item) => sum + item.valor_bruto,
                        0,
                      );
                      const totalDesconto = vendasPorDataCalendario.reduce(
                        (sum, item) => sum + item.desconto,
                        0,
                      );
                      const ticketMedio =
                        totalQtd > 0 ? totalBruto / totalQtd : 0;
                      const percentualDesconto =
                        totalBruto > 0
                          ? ((totalDesconto / totalBruto) * 100).toFixed(1)
                          : 0;

                      return (
                        <tr
                          style={{
                            backgroundColor: "#E5E7EB",
                            color: "#1F2937",
                            fontWeight: "bold",
                          }}
                        >
                          <td className="px-4 py-3" colSpan="2">TOTAL</td>
                          <td className="px-4 py-3 text-right">{totalQtd}</td>
                          <td className="px-4 py-3 text-right">
                            {formatarMoeda(ticketMedio)}
                          </td>
                          <td className="px-4 py-3 text-right">
                            {formatarMoeda(totalBruto)}
                          </td>
                          <td className="px-4 py-3 text-right">
                            {formatarMoeda(
                              vendasPorDataCalendario.reduce(
                                (sum, item) => sum + item.taxa_entrega,
                                0,
                              ),
                            )}
                          </td>
                          <td className="px-4 py-3 text-right">
                            {formatarMoeda(totalDesconto)}
                          </td>
                          <td className="px-4 py-3 text-right">
                            {percentualDesconto}%
                          </td>
                          <td className="px-4 py-3 text-right">
                            {formatarMoeda(
                              vendasPorDataCalendario.reduce(
                                (sum, item) => sum + item.valor_liquido,
                                0,
                              ),
                            )}
                          </td>
                          <td className="px-4 py-3 text-right">
                            {formatarMoeda(
                              vendasPorDataCalendario.reduce(
                                (sum, item) => sum + item.valor_recebido,
                                0,
                              ),
                            )}
                          </td>
                          <td className="px-4 py-3 text-right">
                            {formatarMoeda(
                              vendasPorDataCalendario.reduce(
                                (sum, item) => sum + item.saldo_aberto,
                                0,
                              ),
                            )}
                          </td>
                        </tr>
                      );
                    })()}
                </tbody>
              </table>
            </div>
          </div>

          {/* Grid com outras tabelas */}
          <div className="grid grid-cols-2 gap-6">
            {/* Formas de Recebimento */}
            <div className="bg-white rounded-lg shadow">
              <div className="bg-gray-600 text-white px-4 py-2 rounded-t-lg font-semibold">
                Formas de recebimento
              </div>
              <table className="w-full">
                <thead className="bg-gray-100">
                  <tr>
                    <th className="px-4 py-2 text-left">Forma</th>
                    <th className="px-4 py-2 text-right">Valor pago</th>
                  </tr>
                </thead>
                <tbody>
                  {formasRecebimentoConsolidadas.map((item, idx) => (
                    <tr key={`forma-row-${item.forma_pagamento || idx}`} className="border-b">
                      <td className="px-4 py-2">{item.forma_pagamento}</td>
                      <td className="px-4 py-2 text-right">
                        {formatarMoeda(item.valor_total)}
                      </td>
                    </tr>
                  ))}
                  {formasRecebimentoConsolidadas.length > 0 && (
                    <tr
                      style={{
                        backgroundColor: "#E5E7EB",
                        color: "#1F2937",
                        fontWeight: "bold",
                      }}
                    >
                      <td className="px-4 py-3">TOTAL</td>
                      <td className="px-4 py-3 text-right">
                        {formatarMoeda(
                          formasRecebimentoConsolidadas.reduce(
                            (sum, item) => sum + item.valor_total,
                            0,
                          ),
                        )}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Funcionário */}
            <div className="bg-white rounded-lg shadow">
              <div className="bg-gray-600 text-white px-4 py-2 rounded-t-lg font-semibold">
                Funcionário
              </div>
              <table className="w-full">
                <thead className="bg-gray-100">
                  <tr>
                    <th className="px-4 py-2 text-left">Nome</th>
                    <th className="px-4 py-2 text-right">Qtd</th>
                    <th className="px-4 py-2 text-right">Vl. bruto</th>
                    <th className="px-4 py-2 text-right">Desconto</th>
                    <th className="px-4 py-2 text-right">Vl. líquido</th>
                  </tr>
                </thead>
                <tbody>
                  {vendasPorFuncionarioFiltradas.map((item, idx) => (
                    <tr key={`func-row-${item.funcionario || idx}`} className="border-b">
                      <td className="px-4 py-2">{item.funcionario}</td>
                      <td className="px-4 py-2 text-right">
                        {item.quantidade}
                      </td>
                      <td className="px-4 py-2 text-right">
                        {formatarMoeda(item.valor_bruto)}
                      </td>
                      <td className="px-4 py-2 text-right">
                        {formatarMoeda(item.desconto)}
                      </td>
                      <td className="px-4 py-2 text-right">
                        {formatarMoeda(item.valor_liquido)}
                      </td>
                    </tr>
                  ))}
                  {vendasPorFuncionarioFiltradas.length > 0 && (
                    <tr
                      style={{
                        backgroundColor: "#E5E7EB",
                        color: "#1F2937",
                        fontWeight: "bold",
                      }}
                    >
                      <td className="px-4 py-3">TOTAL</td>
                      <td className="px-4 py-3 text-right">
                        {vendasPorFuncionarioFiltradas.reduce(
                          (sum, item) => sum + item.quantidade,
                          0,
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {formatarMoeda(
                          vendasPorFuncionarioFiltradas.reduce(
                            (sum, item) => sum + item.valor_bruto,
                            0,
                          ),
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {formatarMoeda(
                          vendasPorFuncionarioFiltradas.reduce(
                            (sum, item) => sum + item.desconto,
                            0,
                          ),
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {formatarMoeda(
                          vendasPorFuncionarioFiltradas.reduce(
                            (sum, item) => sum + item.valor_liquido,
                            0,
                          ),
                        )}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Tipo */}
            <div className="bg-white rounded-lg shadow">
              <div className="bg-gray-600 text-white px-4 py-2 rounded-t-lg font-semibold">
                Tipo
              </div>
              <table className="w-full">
                <thead className="bg-gray-100">
                  <tr>
                    <th className="px-4 py-2 text-left">Tipo</th>
                    <th className="px-4 py-2 text-right">Qtd</th>
                    <th className="px-4 py-2 text-right">Vl. bruto</th>
                    <th className="px-4 py-2 text-right">Desconto</th>
                    <th className="px-4 py-2 text-right">Vl. líquido</th>
                  </tr>
                </thead>
                <tbody>
                  {vendasPorTipo.map((item, idx) => (
                    <tr key={`tipo-row-${item.tipo || idx}`} className="border-b">
                      <td className="px-4 py-2">{item.tipo}</td>
                      <td className="px-4 py-2 text-right">
                        {item.quantidade}
                      </td>
                      <td className="px-4 py-2 text-right">
                        {formatarMoeda(item.valor_bruto)}
                      </td>
                      <td className="px-4 py-2 text-right">
                        {formatarMoeda(item.desconto)}
                      </td>
                      <td className="px-4 py-2 text-right">
                        {formatarMoeda(item.valor_liquido)}
                      </td>
                    </tr>
                  ))}
                  {vendasPorTipo.length > 0 && (
                    <tr
                      style={{
                        backgroundColor: "#E5E7EB",
                        color: "#1F2937",
                        fontWeight: "bold",
                      }}
                    >
                      <td className="px-4 py-3">TOTAL</td>
                      <td className="px-4 py-3 text-right">
                        {vendasPorTipo.reduce(
                          (sum, item) => sum + item.quantidade,
                          0,
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {formatarMoeda(
                          vendasPorTipo.reduce(
                            (sum, item) => sum + item.valor_bruto,
                            0,
                          ),
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {formatarMoeda(
                          vendasPorTipo.reduce(
                            (sum, item) => sum + item.desconto,
                            0,
                          ),
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {formatarMoeda(
                          vendasPorTipo.reduce(
                            (sum, item) => sum + item.valor_liquido,
                            0,
                          ),
                        )}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Grupo de Produto */}
            <div className="bg-white rounded-lg shadow">
              <div className="bg-gray-600 text-white px-4 py-2 rounded-t-lg font-semibold">
                Grupo de produto
              </div>
              <table className="w-full">
                <thead className="bg-gray-100">
                  <tr>
                    <th className="px-4 py-2 text-left">Nome</th>
                    <th className="px-4 py-2 text-right">Percentual</th>
                    <th className="px-4 py-2 text-right">Vl. bruto</th>
                    <th className="px-4 py-2 text-right">Desconto</th>
                    <th className="px-4 py-2 text-right">Vl. líquido</th>
                  </tr>
                </thead>
                <tbody>
                  {vendasPorGrupo.map((item, idx) => (
                    <tr key={`grupo-row-${item.grupo || idx}`} className="border-b">
                      <td className="px-4 py-2">{item.grupo}</td>
                      <td className="px-4 py-2 text-right">
                        {item.percentual}%
                      </td>
                      <td className="px-4 py-2 text-right">
                        {formatarMoeda(item.valor_bruto)}
                      </td>
                      <td className="px-4 py-2 text-right">
                        {formatarMoeda(item.desconto)}
                      </td>
                      <td className="px-4 py-2 text-right">
                        {formatarMoeda(item.valor_liquido)}
                      </td>
                    </tr>
                  ))}
                  {vendasPorGrupo.length > 0 && (
                    <tr
                      style={{
                        backgroundColor: "#E5E7EB",
                        color: "#1F2937",
                        fontWeight: "bold",
                      }}
                    >
                      <td className="px-4 py-3">TOTAL</td>
                      <td className="px-4 py-3 text-right">-</td>
                      <td className="px-4 py-3 text-right">
                        {formatarMoeda(
                          vendasPorGrupo.reduce(
                            (sum, item) => sum + item.valor_bruto,
                            0,
                          ),
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {formatarMoeda(
                          vendasPorGrupo.reduce(
                            (sum, item) => sum + item.desconto,
                            0,
                          ),
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {formatarMoeda(
                          vendasPorGrupo.reduce(
                            (sum, item) => sum + item.valor_liquido,
                            0,
                          ),
                        )}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {modalRelatorioAberto && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4">
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">
                Relatorio Personalizado - Lista de Vendas
              </h3>
              <button
                onClick={() => setModalRelatorioAberto(false)}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <span className="text-2xl leading-none">×</span>
              </button>
            </div>

            <div className="px-6 py-4 max-h-[60vh] overflow-y-auto space-y-4">
              <div>
                <label
                  htmlFor="ordenacao-relatorio-vendas"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  Ordem
                </label>
                <select
                  id="ordenacao-relatorio-vendas"
                  value={ordenacaoRelatorio}
                  onChange={(e) => setOrdenacaoRelatorio(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                >
                  <option value="data_desc">Data (mais recente primeiro)</option>
                  <option value="data_asc">Data (mais antiga primeiro)</option>
                  <option value="bruta_desc">Venda bruta (maior para menor)</option>
                  <option value="bruta_asc">Venda bruta (menor para maior)</option>
                  <option value="lucro_desc">Lucro (maior para menor)</option>
                  <option value="lucro_asc">Lucro (menor para maior)</option>
                </select>
              </div>

              <div>
                <p className="text-sm font-medium text-gray-700 mb-2">Colunas</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {COLUNAS_RELATORIO_VENDAS.map((coluna) => (
                    <label
                      key={coluna.key}
                      className="flex items-center gap-2 p-2 rounded hover:bg-gray-50"
                    >
                      <input
                        type="checkbox"
                        checked={colunasRelatorio.includes(coluna.key)}
                        onChange={() => toggleColunaRelatorio(coluna.key)}
                        className="w-4 h-4 text-indigo-600 rounded"
                      />
                      <span className="text-sm text-gray-700">{coluna.label}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>

            <div className="px-6 py-4 border-t border-gray-200 flex justify-end gap-3">
              <button
                onClick={() => setModalRelatorioAberto(false)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                onClick={() => {
                  exportarRelatorioListaVendas({ escopo: "filtrado" });
                  setModalRelatorioAberto(false);
                }}
                className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700"
              >
                Gerar relatorio
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Aba Produtos Detalhados */}
      {abaAtiva === "produtos" && (
        <div className="bg-white rounded-lg shadow">
          <div className="bg-gray-600 text-white px-4 py-2 rounded-t-lg font-semibold">
            Produtos/Serviços
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-100">
                <tr>
                  <th className="px-4 py-2 text-left">Produtos/Serviços</th>
                  <th className="px-4 py-2 text-right">Itens</th>
                  <th className="px-4 py-2 text-right">Bruto</th>
                  <th className="px-4 py-2 text-right">Desconto</th>
                  <th className="px-4 py-2 text-right">Líquido</th>
                </tr>
              </thead>
              <tbody>
                {produtosDetalhadosFiltrados.map((categoria, catIdx) => (
                  <React.Fragment key={`cat-group-${catIdx}`}>
                    {/* Linha da Categoria */}
                    <tr
                      key={`cat-${catIdx}`}
                      className="bg-blue-50 font-semibold"
                    >
                      <td className="px-4 py-2">{categoria.categoria}</td>
                      <td className="px-4 py-2 text-right">
                        {categoria.total_quantidade}
                      </td>
                      <td className="px-4 py-2 text-right">
                        {formatarMoeda(categoria.total_bruto)}
                      </td>
                      <td className="px-4 py-2 text-right">
                        {formatarMoeda(categoria.total_desconto)}
                      </td>
                      <td className="px-4 py-2 text-right">
                        {formatarMoeda(categoria.total_liquido)}
                      </td>
                    </tr>

                    {/* Subcategorias */}
                    {categoria.subcategorias &&
                      categoria.subcategorias.map((sub, subIdx) => (
                        <React.Fragment key={`sub-group-${catIdx}-${subIdx}`}>
                          {/* Linha da Subcategoria */}
                          <tr
                            key={`sub-${catIdx}-${subIdx}`}
                            className="bg-gray-50 font-medium"
                          >
                            <td className="px-4 py-2 pl-8">
                              {sub.subcategoria}
                            </td>
                            <td className="px-4 py-2 text-right">
                              {sub.total_quantidade}
                            </td>
                            <td className="px-4 py-2 text-right">
                              {formatarMoeda(sub.total_bruto)}
                            </td>
                            <td className="px-4 py-2 text-right">
                              {formatarMoeda(sub.total_desconto)}
                            </td>
                            <td className="px-4 py-2 text-right">
                              {formatarMoeda(sub.total_liquido)}
                            </td>
                          </tr>

                          {/* Produtos da Subcategoria */}
                          {sub.produtos &&
                            sub.produtos.map((produto, prodIdx) => (
                              <tr
                                key={`prod-${catIdx}-${subIdx}-${prodIdx}`}
                                className="border-b hover:bg-gray-50"
                              >
                                <td className="px-4 py-2 pl-12 text-gray-700">
                                  {produto.produto}
                                </td>
                                <td className="px-4 py-2 text-right text-gray-700">
                                  {produto.quantidade}
                                </td>
                                <td className="px-4 py-2 text-right text-gray-700">
                                  {formatarMoeda(produto.valor_bruto)}
                                </td>
                                <td className="px-4 py-2 text-right text-gray-700">
                                  {formatarMoeda(produto.desconto)}
                                </td>
                                <td className="px-4 py-2 text-right text-gray-700">
                                  {formatarMoeda(produto.valor_liquido)}
                                </td>
                              </tr>
                            ))}
                        </React.Fragment>
                      ))}

                    {/* Produtos sem subcategoria */}
                    {categoria.produtos &&
                      categoria.produtos.map((produto, prodIdx) => (
                        <tr
                          key={`prod-${catIdx}-${prodIdx}`}
                          className="border-b hover:bg-gray-50"
                        >
                          <td className="px-4 py-2 pl-8 text-gray-700">
                            {produto.produto}
                          </td>
                          <td className="px-4 py-2 text-right text-gray-700">
                            {produto.quantidade}
                          </td>
                          <td className="px-4 py-2 text-right text-gray-700">
                            {formatarMoeda(produto.valor_bruto)}
                          </td>
                          <td className="px-4 py-2 text-right text-gray-700">
                            {formatarMoeda(produto.desconto)}
                          </td>
                          <td className="px-4 py-2 text-right text-gray-700">
                            {formatarMoeda(produto.valor_liquido)}
                          </td>
                        </tr>
                      ))}
                  </React.Fragment>
                ))}

                {/* TOTAL GERAL */}
                {produtosDetalhados.length > 0 && (
                  <tr
                    style={{
                      backgroundColor: "#E5E7EB",
                      color: "#1F2937",
                      fontWeight: "bold",
                    }}
                  >
                    <td className="px-4 py-3">TOTAL GERAL</td>
                    <td className="px-4 py-3 text-right">
                      {produtosDetalhados.reduce(
                        (sum, cat) => sum + cat.total_quantidade,
                        0,
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {formatarMoeda(
                        produtosDetalhados.reduce(
                          (sum, cat) => sum + cat.total_bruto,
                          0,
                        ),
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {formatarMoeda(
                        produtosDetalhados.reduce(
                          (sum, cat) => sum + cat.total_desconto,
                          0,
                        ),
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {formatarMoeda(
                        produtosDetalhados.reduce(
                          (sum, cat) => sum + cat.total_liquido,
                          0,
                        ),
                      )}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Aba Lista de Vendas */}
      {abaAtiva === "lista" && (
        <div className="bg-white rounded-lg shadow">
          <div className="bg-gray-600 text-white px-4 py-2 rounded-t-lg font-semibold">
            Lista de Vendas com Análise de Rentabilidade
          </div>
          <div className="flex flex-col gap-3 border-b border-gray-100 px-4 py-3 md:flex-row md:items-center md:justify-between">
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={limparFiltroStatusLista}
                className={`rounded-full px-3 py-1 text-sm font-semibold transition ${
                  filtroStatusLista === ""
                    ? "bg-blue-600 text-white"
                    : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                }`}
              >
                Todas
              </button>
              <button
                type="button"
                onClick={() => setFiltroStatusLista("em_aberto")}
                className={`rounded-full px-3 py-1 text-sm font-semibold transition ${
                  filtroStatusLista === "em_aberto"
                    ? "bg-red-600 text-white"
                    : "bg-red-50 text-red-700 hover:bg-red-100"
                }`}
              >
                Em aberto
              </button>
              <label
                className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1 text-sm font-semibold text-slate-700 shadow-sm"
                title="Marcado: mostra imposto estimado em todas as vendas. Desmarcado: mostra imposto somente em vendas com NF/NFC-e vinculada."
              >
                <input
                  type="checkbox"
                  checked={mostrarImpostoTodasVendas}
                  onChange={(event) => setMostrarImpostoTodasVendas(event.target.checked)}
                  className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                />
                Mostrar TUDO com imposto
              </label>
            </div>
            <div className="text-sm text-slate-500">
              Mostrando {listaVendasFiltrada.length} de {listaVendasVisiveis.length} venda(s)
            </div>
          </div>
          <div className="grid gap-2 border-b border-gray-100 bg-slate-50 px-4 py-3 sm:grid-cols-2 md:grid-cols-4 xl:grid-cols-8">
            {cardsTotalizadoresLista.map((card) => (
              <div
                key={card.label}
                className="rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-sm"
              >
                <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                  {card.label}
                </p>
                <p className="mt-1 text-sm font-bold text-slate-900">
                  {card.value}
                </p>
              </div>
            ))}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-100">
                <tr>
                  <th className="px-1 py-2 text-left w-8"></th>
                  <th className="px-1 py-2 text-left">Data</th>
                  <th className="px-1 py-2 text-left">Código</th>
                  <th className="px-1 py-2 text-left">Cliente</th>
                  <th className="px-1 py-2 text-right">Venda Bruta</th>
                  <th className="px-1 py-2 text-right">Tx Loja</th>
                  <th className="px-1 py-2 text-right">Desconto</th>
                  <th className="px-1 py-2 text-right">Tx. Entrega</th>
                  <th className="px-1 py-2 text-right">Tx. Operac.</th>
                  <th className="px-1 py-2 text-right">Tx. Cartão</th>
                  <th className="px-1 py-2 text-right">Comissão</th>
                  <th className="px-1 py-2 text-right">Imposto</th>
                  <th
                    className="px-1 py-2 text-right"
                    title="Cashback / cupons resgatados nesta venda"
                  >
                    Custo Camp.
                  </th>
                  <th className="px-1 py-2 text-right">Líquida</th>
                  <th className="px-1 py-2 text-right">Custo</th>
                  <th className="px-1 py-2 text-right">Lucro</th>
                  <th className="px-1 py-2 text-right">MG Venda</th>
                  <th className="px-1 py-2 text-right">MG Custo</th>
                  <th className="px-1 py-2 text-center">Status</th>
                </tr>
              </thead>
              <tbody>
                {listaVendasFiltrada.map((venda) => (
                  <React.Fragment key={venda.id}>
                    <tr
                      className="border-b hover:bg-gray-50 cursor-pointer"
                      onClick={() => toggleVendaExpandida(venda.id)}
                    >
                      <td className="px-1 py-2">
                        {vendasExpandidas.has(venda.id) ? (
                          <ChevronDown className="w-4 h-4 text-gray-600" />
                        ) : (
                          <ChevronRight className="w-4 h-4 text-gray-600" />
                        )}
                      </td>
                      <td className="px-1 py-2 whitespace-nowrap">
                        {formatarData(venda.data_venda)}
                      </td>
                      <td className="px-1 py-2 whitespace-nowrap">
                        <div className="inline-flex items-center gap-1.5">
                          <a
                            href={criarUrlPdvVenda(venda)}
                            target="_blank"
                            rel="noreferrer"
                            onClick={(event) => event.stopPropagation()}
                            className="inline-flex items-center gap-1 font-medium text-blue-700 hover:text-blue-900 hover:underline"
                            title="Abrir venda no PDV em nova aba"
                          >
                            {venda.numero_venda}
                            <ExternalLink className="h-3.5 w-3.5" />
                          </a>
                          <button
                            type="button"
                            onClick={(event) => copiarNumeroVenda(event, venda.numero_venda)}
                            className="inline-flex h-6 w-6 items-center justify-center rounded border border-slate-200 text-slate-500 transition hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700"
                            title="Copiar numero da venda"
                            aria-label={`Copiar numero da venda ${venda.numero_venda}`}
                          >
                            <Copy className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </td>
                      <td className="px-1 py-2">{venda.cliente_nome}</td>
                      <td className="px-1 py-2 text-right font-medium whitespace-nowrap">
                        {formatarMoeda(venda.venda_bruta)}
                      </td>
                      <td
                        className="px-1 py-2 text-right text-green-700 whitespace-nowrap"
                        title="Taxa de entrega total cobrada do cliente"
                      >
                        +{formatarMoeda(venda.taxa_loja || 0)}
                      </td>
                      <td className="px-1 py-2 text-right text-red-600 whitespace-nowrap">
                        -{formatarMoeda(venda.desconto)}
                      </td>
                      <td
                        className="px-1 py-2 text-right text-blue-600 whitespace-nowrap"
                        title="Comissão repassada ao entregador"
                      >
                        -{formatarMoeda(venda.taxa_entrega)}
                      </td>
                      <td
                        className="px-1 py-2 text-right text-orange-500 whitespace-nowrap"
                        title="Custo operacional da entrega (empresa)"
                      >
                        -{formatarMoeda(venda.taxa_operacional || 0)}
                      </td>
                      <td className="px-1 py-2 text-right text-purple-600 whitespace-nowrap">
                        -{formatarMoeda(venda.taxa_cartao)}
                      </td>
                      <td className="px-1 py-2 text-right text-blue-600 whitespace-nowrap">
                        -{formatarMoeda(venda.comissao)}
                      </td>
                      <td
                        className="px-1 py-2 text-right text-pink-600 whitespace-nowrap"
                        title={
                          venda.imposto_aplicado
                            ? "Impostos sobre faturamento"
                            : "Imposto oculto porque a venda nao tem NF/NFC-e emitida"
                        }
                      >
                        -{formatarMoeda(venda.imposto || 0)}
                      </td>
                      <td
                        className="px-1 py-2 text-right text-teal-600 whitespace-nowrap"
                        title="Custo com campanhas (cashback/cupom resgatado)"
                      >
                        {venda.custo_campanha > 0
                          ? `-${formatarMoeda(venda.custo_campanha)}`
                          : "—"}
                      </td>
                      <td className="px-1 py-2 text-right font-medium whitespace-nowrap">
                        {formatarMoeda(venda.venda_liquida)}
                      </td>
                      <td className="px-1 py-2 text-right text-orange-600 whitespace-nowrap">
                        -{formatarMoeda(venda.custo_produtos)}
                      </td>
                      <td
                        className={`px-1 py-2 text-right font-bold whitespace-nowrap ${venda.lucro >= 0 ? "text-green-600" : "text-red-600"}`}
                      >
                        {formatarMoeda(venda.lucro)}
                      </td>
                      <td className="px-1 py-2 text-right whitespace-nowrap">
                        {venda.margem_sobre_venda}%
                      </td>
                      <td className="px-1 py-2 text-right whitespace-nowrap">
                        {venda.margem_sobre_custo}%
                      </td>
                      <td className="px-2 py-2 text-center">
                        <span
                          className={`px-2 py-1 rounded text-xs ${getStatusVendaMeta(venda.status).className}`}
                        >
                          {getStatusVendaMeta(venda.status).label}
                        </span>
                      </td>
                    </tr>

                    {/* Linha expandida com detalhes dos produtos */}
                    {vendasExpandidas.has(venda.id) &&
                      venda.itens &&
                      venda.itens.length > 0 && (
                        <tr key={`${venda.id}-detalhes`} className="bg-blue-50">
                          <td colSpan="19" className="px-4 py-3">
                            <div className="pl-8">
                              <div className="font-semibold text-gray-700 mb-2">
                                Produtos desta venda:
                              </div>
                              <table className="w-full text-xs">
                                <thead className="bg-blue-100">
                                  <tr>
                                    <th className="px-1 py-1 text-left">
                                      Produto
                                    </th>
                                    <th className="px-1 py-1 text-center">
                                      Qtd
                                    </th>
                                    <th className="px-1 py-1 text-right">
                                      Preço Unit.
                                    </th>
                                    <th className="px-1 py-1 text-right">
                                      Venda Bruta
                                    </th>
                                    <th className="px-1 py-1 text-right">
                                      Tx Loja
                                    </th>
                                    <th className="px-1 py-1 text-right">
                                      Desconto
                                    </th>
                                    <th className="px-1 py-1 text-right">
                                      Tx. Entr.
                                    </th>
                                    <th className="px-1 py-1 text-right">
                                      Tx. Oper.
                                    </th>
                                    <th className="px-1 py-1 text-right">
                                      Tx. Cartão
                                    </th>
                                    <th className="px-1 py-1 text-right">
                                      Comissão
                                    </th>
                                    <th className="px-1 py-1 text-right">
                                      Imposto
                                    </th>
                                    <th
                                      className="px-1 py-1 text-right"
                                      title="Cashback/cupom rateado neste item"
                                    >
                                      Campanha
                                    </th>
                                    <th className="px-1 py-1 text-right">
                                      Líquido
                                    </th>
                                    <th className="px-1 py-1 text-right">
                                      Custo Unit.
                                    </th>
                                    <th className="px-1 py-1 text-right">
                                      Custo Total
                                    </th>
                                    <th className="px-1 py-1 text-right">
                                      Lucro
                                    </th>
                                    <th className="px-1 py-1 text-right">
                                      MG Venda
                                    </th>
                                    <th className="px-1 py-1 text-right">
                                      MG Custo
                                    </th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {venda.itens.map((item, idx) => (
                                    <tr
                                      key={`${venda.id}-item-${item.produto_id || item.produto_nome || idx}`}
                                      className="border-b border-blue-200 hover:bg-blue-100"
                                    >
                                      <td className="px-1 py-1">
                                        <div className="flex flex-wrap items-center gap-1">
                                          <span>{item.produto_nome}</span>
                                          {item.em_promocao && (
                                            <span
                                              className="rounded-full bg-cyan-100 px-2 py-0.5 text-[10px] font-bold uppercase text-cyan-700"
                                              title={item.promocao_origem || "Item vendido por preco promocional ativo"}
                                            >
                                              Promo
                                            </span>
                                          )}
                                        </div>
                                      </td>
                                      <td className="px-1 py-1 text-center">
                                        {item.quantidade}
                                      </td>
                                      <td className="px-1 py-1 text-right whitespace-nowrap">
                                        {formatarMoeda(item.preco_unitario)}
                                      </td>
                                      <td className="px-1 py-1 text-right font-medium whitespace-nowrap">
                                        {formatarMoeda(item.venda_bruta)}
                                      </td>
                                      <td className="px-1 py-1 text-right text-green-700 whitespace-nowrap">
                                        +{formatarMoeda(item.taxa_loja || 0)}
                                      </td>
                                      <td className="px-1 py-1 text-right text-red-600 whitespace-nowrap">
                                        -{formatarMoeda(item.desconto)}
                                      </td>
                                      <td className="px-1 py-1 text-right text-blue-600 whitespace-nowrap">
                                        -{formatarMoeda(item.taxa_entrega)}
                                      </td>
                                      <td className="px-1 py-1 text-right text-orange-500 whitespace-nowrap">
                                        -
                                        {formatarMoeda(
                                          item.taxa_operacional || 0,
                                        )}
                                      </td>
                                      <td className="px-1 py-1 text-right text-purple-600 whitespace-nowrap">
                                        -{formatarMoeda(item.taxa_cartao)}
                                      </td>
                                      <td className="px-1 py-1 text-right text-blue-600 whitespace-nowrap">
                                        -{formatarMoeda(item.comissao)}
                                      </td>
                                      <td
                                        className="px-1 py-1 text-right text-pink-600 whitespace-nowrap"
                                        title={
                                          venda.imposto_aplicado
                                            ? "Impostos rateados neste item"
                                            : "Imposto oculto porque a venda nao tem NF/NFC-e emitida"
                                        }
                                      >
                                        -{formatarMoeda(item.imposto || 0)}
                                      </td>
                                      <td className="px-1 py-1 text-right text-teal-600 whitespace-nowrap">
                                        {(item.campanha || 0) > 0
                                          ? `-${formatarMoeda(item.campanha)}`
                                          : "—"}
                                      </td>
                                      <td className="px-1 py-1 text-right font-medium whitespace-nowrap">
                                        {formatarMoeda(item.valor_liquido)}
                                      </td>
                                      <td className="px-1 py-1 text-right text-orange-600 whitespace-nowrap">
                                        {formatarMoeda(item.custo_unitario)}
                                      </td>
                                      <td className="px-1 py-1 text-right text-orange-600 font-medium whitespace-nowrap">
                                        -{formatarMoeda(item.custo_total)}
                                      </td>
                                      <td
                                        className={`px-1 py-1 text-right font-bold whitespace-nowrap ${item.lucro >= 0 ? "text-green-600" : "text-red-600"} cursor-help`}
                                        title={`Lucro unitário: ${formatarMoeda(item.lucro_unitario)}`}
                                      >
                                        {formatarMoeda(item.lucro)}
                                      </td>
                                      <td
                                        className="px-1 py-1 text-right whitespace-nowrap cursor-help"
                                        title={`Margem: ${item.margem_sobre_venda}%`}
                                      >
                                        {item.margem_sobre_venda}%
                                      </td>
                                      <td
                                        className="px-1 py-1 text-right whitespace-nowrap cursor-help"
                                        title={`Markup: ${item.margem_sobre_custo}%`}
                                      >
                                        {item.margem_sobre_custo}%
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          </td>
                        </tr>
                      )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Aba de Comparação */}
      {abaAtiva === "comparacao" && (
        <div>
          {/* Filtro de Tipo de Comparação */}
          <div className="bg-white rounded-lg shadow p-4 mb-6">
            <div className="flex items-center gap-4">
              <label
                htmlFor="tipo-comparacao-vendas"
                className="text-sm font-medium text-gray-700"
              >
                Tipo de Análise:
              </label>
              <select
                id="tipo-comparacao-vendas"
                value={tipoComparacao}
                onChange={(e) => setTipoComparacao(e.target.value)}
                className="border rounded px-4 py-2 text-sm bg-blue-50 font-medium min-w-[250px]"
              >
                <option value="financeiro">📊 Comparação Financeira</option>
                <option value="formas_pagamento">
                  💳 Por Forma de Pagamento
                </option>
                <option value="produtos">📦 Por Grupo de Produtos</option>
                <option value="funcionarios">👥 Por Funcionário</option>
              </select>

              <div className="ml-auto text-sm text-gray-600">
                <span className="font-medium">Período Atual:</span>{" "}
                {formatarData(dataInicio)} - {formatarData(dataFim)}
              </div>
            </div>
          </div>

          {/* Cards de Comparação - 3 Colunas */}
          {tipoComparacao === "financeiro" && (
            <>
              <div className="grid grid-cols-3 gap-6 mb-6">
                {/* Card 1 - Período Anterior */}
                <div className="bg-white rounded-lg shadow-lg border-2 border-gray-300">
                  <div className="bg-gray-500 text-white px-4 py-3 rounded-t-lg">
                    <h3 className="font-bold text-lg">📅 Período Anterior</h3>
                    <p className="text-xs opacity-90 mt-1">
                      {getTextoComparacao()}
                    </p>
                  </div>
                  <div className="p-4 space-y-3">
                    <div className="border-b pb-2">
                      <div className="text-xs text-gray-600">
                        Quantidade de Vendas
                      </div>
                      <div className="text-2xl font-bold text-gray-700">
                        {resumoComparacao.quantidade_vendas || 0}
                      </div>
                    </div>
                    <div className="border-b pb-2">
                      <div className="text-xs text-gray-600">Valor Bruto</div>
                      <div className="text-xl font-bold text-gray-700">
                        {formatarMoeda(resumoComparacao.venda_bruta)}
                      </div>
                    </div>
                    <div className="border-b pb-2">
                      <div className="text-xs text-gray-600">Valor Líquido</div>
                      <div className="text-xl font-bold text-blue-600">
                        {formatarMoeda(resumoComparacao.venda_liquida)}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-gray-600">
                        Valor Recebido
                      </div>
                      <div className="text-xl font-bold text-green-600">
                        {formatarMoeda(
                          resumoComparacao.venda_liquida -
                            resumoComparacao.em_aberto || 0,
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Card 2 - Período Atual */}
                <div className="bg-white rounded-lg shadow-lg border-2 border-blue-500">
                  <div className="bg-blue-600 text-white px-4 py-3 rounded-t-lg">
                    <h3 className="font-bold text-lg">📅 Período Atual</h3>
                    <p className="text-xs opacity-90 mt-1">
                      {formatarData(dataInicio)} - {formatarData(dataFim)}
                    </p>
                  </div>
                  <div className="p-4 space-y-3">
                    <div className="border-b pb-2">
                      <div className="text-xs text-gray-600">
                        Quantidade de Vendas
                      </div>
                      <div className="text-2xl font-bold text-gray-700">
                        {resumo.quantidade_vendas || 0}
                      </div>
                    </div>
                    <div className="border-b pb-2">
                      <div className="text-xs text-gray-600">Valor Bruto</div>
                      <div className="text-xl font-bold text-gray-700">
                        {formatarMoeda(resumo.venda_bruta)}
                      </div>
                    </div>
                    <div className="border-b pb-2">
                      <div className="text-xs text-gray-600">Valor Líquido</div>
                      <div className="text-xl font-bold text-blue-600">
                        {formatarMoeda(resumo.venda_liquida)}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-gray-600">
                        Valor Recebido
                      </div>
                      <div className="text-xl font-bold text-green-600">
                        {formatarMoeda(
                          resumo.venda_liquida - resumo.em_aberto || 0,
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Card 3 - Diferença/Variação */}
                <div className="bg-white rounded-lg shadow-lg border-2 border-green-500">
                  <div className="bg-green-600 text-white px-4 py-3 rounded-t-lg">
                    <h3 className="font-bold text-lg">📈 Diferença</h3>
                    <p className="text-xs opacity-90 mt-1">
                      Variação vs período anterior
                    </p>
                  </div>
                  <div className="p-4 space-y-3">
                    {(() => {
                      const varQtd = calcularVariacao(
                        resumo.quantidade_vendas,
                        resumoComparacao.quantidade_vendas,
                      );
                      const varBruto = calcularVariacao(
                        resumo.venda_bruta,
                        resumoComparacao.venda_bruta,
                      );
                      const varLiquido = calcularVariacao(
                        resumo.venda_liquida,
                        resumoComparacao.venda_liquida,
                      );
                      const valorRecebidoAtual =
                        resumo.venda_liquida - resumo.em_aberto;
                      const valorRecebidoAnt =
                        resumoComparacao.venda_liquida -
                        resumoComparacao.em_aberto;
                      const varRecebido = calcularVariacao(
                        valorRecebidoAtual,
                        valorRecebidoAnt,
                      );

                      return (
                        <>
                          <div className="border-b pb-2">
                            <div className="text-xs text-gray-600">
                              Qtd de Vendas
                            </div>
                            <div
                              className={`text-2xl font-bold flex items-center gap-2 ${varQtd.percentual >= 0 ? "text-green-600" : "text-red-600"}`}
                            >
                              {varQtd.percentual >= 0 ? (
                                <ArrowUp className="w-6 h-6" />
                              ) : (
                                <ArrowDown className="w-6 h-6" />
                              )}
                              {Math.abs(varQtd.percentual)}%
                            </div>
                            <div className="text-xs text-gray-500 mt-1">
                              {varQtd.valor >= 0 ? "+" : ""}
                              {varQtd.valor.toFixed(0)} vendas
                            </div>
                          </div>
                          <div className="border-b pb-2">
                            <div className="text-xs text-gray-600">
                              Valor Bruto
                            </div>
                            <div
                              className={`text-xl font-bold flex items-center gap-2 ${varBruto.percentual >= 0 ? "text-green-600" : "text-red-600"}`}
                            >
                              {varBruto.percentual >= 0 ? (
                                <ArrowUp className="w-5 h-5" />
                              ) : (
                                <ArrowDown className="w-5 h-5" />
                              )}
                              {Math.abs(varBruto.percentual)}%
                            </div>
                            <div className="text-xs text-gray-500 mt-1">
                              {formatarMoeda(varBruto.valor)}
                            </div>
                          </div>
                          <div className="border-b pb-2">
                            <div className="text-xs text-gray-600">
                              Valor Líquido
                            </div>
                            <div
                              className={`text-xl font-bold flex items-center gap-2 ${varLiquido.percentual >= 0 ? "text-green-600" : "text-red-600"}`}
                            >
                              {varLiquido.percentual >= 0 ? (
                                <ArrowUp className="w-5 h-5" />
                              ) : (
                                <ArrowDown className="w-5 h-5" />
                              )}
                              {Math.abs(varLiquido.percentual)}%
                            </div>
                            <div className="text-xs text-gray-500 mt-1">
                              {formatarMoeda(varLiquido.valor)}
                            </div>
                          </div>
                          <div>
                            <div className="text-xs text-gray-600">
                              Valor Recebido
                            </div>
                            <div
                              className={`text-xl font-bold flex items-center gap-2 ${varRecebido.percentual >= 0 ? "text-green-600" : "text-red-600"}`}
                            >
                              {varRecebido.percentual >= 0 ? (
                                <ArrowUp className="w-5 h-5" />
                              ) : (
                                <ArrowDown className="w-5 h-5" />
                              )}
                              {Math.abs(varRecebido.percentual)}%
                            </div>
                            <div className="text-xs text-gray-500 mt-1">
                              {formatarMoeda(varRecebido.valor)}
                            </div>
                          </div>
                        </>
                      );
                    })()}
                  </div>
                </div>
              </div>

              {/* Gráfico de Barras Comparativo */}
              <div className="bg-white rounded-lg shadow p-6 mb-6">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">
                  Comparação Visual
                </h3>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart
                    data={[
                      {
                        nome: "Qtd Vendas",
                        Anterior: resumoComparacao.quantidade_vendas || 0,
                        Atual: resumo.quantidade_vendas || 0,
                      },
                      {
                        nome: "Vl. Bruto (mil)",
                        Anterior: (resumoComparacao.venda_bruta || 0) / 1000,
                        Atual: (resumo.venda_bruta || 0) / 1000,
                      },
                      {
                        nome: "Vl. Líquido (mil)",
                        Anterior: (resumoComparacao.venda_liquida || 0) / 1000,
                        Atual: (resumo.venda_liquida || 0) / 1000,
                      },
                      {
                        nome: "Vl. Recebido (mil)",
                        Anterior:
                          (resumoComparacao.venda_liquida -
                            resumoComparacao.em_aberto || 0) / 1000,
                        Atual:
                          (resumo.venda_liquida - resumo.em_aberto || 0) / 1000,
                      },
                    ]}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="nome" />
                    <YAxis />
                    <Tooltip
                      formatter={(value, name) => [
                        name.includes("mil")
                          ? `R$ ${value.toFixed(1)}k`
                          : value.toFixed(0),
                        name,
                      ]}
                    />
                    <Legend />
                    <Bar
                      dataKey="Anterior"
                      fill="#9CA3AF"
                      name="Período Anterior"
                    />
                    <Bar dataKey="Atual" fill="#3B82F6" name="Período Atual" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </>
          )}

          {/* Comparação por Forma de Pagamento */}
          {tipoComparacao === "formas_pagamento" && (
            <>
              <div className="bg-white rounded-lg shadow p-6 mb-6">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">
                  Comparação por Forma de Pagamento
                </h3>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-100">
                      <tr>
                        <th className="px-4 py-3 text-left">
                          Forma de Pagamento
                        </th>
                        <th className="px-4 py-3 text-right">Anterior</th>
                        <th className="px-4 py-3 text-right">Atual</th>
                        <th className="px-4 py-3 text-right">Diferença</th>
                        <th className="px-4 py-3 text-center">Variação %</th>
                      </tr>
                    </thead>
                    <tbody>
                      {formasRecebimentoConsolidadas.map((formaAtual, idx) => {
                        const formaAnt = formasRecebimentoComparacaoConsolidadas.find(
                          (f) =>
                            f.forma_pagamento === formaAtual.forma_pagamento,
                        ) || { valor_total: 0 };
                        const variacao = calcularVariacao(
                          formaAtual.valor_total,
                          formaAnt.valor_total,
                        );
                        return (
                          <tr key={`comp-forma-${formaAtual.forma_pagamento || idx}`} className="border-b hover:bg-gray-50">
                            <td className="px-4 py-3 font-medium">
                              {formaAtual.forma_pagamento}
                            </td>
                            <td className="px-4 py-3 text-right text-gray-600">
                              {formatarMoeda(formaAnt.valor_total)}
                            </td>
                            <td className="px-4 py-3 text-right font-medium">
                              {formatarMoeda(formaAtual.valor_total)}
                            </td>
                            <td className="px-4 py-3 text-right">
                              {formatarMoeda(variacao.valor)}
                            </td>
                            <td className="px-4 py-3 text-center">
                              <span
                                className={`inline-flex items-center gap-1 px-2 py-1 rounded font-medium ${variacao.percentual >= 0 ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}
                              >
                                {variacao.percentual >= 0 ? (
                                  <ArrowUp className="w-4 h-4" />
                                ) : (
                                  <ArrowDown className="w-4 h-4" />
                                )}
                                {Math.abs(variacao.percentual)}%
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Gráfico de Barras por Forma de Pagamento */}
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">
                  Comparação Visual
                </h3>
                <ResponsiveContainer width="100%" height={350}>
                  <BarChart
                    data={formasRecebimentoConsolidadas.map((f) => ({
                      nome: f.forma_pagamento,
                      Anterior:
                        (formasRecebimentoComparacaoConsolidadas.find(
                          (fa) => fa.forma_pagamento === f.forma_pagamento,
                        )?.valor_total || 0) / 1000,
                      Atual: f.valor_total / 1000,
                    }))}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="nome"
                      angle={-15}
                      textAnchor="end"
                      height={80}
                    />
                    <YAxis
                      tickFormatter={(value) => `R$ ${value.toFixed(0)}k`}
                    />
                    <Tooltip formatter={(value) => `R$ ${value.toFixed(1)}k`} />
                    <Legend />
                    <Bar
                      dataKey="Anterior"
                      fill="#9CA3AF"
                      name="Período Anterior"
                    />
                    <Bar dataKey="Atual" fill="#10B981" name="Período Atual" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </>
          )}

          {/* Comparação por Grupo de Produtos */}
          {tipoComparacao === "produtos" && (
            <>
              <div className="bg-white rounded-lg shadow p-6 mb-6">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">
                  Comparação por Grupo de Produtos
                </h3>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-100">
                      <tr>
                        <th className="px-4 py-3 text-left">Grupo</th>
                        <th className="px-4 py-3 text-right">Anterior</th>
                        <th className="px-4 py-3 text-right">Atual</th>
                        <th className="px-4 py-3 text-right">Diferença</th>
                        <th className="px-4 py-3 text-center">Variação %</th>
                      </tr>
                    </thead>
                    <tbody>
                      {vendasPorGrupo.map((grupoAtual, idx) => {
                        const grupoAnt = vendasPorGrupoComparacao.find(
                          (g) => g.grupo === grupoAtual.grupo,
                        ) || { valor_liquido: 0 };
                        const variacao = calcularVariacao(
                          grupoAtual.valor_liquido,
                          grupoAnt.valor_liquido,
                        );
                        return (
                          <tr key={`comp-grupo-${grupoAtual.grupo || idx}`} className="border-b hover:bg-gray-50">
                            <td className="px-4 py-3 font-medium">
                              {grupoAtual.grupo}
                            </td>
                            <td className="px-4 py-3 text-right text-gray-600">
                              {formatarMoeda(grupoAnt.valor_liquido)}
                            </td>
                            <td className="px-4 py-3 text-right font-medium">
                              {formatarMoeda(grupoAtual.valor_liquido)}
                            </td>
                            <td className="px-4 py-3 text-right">
                              {formatarMoeda(variacao.valor)}
                            </td>
                            <td className="px-4 py-3 text-center">
                              <span
                                className={`inline-flex items-center gap-1 px-2 py-1 rounded font-medium ${variacao.percentual >= 0 ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}
                              >
                                {variacao.percentual >= 0 ? (
                                  <ArrowUp className="w-4 h-4" />
                                ) : (
                                  <ArrowDown className="w-4 h-4" />
                                )}
                                {Math.abs(variacao.percentual)}%
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Gráfico de Pizza Duplo */}
              <div className="grid grid-cols-2 gap-6">
                <div className="bg-white rounded-lg shadow p-6">
                  <h3 className="text-lg font-semibold text-gray-800 mb-4">
                    Período Anterior
                  </h3>
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                      <Pie
                        data={vendasPorGrupoComparacao}
                        dataKey="valor_liquido"
                        nameKey="grupo"
                        cx="50%"
                        cy="50%"
                        outerRadius={80}
                        label={(entry) => {
                          const percent = (
                            (entry.valor_liquido /
                              vendasPorGrupoComparacao.reduce(
                                (sum, item) => sum + item.valor_liquido,
                                0,
                              )) *
                            100
                          ).toFixed(1);
                          return percent > 5 ? `${percent}%` : "";
                        }}
                      >
                        {vendasPorGrupoComparacao.map((entry, index) => (
                          <Cell
                            key={`cell-grupo-ant-${entry.grupo || index}`}
                            fill={CORES_GRAFICOS[index % CORES_GRAFICOS.length]}
                          />
                        ))}
                      </Pie>
                      <Tooltip formatter={(value) => formatarMoeda(value)} />
                      <Legend verticalAlign="bottom" height={36} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>

                <div className="bg-white rounded-lg shadow p-6">
                  <h3 className="text-lg font-semibold text-gray-800 mb-4">
                    Período Atual
                  </h3>
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                      <Pie
                        data={vendasPorGrupo}
                        dataKey="valor_liquido"
                        nameKey="grupo"
                        cx="50%"
                        cy="50%"
                        outerRadius={80}
                        label={(entry) => {
                          const percent = (
                            (entry.valor_liquido /
                              vendasPorGrupo.reduce(
                                (sum, item) => sum + item.valor_liquido,
                                0,
                              )) *
                            100
                          ).toFixed(1);
                          return percent > 5 ? `${percent}%` : "";
                        }}
                      >
                        {vendasPorGrupo.map((entry, index) => (
                          <Cell
                            key={`cell-grupo-atual-${entry.grupo || index}`}
                            fill={CORES_GRAFICOS[index % CORES_GRAFICOS.length]}
                          />
                        ))}
                      </Pie>
                      <Tooltip formatter={(value) => formatarMoeda(value)} />
                      <Legend verticalAlign="bottom" height={36} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </>
          )}

          {/* Comparação por Funcionário */}
          {tipoComparacao === "funcionarios" && (
            <>
              <div className="bg-white rounded-lg shadow p-6 mb-6">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">
                  Comparação por Funcionário
                </h3>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-100">
                      <tr>
                        <th className="px-4 py-3 text-left">Funcionário</th>
                        <th className="px-4 py-3 text-right">Qtd Ant.</th>
                        <th className="px-4 py-3 text-right">Qtd Atual</th>
                        <th className="px-4 py-3 text-right">Vl. Ant.</th>
                        <th className="px-4 py-3 text-right">Vl. Atual</th>
                        <th className="px-4 py-3 text-center">Variação</th>
                      </tr>
                    </thead>
                    <tbody>
                      {vendasPorFuncionario.map((funcAtual, idx) => {
                        const funcAnt = vendasPorFuncionarioComparacao.find(
                          (f) => f.funcionario === funcAtual.funcionario,
                        ) || { quantidade: 0, valor_liquido: 0 };
                        const variacao = calcularVariacao(
                          funcAtual.valor_liquido,
                          funcAnt.valor_liquido,
                        );
                        return (
                          <tr key={`comp-func-${funcAtual.funcionario || idx}`} className="border-b hover:bg-gray-50">
                            <td className="px-4 py-3 font-medium">
                              {funcAtual.funcionario}
                            </td>
                            <td className="px-4 py-3 text-right text-gray-600">
                              {funcAnt.quantidade}
                            </td>
                            <td className="px-4 py-3 text-right font-medium">
                              {funcAtual.quantidade}
                            </td>
                            <td className="px-4 py-3 text-right text-gray-600">
                              {formatarMoeda(funcAnt.valor_liquido)}
                            </td>
                            <td className="px-4 py-3 text-right font-medium">
                              {formatarMoeda(funcAtual.valor_liquido)}
                            </td>
                            <td className="px-4 py-3 text-center">
                              <span
                                className={`inline-flex items-center gap-1 px-2 py-1 rounded font-medium ${variacao.percentual >= 0 ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}
                              >
                                {variacao.percentual >= 0 ? (
                                  <ArrowUp className="w-4 h-4" />
                                ) : (
                                  <ArrowDown className="w-4 h-4" />
                                )}
                                {Math.abs(variacao.percentual)}%
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Gráfico de Barras por Funcionário */}
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">
                  Comparação Visual - Valor Líquido
                </h3>
                <ResponsiveContainer width="100%" height={350}>
                  <BarChart
                    data={vendasPorFuncionario.map((f) => ({
                      nome: f.funcionario,
                      Anterior:
                        (vendasPorFuncionarioComparacao.find(
                          (fa) => fa.funcionario === f.funcionario,
                        )?.valor_liquido || 0) / 1000,
                      Atual: f.valor_liquido / 1000,
                    }))}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="nome"
                      angle={-15}
                      textAnchor="end"
                      height={80}
                    />
                    <YAxis
                      tickFormatter={(value) => `R$ ${value.toFixed(0)}k`}
                    />
                    <Tooltip formatter={(value) => `R$ ${value.toFixed(1)}k`} />
                    <Legend />
                    <Bar
                      dataKey="Anterior"
                      fill="#9CA3AF"
                      name="Período Anterior"
                    />
                    <Bar dataKey="Atual" fill="#8B5CF6" name="Período Atual" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </>
          )}
        </div>
      )}

      {/* Aba de Análise Inteligente */}
      {abaAtiva === "analise" && (
        <div className="space-y-6">
          {/* Indicador de Carregamento */}
          {loading && (
            <div className="flex justify-center items-center h-64">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
          )}

          {/* Conteúdo da Análise */}
          {!loading && (
            <>
              {/* Header Informativo */}
              <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg p-6 text-white">
                <div className="flex items-center gap-3 mb-2">
                  <svg
                    className="w-8 h-8"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                    />
                  </svg>
                  <h2 className="text-2xl font-bold">
                    Análise Inteligente de Produtos
                  </h2>
                </div>
                <p className="text-blue-100">
                  Identifique os produtos mais lucrativos e oportunidades de
                  melhoria no seu mix de produtos
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-white rounded-lg shadow-md p-4 border border-blue-100">
                  <div className="text-xs text-gray-500 mb-1">Previsao proximos 7 dias</div>
                  <div className="text-2xl font-bold text-blue-700">
                    {formatarMoeda(previsaoProximos7Dias)}
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    Baseado na media diaria dos ultimos dias
                  </div>
                </div>
                <div className="bg-white rounded-lg shadow-md p-4 border border-amber-100">
                  <div className="text-xs text-gray-500 mb-1">Alertas automaticos</div>
                  <div className="text-2xl font-bold text-amber-700">
                    {alertasInteligentesVendas.length}
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    Atualizados sempre que o periodo ou filtros mudam
                  </div>
                </div>
                <div className="bg-white rounded-lg shadow-md p-4 border border-emerald-100">
                  <div className="text-xs text-gray-500 mb-1">Ticket medio estimado</div>
                  <div className="text-2xl font-bold text-emerald-700">
                    {formatarMoeda(
                      resumo.quantidade_vendas > 0
                        ? resumo.venda_liquida / resumo.quantidade_vendas
                        : 0,
                    )}
                  </div>
                  <div className="text-xs text-gray-500 mt-1">Periodo atual</div>
                </div>
              </div>

              <div className="bg-white rounded-lg shadow-md p-6">
                <h3 className="text-lg font-semibold mb-4">
                  Alertas Inteligentes Automaticos
                </h3>

                {alertasInteligentesVendas.length === 0 ? (
                  <div className="p-4 rounded-lg bg-green-50 border border-green-200 text-green-700 text-sm">
                    Nenhum alerta critico no momento. O desempenho esta estavel para o periodo analisado.
                  </div>
                ) : (
                  <div className="space-y-3">
                    {alertasInteligentesVendas.map((alerta) => {
                      const classes =
                        alerta.tipo === "critico"
                          ? "bg-red-50 border-red-200"
                          : alerta.tipo === "oportunidade"
                            ? "bg-blue-50 border-blue-200"
                            : "bg-amber-50 border-amber-200";
                      return (
                        <div key={alerta.id} className={`p-4 rounded-lg border ${classes}`}>
                          <div className="font-semibold text-gray-800">{alerta.titulo}</div>
                          <div className="text-sm text-gray-700 mt-1">{alerta.mensagem}</div>
                          <div className="text-sm text-gray-600 mt-2">
                            <strong>Acao sugerida:</strong> {alerta.recomendacao}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Produtos Mais Lucrativos */}
              <div className="bg-white rounded-lg shadow-md p-6">
                <div className="flex items-center gap-2 mb-4">
                  <svg
                    className="w-6 h-6 text-green-600"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  <h3 className="text-lg font-semibold">
                    🏆 Top Produtos por Lucro
                  </h3>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b-2">
                        <th className="text-left py-2 px-2">#</th>
                        <th className="text-left py-2 px-2">Produto</th>
                        <th className="text-left py-2 px-2">Marca</th>
                        <th className="text-right py-2 px-2">Qtd</th>
                        <th className="text-right py-2 px-2">Custo Unit.</th>
                        <th className="text-right py-2 px-2">Preço Venda</th>
                        <th className="text-right py-2 px-2">Margem %</th>
                        <th className="text-right py-2 px-2">Lucro Total</th>
                      </tr>
                    </thead>
                    <tbody>
                      {produtosMaisLucrativos.map((produto, index) => (
                        <tr key={`rank-${produto.nome}-${produto.marca || "sem-marca"}`} className="border-b hover:bg-gray-50">
                          <td className="py-3 px-2">
                            <span
                              className={`inline-flex items-center justify-center w-7 h-7 rounded-full text-xs font-bold ${
                                index === 0
                                  ? "bg-yellow-100 text-yellow-800"
                                  : index === 1
                                    ? "bg-gray-100 text-gray-800"
                                    : index === 2
                                      ? "bg-orange-100 text-orange-800"
                                      : "bg-blue-50 text-blue-800"
                              }`}
                            >
                              {index + 1}
                            </span>
                          </td>
                          <td className="py-3 px-2 font-medium">
                            {produto.nome}
                          </td>
                          <td className="py-3 px-2 text-gray-600">
                            {produto.marca || "-"}
                          </td>
                          <td className="py-3 px-2 text-right">
                            {sanitizarNumero(produto.quantidade)}
                          </td>
                          <td className="py-3 px-2 text-right text-red-600">
                            {formatarMoeda(sanitizarNumero(produto.custo))}
                          </td>
                          <td className="py-3 px-2 text-right text-green-600">
                            {formatarMoeda(sanitizarNumero(produto.preco))}
                          </td>
                          <td className="py-3 px-2 text-right">
                            <span
                              className={`inline-block px-2 py-1 rounded text-xs font-semibold ${
                                sanitizarNumero(produto.margem) >= 50
                                  ? "bg-green-100 text-green-800"
                                  : sanitizarNumero(produto.margem) >= 30
                                    ? "bg-yellow-100 text-yellow-800"
                                    : "bg-red-100 text-red-800"
                              }`}
                            >
                              {sanitizarNumero(produto.margem).toFixed(1)}%
                            </span>
                          </td>
                          <td className="py-3 px-2 text-right font-bold text-green-600">
                            {formatarMoeda(
                              sanitizarNumero(produto.lucro_total),
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Análise por Categoria */}
              <div className="bg-white rounded-lg shadow-md p-6">
                <h3 className="text-lg font-semibold mb-4">
                  📊 Desempenho por Categoria
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {Object.entries(produtosPorCategoria).map(
                    ([categoria, dados]) => (
                      <div
                        key={categoria}
                        className="border rounded-lg p-4 hover:shadow-lg transition-shadow"
                      >
                        <div className="font-semibold text-gray-800 mb-2">
                          {categoria}
                        </div>
                        <div className="space-y-2 text-sm">
                          <div className="flex justify-between">
                            <span className="text-gray-600">Vendas:</span>
                            <span className="font-semibold">
                              {sanitizarNumero(dados.quantidade)}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-gray-600">Faturamento:</span>
                            <span className="font-semibold text-green-600">
                              {formatarMoeda(sanitizarNumero(dados.total))}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-gray-600">Margem Média:</span>
                            <span
                              className={`font-semibold ${
                                sanitizarNumero(dados.margem_media) >= 40
                                  ? "text-green-600"
                                  : sanitizarNumero(dados.margem_media) >= 25
                                    ? "text-yellow-600"
                                    : "text-red-600"
                              }`}
                            >
                              {sanitizarNumero(dados.margem_media).toFixed(1)}%
                            </span>
                          </div>
                        </div>
                      </div>
                    ),
                  )}
                </div>
              </div>

              {/* Alertas e Recomendações */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Produtos com Baixa Margem */}
                <div className="bg-white rounded-lg shadow-md p-6">
                  <div className="flex items-center gap-2 mb-4">
                    <svg
                      className="w-6 h-6 text-red-600"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                      />
                    </svg>
                    <h3 className="text-lg font-semibold">
                      ⚠️ Atenção: Margens Baixas
                    </h3>
                  </div>
                  <div className="space-y-2">
                    {produtosMaisLucrativos
                      .filter((p) => sanitizarNumero(p.margem) < 25)
                      .slice(0, 5)
                      .map((produto, index) => (
                        <div
                          key={`margem-baixa-${produto.nome}-${produto.marca || "sem-marca"}`}
                          className="p-3 bg-red-50 rounded-lg border-l-4 border-red-500"
                        >
                          <div className="font-medium text-sm">
                            {produto.nome}
                          </div>
                          <div className="text-xs text-gray-600 mt-1">
                            Margem:{" "}
                            <span className="font-semibold text-red-600">
                              {sanitizarNumero(produto.margem).toFixed(1)}%
                            </span>
                            {" - "}Revisar preço de custo ou venda
                          </div>
                        </div>
                      ))}
                    {produtosMaisLucrativos.filter(
                      (p) => sanitizarNumero(p.margem) < 25,
                    ).length === 0 && (
                      <div className="text-center text-gray-500 py-4">
                        ✅ Nenhum produto com margem crítica
                      </div>
                    )}
                  </div>
                </div>

                {/* Oportunidades */}
                <div className="bg-white rounded-lg shadow-md p-6">
                  <div className="flex items-center gap-2 mb-4">
                    <svg
                      className="w-6 h-6 text-blue-600"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                      />
                    </svg>
                    <h3 className="text-lg font-semibold">💡 Oportunidades</h3>
                  </div>
                  <div className="space-y-3">
                    {produtosMaisLucrativos
                      .filter(
                        (p) =>
                          sanitizarNumero(p.margem) >= 40 &&
                          sanitizarNumero(p.quantidade) < 10,
                      )
                      .slice(0, 3)
                      .map((produto, index) => (
                        <div
                          key={`oportunidade-${produto.nome}-${produto.marca || "sem-marca"}`}
                          className="p-3 bg-blue-50 rounded-lg border-l-4 border-blue-500"
                        >
                          <div className="font-medium text-sm">
                            {produto.nome}
                          </div>
                          <div className="text-xs text-blue-800 mt-1">
                            <strong>
                              Alta margem (
                              {sanitizarNumero(produto.margem).toFixed(1)}%)
                            </strong>{" "}
                            mas poucas vendas (
                            {sanitizarNumero(produto.quantidade)} un.)
                            <br />
                            💬 Considere promover este produto
                          </div>
                        </div>
                      ))}
                    {produtosMaisLucrativos
                      .filter((p) => sanitizarNumero(p.margem) >= 40)
                      .slice(0, 2)
                      .map((produto, index) => (
                        <div
                          key={`camp-${produto.nome || index}`}
                          className="p-3 bg-green-50 rounded-lg border-l-4 border-green-500"
                        >
                          <div className="font-medium text-sm">
                            {produto.nome}
                          </div>
                          <div className="text-xs text-green-800 mt-1">
                            <strong>⭐ Campeão de vendas</strong> com excelente
                            margem
                            <br />
                            💬 Mantenha em destaque
                          </div>
                        </div>
                      ))}
                  </div>
                </div>
              </div>

              {/* Gráfico de Margem vs Volume */}
              {mostrarGraficos && produtosMaisLucrativos.length > 0 && (
                <div className="bg-white rounded-lg shadow-md p-6">
                  <h3 className="text-lg font-semibold mb-4">
                    📈 Margem vs Volume de Vendas
                  </h3>
                  <ResponsiveContainer width="100%" height={400}>
                    <BarChart
                      data={produtosMaisLucrativos.slice(0, 15).map((p) => ({
                        ...p,
                        margem: sanitizarNumero(p.margem),
                        quantidade: sanitizarNumero(p.quantidade),
                      }))}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis
                        dataKey="nome"
                        angle={-45}
                        textAnchor="end"
                        height={120}
                        interval={0}
                        tick={{ fontSize: 11 }}
                      />
                      <YAxis
                        yAxisId="left"
                        orientation="left"
                        stroke="#10B981"
                        label={{
                          value: "Margem %",
                          angle: -90,
                          position: "insideLeft",
                        }}
                      />
                      <YAxis
                        yAxisId="right"
                        orientation="right"
                        stroke="#3B82F6"
                        label={{
                          value: "Quantidade",
                          angle: 90,
                          position: "insideRight",
                        }}
                      />
                      <Tooltip />
                      <Legend />
                      <Bar
                        yAxisId="left"
                        dataKey="margem"
                        fill="#10B981"
                        name="Margem %"
                      />
                      <Bar
                        yAxisId="right"
                        dataKey="quantidade"
                        fill="#3B82F6"
                        name="Qtd Vendida"
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Aba Histórico por Cliente */}
      {abaAtiva === "historico-cliente" && <HistoricoVendasClienteTab />}
    </div>
  );
}
