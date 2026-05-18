import React, { useEffect, useMemo, useRef, useState } from "react";
import toast from "react-hot-toast";
import { useNavigate } from "react-router-dom";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
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
  exportarRelatorioListaVendasFinanceiro,
  exportarVendasFinanceiroExcel,
  exportarVendasFinanceiroPdf,
} from "./financeiro/vendasFinanceiroExportadores";
import useVendasFinanceiroData from "./financeiro/useVendasFinanceiroData";
import {
  CORES_GRAFICOS_VENDAS,
  COLUNAS_RELATORIO_VENDAS,
  aplicarFiltrosVendasFinanceiro,
  ajustarVendaImposto,
  calcularAnalisePromocoes,
  calcularFeriadosPorData,
  calcularFluxoResultadoCards,
  calcularPeriodoFiltroRapido,
  calcularResumoDiasPeriodo,
  calcularTotalizadoresListaVendas,
  calcularVariacao,
  calcularVendasPorDataCalendario,
  calcularVendasPorDiaSemanaResumo,
  calcularVendasPorHorarioResumo,
  carregarConfigDiasUteis,
  carregarFeriadosCustomizados,
  consolidarFormasRecebimento,
  filtrarHorariosComMovimento,
  formatarData,
  formatarDataLocal,
  getDiasUteisStorageKey,
  getFeriadosStorageKey,
  getStatusVendaMeta,
  montarCardsTotalizadoresLista,
  obterTextoComparacao,
  sanitizarNumero,
  selecionarMelhorPorValorLiquido,
  vendaEstaEmAberto,
} from "./financeiro/vendasFinanceiroUtils";

