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
import { CANAL_LOJA_FISICA, normalizeSalesChannel } from "../utils/salesChannel";
import {
  REPROCESSAMENTO_DESTAQUE_MS,
  montarFeedbackReprocessamentoVendas,
} from "./financeiro/vendasReprocessamentoFeedback";
import {
  ajustarVendaImposto,
  calcularAnaliseInteligenteVendas,
  calcularAnalisePromocoesFinanceiro,
  calcularDistribuicaoTemporalVendasFinanceiro,
  calcularFiltroRapidoPeriodoVendas,
  calcularPeriodoComparacaoFinanceiro,
  calcularResumoDiasPeriodoFinanceiro,
  calcularTotalizadoresListaVendasFinanceiro,
  calcularVariacaoFinanceira,
  carregarConfigDiasUteis,
  carregarFeriadosCustomizados,
  COLUNAS_RELATORIO_VENDAS,
  consolidarFormasRecebimentoFinanceiro,
  exportarPlanilhasExcel,
  filtrarDadosFinanceiroVendas,
  filtrarVendasRelatorio,
  formatarDataVendaFinanceiro,
  formatarDataLocal,
  getDiasUteisStorageKey,
  getFeriadosStorageKey,
  getStatusVendaMeta,
  getTextoComparacaoPeriodo,
  montarCardsTotalizadoresListaVendasFinanceiro,
  montarFluxoResultadoCardsFinanceiro,
  montarFeriadosPeriodoFinanceiro,
  montarVendasPorDataCalendarioFinanceiro,
  ordenarVendasRelatorio,
  sanitizarNumero,
  vendaEstaEmAberto,
} from "./financeiro/vendasFinanceiroUtils";
import MoneyCell, { formatMoneyCellValue, isZeroMoneyValue } from "./ui/MoneyCell";
import NumberCell from "./ui/NumberCell";

