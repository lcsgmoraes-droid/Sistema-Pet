import CampanhasRankingClientesTable from "./CampanhasRankingClientesTable";
import CampanhasRankingConfigPanels from "./CampanhasRankingConfigPanels";
import CampanhasRankingCuponsSection from "./CampanhasRankingCuponsSection";
import CampanhasRankingDistribuicao from "./CampanhasRankingDistribuicao";
import CampanhasRankingFiltrosBar from "./CampanhasRankingFiltrosBar";
import CampanhasRankingLoteCard from "./CampanhasRankingLoteCard";

export default function CampanhasRankingTab(props) {
  const {
    rankLabels,
    filtroNivel,
    setFiltroNivel,
    onRecalcularRanking,
    loadingRanking,
    ranking,
    formatBRL,
    setResultadoLote,
    setModalLote,
    rankingConfig,
    setRankingConfig,
    rankingConfigLoading,
    salvarRankingConfig,
    rankingConfigSalvando,
    campanhas,
    filtroCupomBusca,
    setFiltroCupomBusca,
    filtroCupomDataInicio,
    setFiltroCupomDataInicio,
    filtroCupomDataFim,
    setFiltroCupomDataFim,
    filtroCupomCampanha,
    setFiltroCupomCampanha,
    carregarCupons,
    filtroCupomStatus,
    setFiltroCupomStatus,
    loadingCupons,
    cupons,
    cupomStatus,
    cupomDetalhes,
    setCupomDetalhes,
    anularCupom,
    anulando,
    formatarValorCupom,
  } = props;

  return (
    <div className="space-y-4">
      <CampanhasRankingFiltrosBar
        rankLabels={rankLabels}
        filtroNivel={filtroNivel}
        setFiltroNivel={setFiltroNivel}
        onRecalcularRanking={onRecalcularRanking}
      />

      {loadingRanking ? (
        <div className="p-8 text-center text-gray-400">
          Carregando ranking...
        </div>
      ) : !ranking ? (
        <div className="p-8 text-center text-gray-400">Carregando...</div>
      ) : (
        <>
          <CampanhasRankingDistribuicao
            rankLabels={rankLabels}
            ranking={ranking}
          />
          <CampanhasRankingClientesTable
            ranking={ranking}
            rankLabels={rankLabels}
            formatBRL={formatBRL}
          />
        </>
      )}

      <CampanhasRankingLoteCard
        setResultadoLote={setResultadoLote}
        setModalLote={setModalLote}
      />

      <CampanhasRankingConfigPanels
        rankingConfig={rankingConfig}
        setRankingConfig={setRankingConfig}
        rankingConfigLoading={rankingConfigLoading}
        salvarRankingConfig={salvarRankingConfig}
        rankingConfigSalvando={rankingConfigSalvando}
        rankLabels={rankLabels}
        formatBRL={formatBRL}
      />

      <CampanhasRankingCuponsSection
        campanhas={campanhas}
        filtroCupomBusca={filtroCupomBusca}
        setFiltroCupomBusca={setFiltroCupomBusca}
        filtroCupomDataInicio={filtroCupomDataInicio}
        setFiltroCupomDataInicio={setFiltroCupomDataInicio}
        filtroCupomDataFim={filtroCupomDataFim}
        setFiltroCupomDataFim={setFiltroCupomDataFim}
        filtroCupomCampanha={filtroCupomCampanha}
        setFiltroCupomCampanha={setFiltroCupomCampanha}
        carregarCupons={carregarCupons}
        filtroCupomStatus={filtroCupomStatus}
        setFiltroCupomStatus={setFiltroCupomStatus}
        loadingCupons={loadingCupons}
        cupons={cupons}
        cupomStatus={cupomStatus}
        cupomDetalhes={cupomDetalhes}
        setCupomDetalhes={setCupomDetalhes}
        anularCupom={anularCupom}
        anulando={anulando}
        formatarValorCupom={formatarValorCupom}
      />
    </div>
  );
}