export default function VendasFinanceiro() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const userPermissions = user?.permissions || [];
  const podeVerFinanceiroCompleto =
    user?.is_admin === true || userPermissions.includes("relatorios.financeiro");
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

  const [vendasExpandidas, setVendasExpandidas] = useState(new Set());

  const {
    alertasInteligentesVendas,
    formasRecebimento,
    formasRecebimentoComparacao,
    listaVendas,
    loading,
    previsaoProximos7Dias,
    produtosDetalhados,
    produtosMaisLucrativos,
    produtosPorCategoria,
    resumo,
    resumoComparacao,
    vendasPorData,
    vendasPorFuncionario,
    vendasPorFuncionarioComparacao,
    vendasPorGrupo,
    vendasPorGrupoComparacao,
    vendasPorTipo,
  } = useVendasFinanceiroData({
    abaAtiva,
    dataFim,
    dataInicio,
    modoComparacao,
    periodoComparacao,
    podeVerFinanceiroCompleto,
  });

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

  const listaVendasComImpostoAjustado = useMemo(
    () => listaVendas.map((venda) => ajustarVendaImposto(venda, mostrarImpostoTodasVendas)),
    [listaVendas, mostrarImpostoTodasVendas],
  );

  const exportarRelatorioListaVendas = ({ escopo }) =>
    exportarRelatorioListaVendasFinanceiro({
      colunasRelatorio,
      escopo,
      filtroCategoria,
      filtroFormaPagamento,
      filtroFuncionario,
      filtroStatusLista,
      listaVendas: listaVendasComImpostoAjustado,
      ordenacaoRelatorio,
    });

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

  const filtrosAvancados = {
    filtroFuncionario,
    filtroFormaPagamento,
    filtroCategoria,
  };

  const formasRecebimentoConsolidadas = useMemo(
    () => consolidarFormasRecebimento(formasRecebimento),
    [formasRecebimento],
  );

  const formasRecebimentoComparacaoConsolidadas = useMemo(
    () => consolidarFormasRecebimento(formasRecebimentoComparacao),
    [formasRecebimentoComparacao],
  );

  const formasRecebimentoFiltradas = aplicarFiltrosVendasFinanceiro({
    dados: formasRecebimentoConsolidadas,
    tipo: "formaPagamento",
    ...filtrosAvancados,
  });
  const vendasPorFuncionarioFiltradas = aplicarFiltrosVendasFinanceiro({
    dados: vendasPorFuncionario,
    tipo: "funcionario",
    ...filtrosAvancados,
  });
  const produtosDetalhadosFiltrados = aplicarFiltrosVendasFinanceiro({
    dados: produtosDetalhados,
    tipo: "categoria",
    ...filtrosAvancados,
  });

  const feriadosPorData = useMemo(
    () => calcularFeriadosPorData({ dataInicio, dataFim, feriadosCustomizados }),
    [dataInicio, dataFim, feriadosCustomizados],
  );

  const vendasPorDataCalendario = useMemo(
    () =>
      calcularVendasPorDataCalendario({
        vendasPorData,
        dataInicio,
        dataFim,
        feriadosPorData,
        considerarSabadoDiaUtil: configDiasUteis.considerarSabadoDiaUtil,
      }),
    [configDiasUteis.considerarSabadoDiaUtil, dataInicio, dataFim, feriadosPorData, vendasPorData],
  );

  const resumoDiasPeriodo = useMemo(
    () => calcularResumoDiasPeriodo(vendasPorDataCalendario),
    [vendasPorDataCalendario],
  );

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

  const fluxoResultadoCards = useMemo(
    () => calcularFluxoResultadoCards(resumo),
    [resumo],
  );

  const vendasPorDiaSemanaResumo = useMemo(
    () => calcularVendasPorDiaSemanaResumo(vendasResumoPeriodo),
    [vendasResumoPeriodo],
  );

  const vendasPorHorarioResumo = useMemo(
    () => calcularVendasPorHorarioResumo(vendasResumoPeriodo),
    [vendasResumoPeriodo],
  );

  const vendasPorHorarioComMovimento = useMemo(
    () => filtrarHorariosComMovimento(vendasPorHorarioResumo),
    [vendasPorHorarioResumo],
  );

  const melhorDiaSemana = useMemo(
    () => selecionarMelhorPorValorLiquido(vendasPorDiaSemanaResumo),
    [vendasPorDiaSemanaResumo],
  );

  const melhorHorario = useMemo(
    () => selecionarMelhorPorValorLiquido(vendasPorHorarioComMovimento),
    [vendasPorHorarioComMovimento],
  );

  const analisePromocoes = useMemo(
    () => calcularAnalisePromocoes(vendasResumoPeriodo),
    [vendasResumoPeriodo],
  );

  const totalizadoresListaVendas = useMemo(
    () => calcularTotalizadoresListaVendas(listaVendasFiltrada),
    [listaVendasFiltrada],
  );

  const cardsTotalizadoresLista = useMemo(
    () => montarCardsTotalizadoresLista(totalizadoresListaVendas),
    [totalizadoresListaVendas],
  );

  const textoComparacao = useMemo(
    () => obterTextoComparacao(periodoComparacao),
    [periodoComparacao],
  );
  const getTextoComparacao = () => textoComparacao;

  const exportarParaPDF = () =>
    exportarVendasFinanceiroPdf({
      dataFim,
      dataInicio,
      filtroCategoria,
      filtroFormaPagamento,
      filtroFuncionario,
    });

  const exportarParaExcel = () =>
    exportarVendasFinanceiroExcel({
      dataFim,
      dataInicio,
      formasRecebimentoFiltradas,
      resumo,
      vendasPorDataCalendario,
    });

  const aplicarFiltroRapido = (filtro) => {
    const periodo = calcularPeriodoFiltroRapido(filtro);
    if (!periodo) return;

    setDataInicio(periodo.inicio);
    setDataFim(periodo.fim);
    setFiltroSelecionado(filtro);
  };

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
                    <span className="font-medium">{textoComparacao}</span>
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
            coresGraficos={CORES_GRAFICOS_VENDAS}
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
          coresGraficos={CORES_GRAFICOS_VENDAS}
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
