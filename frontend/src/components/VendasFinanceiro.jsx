import React, { useEffect, useMemo, useRef, useState } from "react";
import toast from "react-hot-toast";
import { useNavigate } from "react-router-dom";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import api from "../api";
import { useAuth } from "../contexts/AuthContext";
import HistoricoVendasClienteTab from "../pages/Financeiro/HistoricoVendasClienteTab";
import DiasUteisResumoPanel from "./financeiro/DiasUteisResumoPanel";
import ProdutosServicosDetalhadosTable from "./financeiro/ProdutosServicosDetalhadosTable";
import VendasAnaliseInteligentePanel from "./financeiro/VendasAnaliseInteligentePanel";
import VendasComparacaoPanel from "./financeiro/VendasComparacaoPanel";
import VendasFinanceiroGraficosResumo from "./financeiro/VendasFinanceiroGraficosResumo";
import VendasFinanceiroHeader from "./financeiro/VendasFinanceiroHeader";
import VendasListaPanel from "./financeiro/VendasListaPanel";
import VendasPromocoesResumoPanel from "./financeiro/VendasPromocoesResumoPanel";
import VendasRelatorioPersonalizadoModal from "./financeiro/VendasRelatorioPersonalizadoModal";
import VendasResultadoComposicaoPanel from "./financeiro/VendasResultadoComposicaoPanel";
import VendasResumoTabelasPanel from "./financeiro/VendasResumoTabelasPanel";
import {
  ajustarVendaImposto,
  calcularAnaliseInteligenteVendas,
  calcularPeriodoComparacaoFinanceiro,
  calcularVariacaoFinanceira,
  calcularValorRecebidoVenda,
  carregarConfigDiasUteis,
  carregarFeriadosCustomizados,
  COLUNAS_RELATORIO_VENDAS,
  dataKeyLocal,
  exportarPlanilhasExcel,
  filtrarVendasRelatorio,
  formatarDataVendaFinanceiro,
  formatarDataLocal,
  getDiasUteisStorageKey,
  getFeriadosStorageKey,
  getStatusVendaMeta,
  getTextoComparacaoPeriodo,
  listarDiasPeriodo,
  montarFeriadosPadrao,
  normalizarFormaPagamentoLabel,
  ordenarVendasRelatorio,
  parseDataHoraLocal,
  sanitizarNumero,
  vendaEstaEmAberto,
} from "./financeiro/vendasFinanceiroUtils";
import MoneyCell, { formatMoneyCellValue, isZeroMoneyValue } from "./ui/MoneyCell";
import NumberCell from "./ui/NumberCell";

