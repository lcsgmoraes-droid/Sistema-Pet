import { useEffect, useMemo, useRef, useState } from "react";
import toast from "react-hot-toast";
import { useNavigate } from "react-router-dom";
import api from "../api";
import { useAuth } from "../contexts/AuthContext";
import VendasFinanceiroView from "./financeiro/VendasFinanceiroView";
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
  filtrarDadosFinanceiroVendas,
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
  sanitizarNumero,
  vendaEstaEmAberto,
} from "./financeiro/vendasFinanceiroUtils";
import { useVendasFinanceiroActions } from "./financeiro/vendasFinanceiro/useVendasFinanceiroActions";
import { formatMoneyCellValue, isZeroMoneyValue } from "./ui/MoneyCell";

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

const RESUMO_VENDAS_VAZIO = {
  venda_bruta: 0,
  taxa_entrega: 0,
  desconto: 0,
  venda_liquida: 0,
  valor_recebido: 0,
  em_aberto: 0,
  quantidade_vendas: 0,
};

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
  const [resumo, setResumo] = useState(RESUMO_VENDAS_VAZIO);

  const [resumoComparacao, setResumoComparacao] = useState(RESUMO_VENDAS_VAZIO);

  const [vendasPorData, setVendasPorData] = useState([]);
  const [formasRecebimento, setFormasRecebimento] = useState([]);
  const [vendasPorFuncionario, setVendasPorFuncionario] = useState([]);
  const [vendasPorTipo, setVendasPorTipo] = useState([]);
  const [vendasPorGrupo, setVendasPorGrupo] = useState([]);
  const [produtosDetalhados, setProdutosDetalhados] = useState([]);
  const [listaVendas, setListaVendas] = useState([]);
  const [vendasExpandidas, setVendasExpandidas] = useState(new Set());

  // Dados de comparação estendidos
  const [formasRecebimentoComparacao, setFormasRecebimentoComparacao] = useState([]);
  const [vendasPorGrupoComparacao, setVendasPorGrupoComparacao] = useState([]);
  const [vendasPorFuncionarioComparacao, setVendasPorFuncionarioComparacao] = useState([]);

  // Estados para Análise Inteligente
  const [produtosMaisLucrativos, setProdutosMaisLucrativos] = useState([]);
  const [produtosPorCategoria, setProdutosPorCategoria] = useState({});
  const [produtosAnalise, setProdutosAnalise] = useState([]);
  const [alertasInteligentesVendas, setAlertasInteligentesVendas] = useState([]);
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
  const [feriadosCustomizados, setFeriadosCustomizados] = useState(carregarFeriadosCustomizados);
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

  const formatarMoedaOuTraco = (valor) => formatMoneyCellValue(valor, { zeroAsDash: true });

  const formatarMoedaComSinalOuTraco = (valor, sinal) =>
    formatMoneyCellValue(valor, { sign: sinal, zeroAsDash: true });

  const formatarPercentualOuTraco = (valor) => (valorEhZeroVisual(valor) ? "-" : `${valor}%`);

  const formatarData = formatarDataVendaFinanceiro;

  const listaVendasComImpostoAjustado = useMemo(
    () => listaVendas.map((venda) => ajustarVendaImposto(venda, mostrarImpostoTodasVendas)),
    [listaVendas, mostrarImpostoTodasVendas],
  );

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
  }, [
    configDiasUteis.considerarSabadoDiaUtil,
    dataInicio,
    dataFim,
    feriadosPorData,
    vendasPorData,
  ]);

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

  const fluxoResultadoCards = useMemo(() => montarFluxoResultadoCardsFinanceiro(resumo), [resumo]);

  const distribuicaoTemporalVendas = useMemo(
    () => calcularDistribuicaoTemporalVendasFinanceiro(vendasResumoPeriodo),
    [vendasResumoPeriodo],
  );
  const { vendasPorDiaSemanaResumo, vendasPorHorarioComMovimento, melhorDiaSemana, melhorHorario } =
    distribuicaoTemporalVendas;

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
        setFormasRecebimentoComparacao(responseComp.data.formas_recebimento || []);
        setVendasPorGrupoComparacao(responseComp.data.vendas_por_grupo || []);
        setVendasPorFuncionarioComparacao(responseComp.data.vendas_por_funcionario || []);
      } else {
        // Limpar dados de comparação quando desativado
        setResumoComparacao(RESUMO_VENDAS_VAZIO);
      }
    } catch (error) {
      console.error("Erro ao carregar relatório:", error);
    } finally {
      setLoading(false);
    }
  };

  const {
    exportarParaExcel,
    exportarParaPDF,
    exportarRelatorioListaVendas,
    registrarLinhaVendaReprocessada,
    reprocessarRentabilidadeVendas,
    toggleSelecaoTodasVendas,
    toggleSelecaoVenda,
  } = useVendasFinanceiroActions({
    carregarDados,
    colunasRelatorio,
    dataFim,
    dataInicio,
    filtroCanalVenda,
    filtroCategoria,
    filtroFormaPagamento,
    filtroFuncionario,
    filtroStatusLista,
    formasRecebimentoFiltradas,
    formatarData,
    linhasVendasRefs,
    listaVendasComImpostoAjustado,
    listaVendasFiltrada,
    listaVendasPorCanal,
    ordenacaoRelatorio,
    resumo,
    setFeedbackReprocessamento,
    setReprocessandoRentabilidade,
    setVendasSelecionadasIds,
    vendasPorDataCalendario,
  });

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
    window.localStorage.setItem(getFeriadosStorageKey(), JSON.stringify(feriadosCustomizados));
  }, [feriadosCustomizados]);

  useEffect(() => {
    window.localStorage.setItem(getDiasUteisStorageKey(), JSON.stringify(configDiasUteis));
  }, [configDiasUteis]);

  useEffect(() => {
    const fecharMenuAoClicarFora = (event) => {
      if (menuRelatoriosRef.current && !menuRelatoriosRef.current.contains(event.target)) {
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
    <VendasFinanceiroView
      {...{
        abaAtiva,
        abasVendasFinanceiro,
        aplicarFiltroRapido,
        dataFim,
        dataInicio,
        exportarParaExcel,
        exportarParaPDF,
        exportarRelatorioListaVendas,
        filtroCategoria,
        filtroCanalVenda,
        filtroFormaPagamento,
        filtroFuncionario,
        filtroSelecionado,
        formasRecebimentoConsolidadas,
        formatarData,
        menuRelatoriosAberto,
        menuRelatoriosRef,
        modoComparacao,
        mostrarGraficos,
        periodoComparacao,
        podeVerFinanceiroCompleto,
        produtosDetalhados,
        setAbaAtiva,
        setDataFim,
        setDataInicio,
        setFiltroCategoria,
        setFiltroCanalVenda,
        setFiltroFormaPagamento,
        setFiltroFuncionario,
        setFiltroSelecionado,
        setMenuRelatoriosAberto,
        setModalRelatorioAberto,
        setModoComparacao,
        setMostrarGraficos,
        setPeriodoComparacao,
        vendasPorFuncionario,
        getTextoComparacao,
        abrirVendasEmAberto,
        filtroStatusLista,
        fluxoResultadoCards,
        formatarMoeda,
        resumo,
        CORES_GRAFICOS,
        formasRecebimentoFiltradas,
        formatarDataLocal,
        melhorDiaSemana,
        melhorHorario,
        produtosDetalhadosFiltrados,
        vendasPorDataCalendario,
        vendasPorDiaSemanaResumo,
        vendasPorHorarioComMovimento,
        analisePromocoes,
        adicionarFeriadoCustomizado,
        configDiasUteis,
        feriadosCustomizados,
        mostrarConfigFeriados,
        novoFeriadoData,
        novoFeriadoNome,
        removerFeriadoCustomizado,
        resumoDiasPeriodo,
        setConfigDiasUteis,
        setMostrarConfigFeriados,
        setNovoFeriadoData,
        setNovoFeriadoNome,
        vendasPorFuncionarioFiltradas,
        vendasPorGrupo,
        vendasPorTipo,
        modalRelatorioAberto,
        COLUNAS_RELATORIO_VENDAS,
        colunasRelatorio,
        ordenacaoRelatorio,
        setOrdenacaoRelatorio,
        toggleColunaRelatorio,
        abrirVendaNoPdv,
        cardsTotalizadoresLista,
        getStatusVendaMeta,
        limparFiltroStatusLista,
        listaVendasFiltrada,
        listaVendasVisiveis,
        mostrarImpostoTodasVendas,
        algumasVendasFiltradasSelecionadas,
        reprocessarRentabilidadeVendas,
        vendasSelecionadas,
        toggleSelecaoTodasVendas,
        toggleSelecaoVenda,
        registrarLinhaVendaReprocessada,
        reprocessandoRentabilidade,
        setFiltroStatusLista,
        setMostrarImpostoTodasVendas,
        todasVendasFiltradasSelecionadas,
        toggleVendaExpandida,
        listaVendasPorCanal,
        feedbackReprocessamento,
        vendasSelecionadasIds,
        vendasExpandidas,
        calcularVariacao,
        formasRecebimentoComparacaoConsolidadas,
        resumoComparacao,
        setTipoComparacao,
        tipoComparacao,
        vendasPorFuncionarioComparacao,
        vendasPorGrupoComparacao,
        alertasInteligentesVendas,
        loading,
        previsaoProximos7Dias,
        produtosMaisLucrativos,
        produtosPorCategoria,
        sanitizarNumero,
      }}
    />
  );
}
