import HistoricoVendasClienteTab from "../../pages/Financeiro/HistoricoVendasClienteTab";
import DiasUteisResumoPanel from "./DiasUteisResumoPanel";
import ProdutosServicosDetalhadosTable from "./ProdutosServicosDetalhadosTable";
import VendasAnaliseInteligentePanel from "./VendasAnaliseInteligentePanel";
import VendasComparacaoPanel from "./VendasComparacaoPanel";
import VendasFinanceiroGraficosResumo from "./VendasFinanceiroGraficosResumo";
import VendasFinanceiroHeader from "./VendasFinanceiroHeader";
import VendasListaPanel from "./VendasListaPanel";
import VendasPromocoesResumoPanel from "./VendasPromocoesResumoPanel";
import VendasRelatorioPersonalizadoModal from "./VendasRelatorioPersonalizadoModal";
import VendasResultadoComposicaoPanel from "./VendasResultadoComposicaoPanel";
import VendasResumoTabelasPanel from "./VendasResumoTabelasPanel";

export default function VendasFinanceiroView({
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
}) {
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
                  <span className="font-semibold text-blue-800">Modo Comparação Ativo:</span>
                  <span className="text-blue-700 sm:ml-2">
                    Comparando{" "}
                    <span className="font-medium">
                      {formatarData(dataInicio)} até {formatarData(dataFim)}
                    </span>{" "}
                    com <span className="font-medium">{getTextoComparacao()}</span>
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
          onReprocessarVenda={(venda) => reprocessarRentabilidadeVendas({ vendaIds: [venda.id] })}
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
