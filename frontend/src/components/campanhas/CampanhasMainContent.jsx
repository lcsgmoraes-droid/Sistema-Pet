import { formatBRL } from "../../utils/formatters";
import CanalDescontos from "../../pages/CanalDescontos";
import CampanhasDashboardTab from "./CampanhasDashboardTab";
import CampanhasListTab from "./CampanhasListTab";
import CampanhasRetencaoTab from "./CampanhasRetencaoTab";
import CampanhasDestaqueTab from "./CampanhasDestaqueTab";
import CampanhasSorteiosTab from "./CampanhasSorteiosTab";
import CampanhasRankingTab from "./CampanhasRankingTab";
import CampanhasRelatoriosTab from "./CampanhasRelatoriosTab";
import CampanhasUnificacaoTab from "./CampanhasUnificacaoTab";
import CampanhasGestorTab from "./CampanhasGestorTab";
import CampanhasConfigTab from "./CampanhasConfigTab";
import {
  TIPO_LABELS,
  USER_CREATABLE_TYPES,
  CUPOM_STATUS,
  RANK_LABELS,
  createDefaultPremio,
} from "./campanhasConstants";

function formatarData(iso) {
  if (!iso) return "-";
  const d = iso.split("T")[0].split("-");
  return `${d[2]}/${d[1]}/${d[0]}`;
}