function obterCanalVendaFinanceiro(venda) {
  return normalizeSalesChannel(
    venda?.canal_venda ||
      venda?.origem_canal_venda ||
      venda?.canal ||
      venda?.origem ||
      venda?.origem_loja_virtual,
    CANAL_LOJA_FISICA,
  );
}

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
  const [filtroCanalVenda, setFiltroCanalVenda] = useState("");
  const [mostrarImpostoTodasVendas, setMostrarImpostoTodasVendas] = useState(true);
  const [vendasSelecionadasIds, setVendasSelecionadasIds] = useState(new Set());
  const [reprocessandoRentabilidade, setReprocessandoRentabilidade] = useState(false);
  const [feedbackReprocessamento, setFeedbackReprocessamento] = useState({
    ids: new Set(),
    focoId: null,
    token: 0,
  });
  const linhasVendasRefs = useRef(new Map());
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

  const filtrosFinanceiros = { filtroFuncionario, filtroFormaPagamento, filtroCategoria };

  const formasRecebimentoConsolidadas = useMemo(
    () => consolidarFormasRecebimentoFinanceiro(formasRecebimento),
    [formasRecebimento],
  );

  const formasRecebimentoComparacaoConsolidadas = useMemo(
    () => consolidarFormasRecebimentoFinanceiro(formasRecebimentoComparacao),
    [formasRecebimentoComparacao],
  );

  const formasRecebimentoFiltradas = filtrarDadosFinanceiroVendas(
    formasRecebimentoConsolidadas,
    "formaPagamento",
    filtrosFinanceiros,
  );
  const vendasPorFuncionarioFiltradas = filtrarDadosFinanceiroVendas(
    vendasPorFuncionario,
    "funcionario",
    filtrosFinanceiros,
  );
  const produtosDetalhadosFiltrados = filtrarDadosFinanceiroVendas(
    produtosDetalhados,
    "categoria",
    filtrosFinanceiros,
  );

  const feriadosPorData = useMemo(() => {
    return montarFeriadosPeriodoFinanceiro({
      dataInicio,
      dataFim,
      feriadosCustomizados,
    });
  }, [dataInicio, dataFim, feriadosCustomizados]);

  const vendasPorDataCalendario = useMemo(() => {
    return montarVendasPorDataCalendarioFinanceiro({
      dataInicio,
      dataFim,
      vendasPorData,
      feriadosPorData,
      considerarSabadoDiaUtil: configDiasUteis.considerarSabadoDiaUtil,
    });
  }, [configDiasUteis.considerarSabadoDiaUtil, dataInicio, dataFim, feriadosPorData, vendasPorData]);

  const resumoDiasPeriodo = useMemo(
    () => calcularResumoDiasPeriodoFinanceiro(vendasPorDataCalendario),
    [vendasPorDataCalendario],
  );

  const listaVendasVisiveis = useMemo(
    () =>
      listaVendasComImpostoAjustado.filter(
        (venda) => String(venda?.status || "").toLowerCase() !== "cancelada",
      ),
    [listaVendasComImpostoAjustado],
  );

  const listaVendasPorCanal = useMemo(() => {
    if (!filtroCanalVenda) return listaVendasVisiveis;
    return listaVendasVisiveis.filter(
      (venda) => obterCanalVendaFinanceiro(venda) === filtroCanalVenda,
    );
  }, [filtroCanalVenda, listaVendasVisiveis]);

  const listaVendasFiltrada = useMemo(() => {
    if (filtroStatusLista !== "em_aberto") return listaVendasPorCanal;
    return listaVendasPorCanal.filter(vendaEstaEmAberto);
  }, [filtroStatusLista, listaVendasPorCanal]);

  const vendasSelecionadas = useMemo(
    () => listaVendasFiltrada.filter((venda) => vendasSelecionadasIds.has(venda.id)),
    [listaVendasFiltrada, vendasSelecionadasIds],
  );

  const todasVendasFiltradasSelecionadas =
    listaVendasFiltrada.length > 0 &&
    listaVendasFiltrada.every((venda) => vendasSelecionadasIds.has(venda.id));

  const algumasVendasFiltradasSelecionadas =
    vendasSelecionadas.length > 0 && !todasVendasFiltradasSelecionadas;

  const vendasResumoPeriodo = useMemo(() => listaVendasVisiveis, [listaVendasVisiveis]);

  const fluxoResultadoCards = useMemo(
    () => montarFluxoResultadoCardsFinanceiro(resumo),
    [resumo],
  );

  const distribuicaoTemporalVendas = useMemo(
    () => calcularDistribuicaoTemporalVendasFinanceiro(vendasResumoPeriodo),
    [vendasResumoPeriodo],
  );
  const {
    vendasPorDiaSemanaResumo,
    vendasPorHorarioComMovimento,
    melhorDiaSemana,
    melhorHorario,
  } = distribuicaoTemporalVendas;

  const analisePromocoes = useMemo(
    () => calcularAnalisePromocoesFinanceiro(vendasResumoPeriodo),
    [vendasResumoPeriodo],
  );

  const totalizadoresListaVendas = useMemo(
    () => calcularTotalizadoresListaVendasFinanceiro(listaVendasFiltrada),
    [listaVendasFiltrada],
  );

  const cardsTotalizadoresLista = useMemo(
    () =>
      montarCardsTotalizadoresListaVendasFinanceiro(totalizadoresListaVendas, {
        formatarMoedaOuTraco,
        formatarMoedaComSinalOuTraco,
        formatarPercentualOuTraco,
      }),
    [
      totalizadoresListaVendas,
      formatarMoedaOuTraco,
      formatarMoedaComSinalOuTraco,
      formatarPercentualOuTraco,
    ],
  );

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
      if (filtroCanalVenda) params.append("canal_venda", filtroCanalVenda);

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
    const periodo = calcularFiltroRapidoPeriodoVendas(filtro);
    if (!periodo) return;

    setDataInicio(periodo.inicio);
    setDataFim(periodo.fim);
    setFiltroSelecionado(filtro);
  };

  const calcularPeriodoComparacao = () =>
    calcularPeriodoComparacaoFinanceiro({
      dataInicio,
      dataFim,
      periodoComparacao,
    });

  const calcularVariacao = calcularVariacaoFinanceira;

  const montarParametrosRelatorio = (params) => ({
    ...params,
    ...(filtroCanalVenda ? { canal_venda: filtroCanalVenda } : {}),
  });

  const carregarDados = async () => {
    if (!podeVerFinanceiroCompleto) return;
    if (!dataInicio || !dataFim) return;

    setLoading(true);

    try {
      const response = await api.get("/relatorios/vendas/relatorio", {
        params: montarParametrosRelatorio({
          data_inicio: dataInicio,
          data_fim: dataFim,
        }),
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
          params: montarParametrosRelatorio(periodoComp),
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

  const toggleSelecaoVenda = (vendaId, selecionada) => {
    setVendasSelecionadasIds((prev) => {
      const proximo = new Set(prev);
      if (selecionada) {
        proximo.add(vendaId);
      } else {
        proximo.delete(vendaId);
      }
      return proximo;
    });
  };

  const toggleSelecaoTodasVendas = (selecionar) => {
    setVendasSelecionadasIds((prev) => {
      const proximo = new Set(prev);
      listaVendasFiltrada.forEach((venda) => {
        if (selecionar) {
          proximo.add(venda.id);
        } else {
          proximo.delete(venda.id);
        }
      });
      return proximo;
    });
  };

  const registrarLinhaVendaReprocessada = (vendaId, element) => {
    const idNormalizado = Number(vendaId);
    if (!Number.isFinite(idNormalizado) || idNormalizado <= 0) return;

    if (element) {
      linhasVendasRefs.current.set(idNormalizado, element);
    } else {
      linhasVendasRefs.current.delete(idNormalizado);
    }
  };

  const aplicarFeedbackReprocessamento = (vendaIds) => {
    const feedback = montarFeedbackReprocessamentoVendas({
      vendaIds,
      vendasVisiveis: listaVendasFiltrada,
    });

    if (!feedback.ids.length) return;

    setFeedbackReprocessamento((prev) => ({
      ids: new Set(feedback.ids),
      focoId: feedback.focoId,
      token: prev.token + 1,
    }));
  };

  const reprocessarRentabilidadeVendas = async ({ vendaIds = null, periodo = false } = {}) => {
    const ids = Array.isArray(vendaIds)
      ? vendaIds.map((id) => Number(id)).filter((id) => Number.isFinite(id) && id > 0)
      : [];
    const quantidade = periodo ? listaVendasPorCanal.length : ids.length;

    if (periodo && (!dataInicio || !dataFim)) {
      toast.error("Selecione um periodo para reprocessar.");
      return;
    }

    if (quantidade <= 0) {
      toast.error(periodo ? "Nao ha vendas no periodo atual." : "Selecione pelo menos uma venda.");
      return;
    }

    const descricaoEscopo = periodo
      ? `do periodo ${formatarData(dataInicio)} ate ${formatarData(dataFim)}`
      : "selecionada(s)";
    const confirmou = globalThis.confirm(
      `Reprocessar ${quantidade} venda(s) ${descricaoEscopo}?\n\n` +
        "Isso atualiza o custo das movimentacoes de estoque da venda para o custo atual do produto e recalcula custo, lucro e margem.",
    );

    if (!confirmou) return;

    const toastId = "reprocessar-rentabilidade-vendas";
    setReprocessandoRentabilidade(true);
    toast.loading("Reprocessando rentabilidade das vendas...", { id: toastId });

    try {
      const payload = periodo
        ? {
            data_inicio: dataInicio,
            data_fim: dataFim,
            ...(filtroCanalVenda ? { canal_venda: filtroCanalVenda } : {}),
          }
        : { venda_ids: ids };

      const { data } = await api.post(
        "/relatorios/vendas/reprocessar-rentabilidade",
        payload,
      );
      const total = Number(data?.total_reprocessado || 0);
      const vendasReprocessadasIds = Array.isArray(data?.vendas)
        ? data.vendas.map((venda) => venda?.venda_id)
        : ids;
      toast.success(`${total} venda(s) reprocessada(s).`, { id: toastId });
      setVendasSelecionadasIds(new Set());
      await carregarDados();
      aplicarFeedbackReprocessamento(vendasReprocessadasIds);
    } catch (error) {
      console.error("Erro ao reprocessar rentabilidade:", error);
      toast.error(
        error?.response?.data?.detail || "Nao foi possivel reprocessar as vendas.",
        { id: toastId },
      );
    } finally {
      setReprocessandoRentabilidade(false);
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
    filtroCanalVenda,
    abaAtiva,
    podeVerFinanceiroCompleto,
  ]);

  useEffect(() => {
    const idsVisiveis = new Set(listaVendasFiltrada.map((venda) => venda.id));
    setVendasSelecionadasIds((prev) => {
      const idsMantidos = Array.from(prev).filter((id) => idsVisiveis.has(id));
      return idsMantidos.length === prev.size ? prev : new Set(idsMantidos);
    });
  }, [listaVendasFiltrada]);

  useEffect(() => {
    if (!feedbackReprocessamento.token || !feedbackReprocessamento.ids.size) return undefined;

    const feedbackAtual = montarFeedbackReprocessamentoVendas({
      vendaIds: Array.from(feedbackReprocessamento.ids),
      vendasVisiveis: listaVendasFiltrada,
    });
    const focoId = feedbackAtual.focoId || feedbackReprocessamento.focoId;
    const linhaFoco = focoId ? linhasVendasRefs.current.get(focoId) : null;

    if (linhaFoco) {
      const rolarParaLinha = () => {
        linhaFoco.scrollIntoView({
          behavior: "smooth",
          block: "center",
          inline: "nearest",
        });
      };

      if (globalThis.requestAnimationFrame) {
        globalThis.requestAnimationFrame(rolarParaLinha);
      } else {
        globalThis.setTimeout(rolarParaLinha, 0);
      }
    }

    const timeoutId = globalThis.setTimeout(() => {
      setFeedbackReprocessamento({ ids: new Set(), focoId: null, token: 0 });
    }, REPROCESSAMENTO_DESTAQUE_MS);

    return () => globalThis.clearTimeout(timeoutId);
  }, [feedbackReprocessamento, listaVendasFiltrada]);

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
    <div className="min-h-screen bg-gray-50 p-3 sm:p-4 lg:p-6">
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
        filtroCanalVenda={filtroCanalVenda}
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
        setFiltroCanalVenda={setFiltroCanalVenda}
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
            <div className="mb-6 rounded border-l-4 border-blue-500 bg-blue-50 p-4">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
                <svg
                  className="h-5 w-5 shrink-0 text-blue-500"
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
                  <span className="text-blue-700 sm:ml-2">
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
          filtroCanalVenda={filtroCanalVenda}
          filtroStatusLista={filtroStatusLista}
          formatarData={formatarData}
          formatarMoeda={formatarMoeda}
          getStatusVendaMeta={getStatusVendaMeta}
          limparFiltroStatusLista={limparFiltroStatusLista}
          listaVendasFiltrada={listaVendasFiltrada}
          listaVendasVisiveis={listaVendasVisiveis}
          mostrarImpostoTodasVendas={mostrarImpostoTodasVendas}
          algumasVendasFiltradasSelecionadas={algumasVendasFiltradasSelecionadas}
          onReprocessarPeriodo={() => reprocessarRentabilidadeVendas({ periodo: true })}
          onReprocessarSelecionadas={() =>
            reprocessarRentabilidadeVendas({
              vendaIds: vendasSelecionadas.map((venda) => venda.id),
            })
          }
          onReprocessarVenda={(venda) =>
            reprocessarRentabilidadeVendas({ vendaIds: [venda.id] })
          }
          onToggleSelecaoTodasVendas={toggleSelecaoTodasVendas}
          onToggleSelecaoVenda={toggleSelecaoVenda}
          onVendaRowRef={registrarLinhaVendaReprocessada}
          reprocessandoRentabilidade={reprocessandoRentabilidade}
          setFiltroCanalVenda={setFiltroCanalVenda}
          setFiltroStatusLista={setFiltroStatusLista}
          setMostrarImpostoTodasVendas={setMostrarImpostoTodasVendas}
          todasVendasFiltradasSelecionadas={todasVendasFiltradasSelecionadas}
          toggleVendaExpandida={toggleVendaExpandida}
          totalVendasPeriodoReprocessamento={listaVendasPorCanal.length}
          totalVendasSelecionadas={vendasSelecionadas.length}
          vendaReprocessadaFocoId={feedbackReprocessamento.focoId}
          vendasReprocessadasIds={feedbackReprocessamento.ids}
          vendasSelecionadasIds={vendasSelecionadasIds}
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