export default function VendasFinanceiro() {
  const { user } = useAuth();
  const navigate = useNavigate();
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
    valor_recebido: 0,
    em_aberto: 0,
    quantidade_vendas: 0,
  });

  const [resumoComparacao, setResumoComparacao] = useState({
    venda_bruta: 0,
    taxa_entrega: 0,
    desconto: 0,
    venda_liquida: 0,
    valor_recebido: 0,
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
    "valor_recebido",
    "lucro",
    "status",
  ]);

  const abasVendasFinanceiro = useMemo(() => {
    const tabsRestritas = [{ id: "historico-cliente", label: "Historico por Cliente" }];

    if (!podeVerFinanceiroCompleto) return tabsRestritas;

    return [
      { id: "resumo", label: "Resumo" },
      ...tabsRestritas,
      { id: "produtos", label: "Totais por produto/servico" },
      { id: "lista", label: "Lista de Vendas" },
      { id: "comparacao", label: "Comparacao de Periodos" },
      { id: "analise", label: "Analise Inteligente" },
    ];
  }, [podeVerFinanceiroCompleto]);

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
  const abrirVendaNoPdv = (venda) => {
    if (!venda?.id) return;
    navigate(criarUrlPdvVenda(venda));
  };

  const formatarMoeda = (valor) => {
    return formatMoneyCellValue(valor);
  };

  const valorEhZeroVisual = isZeroMoneyValue;

  const formatarMoedaOuTraco = (valor) =>
    formatMoneyCellValue(valor, { zeroAsDash: true });

  const formatarMoedaComSinalOuTraco = (valor, sinal) =>
    formatMoneyCellValue(valor, { sign: sinal, zeroAsDash: true });

  const formatarPercentualOuTraco = (valor) =>
    valorEhZeroVisual(valor) ? "-" : `${valor}%`;

  const formatarData = formatarDataVendaFinanceiro;

  const listaVendasComImpostoAjustado = useMemo(
    () => listaVendas.map((venda) => ajustarVendaImposto(venda, mostrarImpostoTodasVendas)),
    [listaVendas, mostrarImpostoTodasVendas],
  );

  const filtrarVendasParaRelatorio = (escopo) =>
    filtrarVendasRelatorio(listaVendasComImpostoAjustado, {
      escopo,
      filtroFuncionario,
      filtroFormaPagamento,
      filtroCategoria,
      filtroStatusLista,
    });

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
  }, [listaVendasFiltrada]);

  const formatarDeducaoTotalizador = (valor) =>
    formatarMoedaComSinalOuTraco(valor, "-");

  const cardsTotalizadoresLista = [
    { label: "Vendas", value: totalizadoresListaVendas.quantidade.toLocaleString("pt-BR"), intent: "slate" },
    { label: "Com NF", value: totalizadoresListaVendas.com_nf.toLocaleString("pt-BR"), intent: "blue" },
    { label: "Venda Bruta", value: formatarMoedaOuTraco(totalizadoresListaVendas.venda_bruta), intent: "emerald" },
    { label: "Tx Loja", value: formatarMoedaComSinalOuTraco(totalizadoresListaVendas.taxa_loja, "+"), intent: "emerald" },
    { label: "Desconto", value: formatarDeducaoTotalizador(totalizadoresListaVendas.desconto), intent: "amber" },
    { label: "Tx. Entrega", value: formatarDeducaoTotalizador(totalizadoresListaVendas.taxa_entrega), intent: "blue" },
    { label: "Tx. Operac.", value: formatarDeducaoTotalizador(totalizadoresListaVendas.taxa_operacional), intent: "amber" },
    { label: "Tx. Cartao", value: formatarDeducaoTotalizador(totalizadoresListaVendas.taxa_cartao), intent: "violet" },
    { label: "Comissao", value: formatarDeducaoTotalizador(totalizadoresListaVendas.comissao), intent: "blue" },
    { label: "Imposto", value: formatarDeducaoTotalizador(totalizadoresListaVendas.imposto), intent: "red" },
    { label: "Custo Camp.", value: formatarDeducaoTotalizador(totalizadoresListaVendas.custo_campanha), intent: "cyan" },
    { label: "Liquida", value: formatarMoedaOuTraco(totalizadoresListaVendas.venda_liquida), intent: "blue" },
    { label: "Valor Recebido", value: formatarMoedaOuTraco(totalizadoresListaVendas.valor_recebido), intent: "emerald" },
    { label: "Custo", value: formatarDeducaoTotalizador(totalizadoresListaVendas.custo_produtos), intent: "amber" },
    {
      label: "Lucro",
      value: formatarMoedaOuTraco(totalizadoresListaVendas.lucro),
      intent: Number(totalizadoresListaVendas.lucro || 0) >= 0 ? "emerald" : "red",
    },
    { label: "MG Venda", value: formatarPercentualOuTraco(totalizadoresListaVendas.margem_sobre_venda), intent: "slate" },
    { label: "MG Custo", value: formatarPercentualOuTraco(totalizadoresListaVendas.margem_sobre_custo), intent: "slate" },
  ];

  const getTextoComparacao = () => getTextoComparacaoPeriodo(periodoComparacao);

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

  const calcularPeriodoComparacao = () =>
    calcularPeriodoComparacaoFinanceiro({
      dataInicio,
      dataFim,
      periodoComparacao,
    });

  const calcularVariacao = calcularVariacaoFinanceira;

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
          valor_recebido: 0,
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

  const calcularAnaliseInteligente = () => {
    const analise = calcularAnaliseInteligenteVendas({
      produtosAnalise,
      resumo,
      resumoComparacao,
      vendasPorData,
    });

    setProdutosMaisLucrativos(analise.produtosMaisLucrativos);
    setProdutosPorCategoria(analise.produtosPorCategoria);
    setAlertasInteligentesVendas(analise.alertasInteligentesVendas);
    setPrevisaoProximos7Dias(analise.previsaoProximos7Dias);
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
      <VendasFinanceiroHeader
        abaAtiva={abaAtiva}
        abasVendasFinanceiro={abasVendasFinanceiro}
        aplicarFiltroRapido={aplicarFiltroRapido}
        dataFim={dataFim}
        dataInicio={dataInicio}
        exportarParaExcel={exportarParaExcel}
        exportarParaPDF={exportarParaPDF}
        exportarRelatorioListaVendas={exportarRelatorioListaVendas}
        filtroCategoria={filtroCategoria}
        filtroFormaPagamento={filtroFormaPagamento}
        filtroFuncionario={filtroFuncionario}
        filtroSelecionado={filtroSelecionado}
        formasRecebimentoConsolidadas={formasRecebimentoConsolidadas}
        formatarData={formatarData}
        menuRelatoriosAberto={menuRelatoriosAberto}
        menuRelatoriosRef={menuRelatoriosRef}
        modoComparacao={modoComparacao}
        mostrarGraficos={mostrarGraficos}
        periodoComparacao={periodoComparacao}
        podeVerFinanceiroCompleto={podeVerFinanceiroCompleto}
        produtosDetalhados={produtosDetalhados}
        setAbaAtiva={setAbaAtiva}
        setDataFim={setDataFim}
        setDataInicio={setDataInicio}
        setFiltroCategoria={setFiltroCategoria}
        setFiltroFormaPagamento={setFiltroFormaPagamento}
        setFiltroFuncionario={setFiltroFuncionario}
        setFiltroSelecionado={setFiltroSelecionado}
        setMenuRelatoriosAberto={setMenuRelatoriosAberto}
        setModalRelatorioAberto={setModalRelatorioAberto}
        setModoComparacao={setModoComparacao}
        setMostrarGraficos={setMostrarGraficos}
        setPeriodoComparacao={setPeriodoComparacao}
        vendasPorFuncionario={vendasPorFuncionario}
      />

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

          <VendasResultadoComposicaoPanel
            abaAtiva={abaAtiva}
            abrirVendasEmAberto={abrirVendasEmAberto}
            filtroStatusLista={filtroStatusLista}
            fluxoResultadoCards={fluxoResultadoCards}
            formatarMoeda={formatarMoeda}
            resumo={resumo}
          />

          <VendasFinanceiroGraficosResumo
            coresGraficos={CORES_GRAFICOS}
            formasRecebimentoFiltradas={formasRecebimentoFiltradas}
            formatarData={formatarData}
            formatarDataLocal={formatarDataLocal}
            formatarMoeda={formatarMoeda}
            melhorDiaSemana={melhorDiaSemana}
            melhorHorario={melhorHorario}
            mostrarGraficos={mostrarGraficos}
            produtosDetalhadosFiltrados={produtosDetalhadosFiltrados}
            vendasPorDataCalendario={vendasPorDataCalendario}
            vendasPorDiaSemanaResumo={vendasPorDiaSemanaResumo}
            vendasPorHorarioComMovimento={vendasPorHorarioComMovimento}
          />

          <VendasPromocoesResumoPanel
            analisePromocoes={analisePromocoes}
            formatarMoeda={formatarMoeda}
          />

          <DiasUteisResumoPanel
            adicionarFeriadoCustomizado={adicionarFeriadoCustomizado}
            configDiasUteis={configDiasUteis}
            feriadosCustomizados={feriadosCustomizados}
            formatarData={formatarData}
            formatarMoeda={formatarMoeda}
            mostrarConfigFeriados={mostrarConfigFeriados}
            novoFeriadoData={novoFeriadoData}
            novoFeriadoNome={novoFeriadoNome}
            removerFeriadoCustomizado={removerFeriadoCustomizado}
            resumoDiasPeriodo={resumoDiasPeriodo}
            setConfigDiasUteis={setConfigDiasUteis}
            setMostrarConfigFeriados={setMostrarConfigFeriados}
            setNovoFeriadoData={setNovoFeriadoData}
            setNovoFeriadoNome={setNovoFeriadoNome}
          />

          <VendasResumoTabelasPanel
            formasRecebimentoConsolidadas={formasRecebimentoConsolidadas}
            formatarData={formatarData}
            vendasPorDataCalendario={vendasPorDataCalendario}
            vendasPorFuncionarioFiltradas={vendasPorFuncionarioFiltradas}
            vendasPorGrupo={vendasPorGrupo}
            vendasPorTipo={vendasPorTipo}
          />

        </div>
      )}

      <VendasRelatorioPersonalizadoModal
        aberto={modalRelatorioAberto}
        colunasDisponiveis={COLUNAS_RELATORIO_VENDAS}
        colunasRelatorio={colunasRelatorio}
        exportarRelatorioListaVendas={exportarRelatorioListaVendas}
        ordenacaoRelatorio={ordenacaoRelatorio}
        setModalRelatorioAberto={setModalRelatorioAberto}
        setOrdenacaoRelatorio={setOrdenacaoRelatorio}
        toggleColunaRelatorio={toggleColunaRelatorio}
      />

      {/* Aba Produtos Detalhados */}
      {abaAtiva === "produtos" && (
        <div className="bg-white rounded-lg shadow">
          <div className="bg-gray-600 text-white px-4 py-2 rounded-t-lg font-semibold">
            Produtos/Serviços
          </div>
          <ProdutosServicosDetalhadosTable
            linhas={produtosDetalhadosFiltrados}
            linhasTotal={produtosDetalhados}
          />
        </div>
      )}

      {/* Aba Lista de Vendas */}
      {abaAtiva === "lista" && (
        <VendasListaPanel
          abrirVendaNoPdv={abrirVendaNoPdv}
          cardsTotalizadoresLista={cardsTotalizadoresLista}
          filtroStatusLista={filtroStatusLista}
          formatarData={formatarData}
          formatarMoeda={formatarMoeda}
          getStatusVendaMeta={getStatusVendaMeta}
          limparFiltroStatusLista={limparFiltroStatusLista}
          listaVendasFiltrada={listaVendasFiltrada}
          listaVendasVisiveis={listaVendasVisiveis}
          mostrarImpostoTodasVendas={mostrarImpostoTodasVendas}
          setFiltroStatusLista={setFiltroStatusLista}
          setMostrarImpostoTodasVendas={setMostrarImpostoTodasVendas}
          toggleVendaExpandida={toggleVendaExpandida}
          vendasExpandidas={vendasExpandidas}
        />
      )}

      {/* Aba de Comparacao */}
      {abaAtiva === "comparacao" && (
        <VendasComparacaoPanel
          calcularVariacao={calcularVariacao}
          coresGraficos={CORES_GRAFICOS}
          dataFim={dataFim}
          dataInicio={dataInicio}
          formasRecebimentoComparacaoConsolidadas={formasRecebimentoComparacaoConsolidadas}
          formasRecebimentoConsolidadas={formasRecebimentoConsolidadas}
          formatarData={formatarData}
          formatarMoeda={formatarMoeda}
          getTextoComparacao={getTextoComparacao}
          resumo={resumo}
          resumoComparacao={resumoComparacao}
          setTipoComparacao={setTipoComparacao}
          tipoComparacao={tipoComparacao}
          vendasPorFuncionario={vendasPorFuncionario}
          vendasPorFuncionarioComparacao={vendasPorFuncionarioComparacao}
          vendasPorGrupo={vendasPorGrupo}
          vendasPorGrupoComparacao={vendasPorGrupoComparacao}
        />
      )}
      {/* Aba de Analise Inteligente */}
      {abaAtiva === "analise" && (
        <VendasAnaliseInteligentePanel
          alertasInteligentesVendas={alertasInteligentesVendas}
          formatarMoeda={formatarMoeda}
          loading={loading}
          mostrarGraficos={mostrarGraficos}
          previsaoProximos7Dias={previsaoProximos7Dias}
          produtosMaisLucrativos={produtosMaisLucrativos}
          produtosPorCategoria={produtosPorCategoria}
          resumo={resumo}
          sanitizarNumero={sanitizarNumero}
        />
      )}
      {/* Aba Histórico por Cliente */}
      {abaAtiva === "historico-cliente" && <HistoricoVendasClienteTab />}
    </div>
  );
}