export default function CampanhasMainContent({
  aba,
  onAbrirAba,
  consultas,
  gestao,
  gestor,
  configuracoes,
  inativos,
  retencao,
  cupons,
  destaque,
  sorteios,
  unificacao,
}) {
  const {
    campanhas,
    loadingCampanhas,
    dashboard,
    loadingDashboard,
    retencaoRegras,
    loadingRetencao,
    ranking,
    loadingRanking,
    filtroNivel,
    setFiltroNivel,
    cupons: listaCupons,
    loadingCupons,
    filtroCupomStatus,
    setFiltroCupomStatus,
    filtroCupomBusca,
    setFiltroCupomBusca,
    filtroCupomDataInicio,
    setFiltroCupomDataInicio,
    filtroCupomDataFim,
    setFiltroCupomDataFim,
    filtroCupomCampanha,
    setFiltroCupomCampanha,
    cupomDetalhes,
    setCupomDetalhes,
    destaque: destaqueAtual,
    loadingDestaque,
    premiosPorVencedor,
    setPremiosPorVencedor,
    vencedoresSelecionados,
    setVencedoresSelecionados,
    sorteios: listaSorteios,
    loadingSorteios,
    sugestoes,
    loadingSugestoes,
    relatorio,
    loadingRelatorio,
    relDataInicio,
    setRelDataInicio,
    relDataFim,
    setRelDataFim,
    relTipo,
    setRelTipo,
    rankingConfigLoading,
    schedulerConfigLoading,
    carregarCupons,
    carregarDestaque,
    carregarSugestoes,
  } = consultas;

  return (
    <>
      {aba === "dashboard" && (
        <CampanhasDashboardTab
          loadingDashboard={loadingDashboard}
          dashboard={dashboard}
          onAbrirEnvioInativos={(dias) => {
            inativos.setModalEnvioInativos(dias);
            inativos.setResultadoEnvioInativos(null);
          }}
          onAbrirAba={onAbrirAba}
        />
      )}

      {aba === "campanhas" && (
        <CampanhasListTab
          campanhas={campanhas}
          loadingCampanhas={loadingCampanhas}
          campanhaEditando={gestao.campanhaEditando}
          paramsEditando={gestao.paramsEditando}
          setParamsEditando={gestao.setParamsEditando}
          arquivando={gestao.arquivando}
          toggling={gestao.toggling}
          salvandoParams={gestao.salvandoParams}
          tipoLabels={TIPO_LABELS}
          userCreatableTypes={USER_CREATABLE_TYPES}
          formatarParams={gestao.formatarParams}
          onNovaCampanha={() => {
            gestao.setErroCriarCampanha("");
            gestao.setModalCriarCampanha(true);
          }}
          onAbrirEdicao={gestao.abrirEdicao}
          onFecharEdicao={gestao.fecharEdicao}
          onArquivarCampanha={gestao.arquivarCampanha}
          onToggleCampanha={gestao.toggleCampanha}
          onSalvarParametros={gestao.salvarParametros}
        />
      )}

      {aba === "retencao" && (
        <CampanhasRetencaoTab
          retencaoEditando={retencao.retencaoEditando}
          salvandoRetencao={retencao.salvandoRetencao}
          loadingRetencao={loadingRetencao}
          retencaoRegras={retencaoRegras}
          deletandoRetencao={retencao.deletandoRetencao}
          onSalvarRetencao={retencao.salvarRetencao}
          onCancelarEdicao={() => retencao.setRetencaoEditando(null)}
          onNovaRegra={() =>
            retencao.setRetencaoEditando({ ...retencao.novaRegraPadrao })
          }
          onEditarRegra={retencao.setRetencaoEditando}
          onDeletarRegra={retencao.deletarRetencao}
        />
      )}

      {aba === "destaque" && (
        <CampanhasDestaqueTab
          loadingDestaque={loadingDestaque}
          destaque={destaqueAtual}
          carregarDestaque={carregarDestaque}
          premiosPorVencedor={premiosPorVencedor}
          setPremiosPorVencedor={setPremiosPorVencedor}
          vencedoresSelecionados={vencedoresSelecionados}
          setVencedoresSelecionados={setVencedoresSelecionados}
          createDefaultPremio={createDefaultPremio}
          destaqueResultado={destaque.destaqueResultado}
          setDestaqueResultado={destaque.setDestaqueResultado}
          enviarDestaque={destaque.enviarDestaque}
          enviandoDestaque={destaque.enviandoDestaque}
        />
      )}

      {aba === "sorteios" && (
        <CampanhasSorteiosTab
          loadingSorteios={loadingSorteios}
          sorteios={listaSorteios}
          sorteioResultado={sorteios.sorteioResultado}
          setSorteioResultado={sorteios.setSorteioResultado}
          setErroCriarSorteio={sorteios.setErroCriarSorteio}
          setModalSorteio={sorteios.setModalSorteio}
          inscrevendo={sorteios.inscrevendo}
          inscreverSorteio={sorteios.inscreverSorteio}
          executandoSorteio={sorteios.executandoSorteio}
          executarSorteio={sorteios.executarSorteio}
          cancelarSorteio={sorteios.cancelarSorteio}
          abrirCodigosOffline={sorteios.abrirCodigosOffline}
          rankLabels={RANK_LABELS}
        />
      )}

      {aba === "ranking" && (
        <CampanhasRankingTab
          rankLabels={RANK_LABELS}
          filtroNivel={filtroNivel}
          setFiltroNivel={setFiltroNivel}
          onRecalcularRanking={configuracoes.recalcularRanking}
          loadingRanking={loadingRanking}
          ranking={ranking}
          formatBRL={formatBRL}
          setResultadoLote={configuracoes.setResultadoLote}
          setModalLote={configuracoes.setModalLote}
          rankingConfig={configuracoes.rankingConfig}
          setRankingConfig={configuracoes.setRankingConfig}
          rankingConfigLoading={rankingConfigLoading}
          salvarRankingConfig={configuracoes.salvarRankingConfig}
          rankingConfigSalvando={configuracoes.rankingConfigSalvando}
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
          cupons={listaCupons}
          cupomStatus={CUPOM_STATUS}
          cupomDetalhes={cupomDetalhes}
          setCupomDetalhes={setCupomDetalhes}
          anularCupom={cupons.anularCupom}
          anulando={cupons.anulando}
          formatarValorCupom={cupons.formatarValorCupom}
        />
      )}

      {aba === "relatorios" && (
        <CampanhasRelatoriosTab
          relDataInicio={relDataInicio}
          setRelDataInicio={setRelDataInicio}
          relDataFim={relDataFim}
          setRelDataFim={setRelDataFim}
          relTipo={relTipo}
          setRelTipo={setRelTipo}
          relatorio={relatorio}
          loadingRelatorio={loadingRelatorio}
          formatBRL={formatBRL}
          formatarData={formatarData}
        />
      )}

      {aba === "unificacao" && (
        <CampanhasUnificacaoTab
          carregarSugestoes={carregarSugestoes}
          loadingSugestoes={loadingSugestoes}
          resultadoMerge={unificacao.resultadoMerge}
          desfazerMerge={unificacao.desfazerMerge}
          sugestoes={sugestoes}
          confirmarMerge={unificacao.confirmarMerge}
          confirmandoMerge={unificacao.confirmandoMerge}
        />
      )}

      {aba === "gestor" && (
        <CampanhasGestorTab
          {...gestor}
          formatBRL={formatBRL}
          RANK_LABELS={RANK_LABELS}
          CUPOM_STATUS={CUPOM_STATUS}
        />
      )}

      {aba === "config" && (
        <CampanhasConfigTab
          schedulerConfigLoading={schedulerConfigLoading}
          schedulerConfig={configuracoes.schedulerConfig}
          setSchedulerConfig={configuracoes.setSchedulerConfig}
          onSalvarSchedulerConfig={configuracoes.salvarSchedulerConfig}
          schedulerConfigSalvando={configuracoes.schedulerConfigSalvando}
        />
      )}

      {aba === "canais" && <CanalDescontos />}
    </>
  );
}
