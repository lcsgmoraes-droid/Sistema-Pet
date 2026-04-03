import CanalDescontos from "./CanalDescontos";
import { formatBRL } from "../utils/formatters";
import { useCampanhasConsultas } from "../hooks/useCampanhasConsultas";
import CampanhasTabsBar from "../components/campanhas/CampanhasTabsBar";
import CampanhasDashboardTab from "../components/campanhas/CampanhasDashboardTab";
import CampanhasListTab from "../components/campanhas/CampanhasListTab";
import CampanhasRetencaoTab from "../components/campanhas/CampanhasRetencaoTab";
import CampanhasDestaqueTab from "../components/campanhas/CampanhasDestaqueTab";
import CampanhasSorteiosTab from "../components/campanhas/CampanhasSorteiosTab";
import CampanhasRankingTab from "../components/campanhas/CampanhasRankingTab";
import CampanhasRelatoriosTab from "../components/campanhas/CampanhasRelatoriosTab";
import CampanhasUnificacaoTab from "../components/campanhas/CampanhasUnificacaoTab";
import CampanhasGestorTab from "../components/campanhas/CampanhasGestorTab";
import CampanhasConfigTab from "../components/campanhas/CampanhasConfigTab";
import CampanhasModalsLayer from "../components/campanhas/CampanhasModalsLayer";
import useCampanhasGestor from "../hooks/useCampanhasGestor";
import useCampanhasConfiguracoes from "../hooks/useCampanhasConfiguracoes";
import useCampanhasGestao from "../hooks/useCampanhasGestao";
import useCampanhasInativos from "../hooks/useCampanhasInativos";
import useCampanhasRetencao, {
  NOVA_REGRA_RETENCAO_PADRAO,
} from "../hooks/useCampanhasRetencao";
import useCampanhasCupons from "../hooks/useCampanhasCupons";
import useCampanhasDestaque from "../hooks/useCampanhasDestaque";
import useCampanhasSorteios from "../hooks/useCampanhasSorteios";
import useCampanhasLote from "../hooks/useCampanhasLote";
import useCampanhasUnificacao from "../hooks/useCampanhasUnificacao";
import useCampanhasFidelidade from "../hooks/useCampanhasFidelidade";
import {
  TIPO_LABELS,
  USER_CREATABLE_TYPES,
  CUPOM_STATUS,
  RANK_LABELS,
  hoje,
  primeiroDiaMes,
  createDefaultPremio,
} from "../components/campanhas/campanhasConstants";

export default function Campanhas() {
  const {
    aba,
    setAba,
    campanhas,
    setCampanhas,
    loadingCampanhas,
    dashboard,
    loadingDashboard,
    retencaoRegras,
    loadingRetencao,
    ranking,
    loadingRanking,
    filtroNivel,
    setFiltroNivel,
    cupons,
    setCupons,
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
    destaque,
    setDestaque,
    loadingDestaque,
    premiosPorVencedor,
    setPremiosPorVencedor,
    vencedoresSelecionados,
    setVencedoresSelecionados,
    sorteios,
    setSorteios,
    loadingSorteios,
    codigosOffline,
    setCodigosOffline,
    loadingCodigosOffline,
    setLoadingCodigosOffline,
    sugestoes,
    setSugestoes,
    loadingSugestoes,
    relatorio,
    loadingRelatorio,
    relDataInicio,
    setRelDataInicio,
    relDataFim,
    setRelDataFim,
    relTipo,
    setRelTipo,
    rankingConfig,
    setRankingConfig,
    rankingConfigLoading,
    schedulerConfig,
    setSchedulerConfig,
    schedulerConfigLoading,
    carregarCampanhas,
    carregarCupons,
    carregarRetencao,
    carregarRanking,
    carregarDestaque,
    carregarSorteios,
    carregarSugestoes,
    carregarRelatorio,
    carregarSchedulerConfig,
  } = useCampanhasConsultas({
    createDefaultPremio,
    hoje,
    primeiroDiaMes,
  });
  const campanhasGestor = useCampanhasGestor();
  const {
    rankingConfig: rankingConfigState,
    setRankingConfig: setRankingConfigState,
    rankingConfigSalvando,
    schedulerConfig: schedulerConfigState,
    setSchedulerConfig: setSchedulerConfigState,
    schedulerConfigSalvando,
    salvarRankingConfig,
    salvarSchedulerConfig,
    recalcularRanking,
  } = useCampanhasConfiguracoes({
    rankingConfig,
    setRankingConfig,
    schedulerConfig,
    setSchedulerConfig,
    carregarRanking,
    carregarSchedulerConfig,
  });
  const campanhasGestao = useCampanhasGestao({
    setCampanhas,
    carregarCampanhas,
  });
  const {
    modalEnvioInativos,
    setModalEnvioInativos,
    envioInativosForm,
    setEnvioInativosForm,
    enviandoInativos,
    resultadoEnvioInativos,
    setResultadoEnvioInativos,
    enviarParaInativos,
  } = useCampanhasInativos();
  const {
    retencaoEditando,
    setRetencaoEditando,
    salvandoRetencao,
    deletandoRetencao,
    salvarRetencao,
    deletarRetencao,
  } = useCampanhasRetencao({
    carregarRetencao,
  });
  const {
    anulando,
    modalCupomAberto,
    setModalCupomAberto,
    novoCupom,
    setNovoCupom,
    criandoCupom,
    erroCupom,
    setErroCupom,
    anularCupom,
    criarCupomManual,
    formatarValorCupom,
  } = useCampanhasCupons({
    setCupons,
    carregarCupons,
    aba,
    setAba,
  });
  const {
    enviandoDestaque,
    destaqueResultado,
    setDestaqueResultado,
    enviarDestaque,
  } = useCampanhasDestaque({
    destaque,
    premiosPorVencedor,
    vencedoresSelecionados,
  });
  const {
    modalSorteio,
    setModalSorteio,
    novoSorteio,
    setNovoSorteio,
    criandoSorteio,
    erroCriarSorteio,
    setErroCriarSorteio,
    executandoSorteio,
    inscrevendo,
    sorteioResultado,
    setSorteioResultado,
    modalCodigosOffline,
    setModalCodigosOffline,
    criarSorteio,
    inscreverSorteio,
    executarSorteio,
    cancelarSorteio,
    abrirCodigosOffline,
  } = useCampanhasSorteios({
    setSorteios,
    carregarSorteios,
    setCodigosOffline,
    setLoadingCodigosOffline,
  });
  const {
    modalLote,
    setModalLote,
    loteForm,
    setLoteForm,
    enviandoLote,
    resultadoLote,
    setResultadoLote,
    enviarLote,
  } = useCampanhasLote();
  const { confirmandoMerge, resultadoMerge, confirmarMerge, desfazerMerge } =
    useCampanhasUnificacao({
      setSugestoes,
      carregarSugestoes,
    });
  const {
    fidClienteId,
    fidModalManual,
    setFidModalManual,
    fidLancandoManual,
    fidManualNota,
    setFidManualNota,
    lancarCarimboManual,
  } = useCampanhasFidelidade();

  const formatarData = (iso) => {
    if (!iso) return "—";
    const d = iso.split("T")[0].split("-");
    return `${d[2]}/${d[1]}/${d[0]}`;
  };

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            🎯 Campanhas de Fidelidade
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Gerencie campanhas automáticas, ranking de clientes e cupons.
          </p>
        </div>

      </div>

      <CampanhasTabsBar aba={aba} onChange={setAba} />

      {/* ── ABA: DASHBOARD ── */}
      {aba === "dashboard" && (
        <CampanhasDashboardTab
          loadingDashboard={loadingDashboard}
          dashboard={dashboard}
          onAbrirEnvioInativos={(dias) => {
            setModalEnvioInativos(dias);
            setResultadoEnvioInativos(null);
          }}
          onAbrirAba={setAba}
        />
      )}

      {/* ── Modal: Envio para Inativos ── */}
      {aba === "campanhas" && (
        <CampanhasListTab
          campanhas={campanhas}
          loadingCampanhas={loadingCampanhas}
          campanhaEditando={campanhasGestao.campanhaEditando}
          paramsEditando={campanhasGestao.paramsEditando}
          setParamsEditando={campanhasGestao.setParamsEditando}
          arquivando={campanhasGestao.arquivando}
          toggling={campanhasGestao.toggling}
          salvandoParams={campanhasGestao.salvandoParams}
          tipoLabels={TIPO_LABELS}
          userCreatableTypes={USER_CREATABLE_TYPES}
          formatarParams={campanhasGestao.formatarParams}
          onNovaCampanha={() => {
            campanhasGestao.setErroCriarCampanha("");
            campanhasGestao.setModalCriarCampanha(true);
          }}
          onAbrirEdicao={campanhasGestao.abrirEdicao}
          onFecharEdicao={campanhasGestao.fecharEdicao}
          onArquivarCampanha={campanhasGestao.arquivarCampanha}
          onToggleCampanha={campanhasGestao.toggleCampanha}
          onSalvarParametros={campanhasGestao.salvarParametros}
        />
      )}


      {/* ── ABA: RETENÇÃO DINÂMICA ── */}
      {aba === "retencao" && (
        <CampanhasRetencaoTab
          retencaoEditando={retencaoEditando}
          salvandoRetencao={salvandoRetencao}
          loadingRetencao={loadingRetencao}
          retencaoRegras={retencaoRegras}
          deletandoRetencao={deletandoRetencao}
          onSalvarRetencao={salvarRetencao}
          onCancelarEdicao={() => setRetencaoEditando(null)}
          onNovaRegra={() =>
            setRetencaoEditando({ ...NOVA_REGRA_RETENCAO_PADRAO })
          }
          onEditarRegra={setRetencaoEditando}
          onDeletarRegra={deletarRetencao}
        />
      )}

      {aba === "destaque" && (
        <CampanhasDestaqueTab
          loadingDestaque={loadingDestaque}
          destaque={destaque}
          carregarDestaque={carregarDestaque}
          premiosPorVencedor={premiosPorVencedor}
          setPremiosPorVencedor={setPremiosPorVencedor}
          vencedoresSelecionados={vencedoresSelecionados}
          setVencedoresSelecionados={setVencedoresSelecionados}
          createDefaultPremio={createDefaultPremio}
          destaqueResultado={destaqueResultado}
          setDestaqueResultado={setDestaqueResultado}
          enviarDestaque={enviarDestaque}
          enviandoDestaque={enviandoDestaque}
        />
      )}

      {aba === "sorteios" && (
        <CampanhasSorteiosTab
          loadingSorteios={loadingSorteios}
          sorteios={sorteios}
          sorteioResultado={sorteioResultado}
          setSorteioResultado={setSorteioResultado}
          setErroCriarSorteio={setErroCriarSorteio}
          setModalSorteio={setModalSorteio}
          inscrevendo={inscrevendo}
          inscreverSorteio={inscreverSorteio}
          executandoSorteio={executandoSorteio}
          executarSorteio={executarSorteio}
          cancelarSorteio={cancelarSorteio}
          abrirCodigosOffline={abrirCodigosOffline}
          rankLabels={RANK_LABELS}
        />
      )}

      {/* ── ABA: RANKING ── */}
      {aba === "ranking" && (
        <CampanhasRankingTab
          rankLabels={RANK_LABELS}
          filtroNivel={filtroNivel}
          setFiltroNivel={setFiltroNivel}
          onRecalcularRanking={recalcularRanking}
          loadingRanking={loadingRanking}
          ranking={ranking}
          formatBRL={formatBRL}
          setResultadoLote={setResultadoLote}
          setModalLote={setModalLote}
          rankingConfig={rankingConfigState}
          setRankingConfig={setRankingConfigState}
          rankingConfigLoading={rankingConfigLoading}
          salvarRankingConfig={salvarRankingConfig}
          rankingConfigSalvando={rankingConfigSalvando}
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
          cupomStatus={CUPOM_STATUS}
          cupomDetalhes={cupomDetalhes}
          setCupomDetalhes={setCupomDetalhes}
          anularCupom={anularCupom}
          anulando={anulando}
          formatarValorCupom={formatarValorCupom}
        />
      )}

      {/* ── ABA: RELATÓRIOS ── */}
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

      {/* ── ABA: UNIFICAÇÃO CROSS-CANAL ── */}
      {aba === "unificacao" && (
        <CampanhasUnificacaoTab
          carregarSugestoes={carregarSugestoes}
          loadingSugestoes={loadingSugestoes}
          resultadoMerge={resultadoMerge}
          desfazerMerge={desfazerMerge}
          sugestoes={sugestoes}
          confirmarMerge={confirmarMerge}
          confirmandoMerge={confirmandoMerge}
        />
      )}

      {/* ── MODAL: CRIAR SORTEIO ── */}
      <CampanhasModalsLayer
        {...{
          modalEnvioInativos,
          setModalEnvioInativos,
          resultadoEnvioInativos,
          setResultadoEnvioInativos,
          envioInativosForm,
          setEnvioInativosForm,
          enviandoInativos,
          enviarParaInativos,
          modalSorteio,
          setModalSorteio,
          novoSorteio,
          setNovoSorteio,
          erroCriarSorteio,
          criarSorteio,
          criandoSorteio,
          modalCodigosOffline,
          setModalCodigosOffline,
          loadingCodigosOffline,
          codigosOffline,
          RANK_LABELS,
          fidModalManual,
          setFidModalManual,
          fidClienteId,
          fidManualNota,
          setFidManualNota,
          lancarCarimboManual,
          fidLancandoManual,
          modalLote,
          setModalLote,
          loteForm,
          setLoteForm,
          resultadoLote,
          enviarLote,
          enviandoLote,
          modalCriarCampanha: campanhasGestao.modalCriarCampanha,
          setModalCriarCampanha: campanhasGestao.setModalCriarCampanha,
          novaCampanha: campanhasGestao.novaCampanha,
          setNovaCampanha: campanhasGestao.setNovaCampanha,
          erroCriarCampanha: campanhasGestao.erroCriarCampanha,
          criarCampanha: campanhasGestao.criarCampanha,
          criandoCampanha: campanhasGestao.criandoCampanha,
          modalCupomAberto,
          setModalCupomAberto,
          setErroCupom,
          novoCupom,
          setNovoCupom,
          erroCupom,
          criarCupomManual,
          criandoCupom,
        }}
      />

      {aba === "gestor" && (
        <CampanhasGestorTab
          {...campanhasGestor}
          formatBRL={formatBRL}
          RANK_LABELS={RANK_LABELS}
          CUPOM_STATUS={CUPOM_STATUS}
        />
      )}

      {/* ── ABA: CONFIGURAÇÕES ── */}
      {aba === "config" && (
        <CampanhasConfigTab
          schedulerConfigLoading={schedulerConfigLoading}
          schedulerConfig={schedulerConfigState}
          setSchedulerConfig={setSchedulerConfigState}
          onSalvarSchedulerConfig={salvarSchedulerConfig}
          schedulerConfigSalvando={schedulerConfigSalvando}
        />
      )}

      {/* ── ABA: DESCONTOS POR CANAL ── */}
      {aba === "canais" && <CanalDescontos />}
    </div>
  );
}
