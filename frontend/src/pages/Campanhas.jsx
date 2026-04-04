import { useCampanhasConsultas } from "../hooks/useCampanhasConsultas";
import CampanhasTabsBar from "../components/campanhas/CampanhasTabsBar";
import CampanhasMainContent from "../components/campanhas/CampanhasMainContent";
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
import { hoje, primeiroDiaMes, createDefaultPremio } from "../components/campanhas/campanhasConstants";
import useCampanhasPageComposition from "../hooks/useCampanhasPageComposition";

export default function Campanhas() {
  const campanhasConsultas = useCampanhasConsultas({
    createDefaultPremio,
    hoje,
    primeiroDiaMes,
  });
  const {
    aba,
    setAba,
    campanhas,
    setCampanhas,
    cupons,
    setCupons,
    destaque,
    premiosPorVencedor,
    vencedoresSelecionados,
    sorteios,
    setSorteios,
    codigosOffline,
    setCodigosOffline,
    loadingCodigosOffline,
    setLoadingCodigosOffline,
    sugestoes,
    setSugestoes,
    rankingConfig,
    setRankingConfig,
    schedulerConfig,
    setSchedulerConfig,
    carregarCampanhas,
    carregarCupons,
    carregarRetencao,
    carregarRanking,
    carregarSorteios,
    carregarSugestoes,
    carregarSchedulerConfig,
  } = campanhasConsultas;

  const campanhasGestor = useCampanhasGestor();
  const campanhasGestao = useCampanhasGestao({
    setCampanhas,
    carregarCampanhas,
  });
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
  const campanhasInativos = useCampanhasInativos();
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
    premiosPorVencedor: campanhasConsultas.premiosPorVencedor,
    vencedoresSelecionados: campanhasConsultas.vencedoresSelecionados,
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
  const { mainContentProps, modalsLayerProps } = useCampanhasPageComposition({
    aba,
    setAba,
    consultas: campanhasConsultas,
    gestao: campanhasGestao,
    gestor: {
      ...campanhasGestor,
      fidClienteId,
      fidModalManual,
      setFidModalManual,
      fidLancandoManual,
      fidManualNota,
      setFidManualNota,
      lancarCarimboManual,
    },
    configuracoes: {
      rankingConfig: rankingConfigState,
      setRankingConfig: setRankingConfigState,
      rankingConfigSalvando,
      schedulerConfig: schedulerConfigState,
      setSchedulerConfig: setSchedulerConfigState,
      schedulerConfigSalvando,
      salvarRankingConfig,
      salvarSchedulerConfig,
      recalcularRanking,
      modalLote,
      setModalLote,
      loteForm,
      setLoteForm,
      resultadoLote,
      setResultadoLote,
      enviarLote,
      enviandoLote,
    },
    inativos: campanhasInativos,
    retencao: {
      retencaoEditando,
      setRetencaoEditando,
      salvandoRetencao,
      deletandoRetencao,
      salvarRetencao,
      deletarRetencao,
      novaRegraPadrao: NOVA_REGRA_RETENCAO_PADRAO,
    },
    cupons: {
      anulando,
      anularCupom,
      formatarValorCupom,
      modalCupomAberto,
      setModalCupomAberto,
      novoCupom,
      setNovoCupom,
      criandoCupom,
      erroCupom,
      setErroCupom,
      criarCupomManual,
    },
    destaque: {
      enviandoDestaque,
      destaqueResultado,
      setDestaqueResultado,
      enviarDestaque,
    },
    sorteios: {
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
    },
    unificacao: {
      confirmandoMerge,
      resultadoMerge,
      confirmarMerge,
      desfazerMerge,
    },
  });

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Campanhas de Fidelidade
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Gerencie campanhas automaticas, ranking de clientes e cupons.
          </p>
        </div>
      </div>

      <CampanhasTabsBar aba={aba} onChange={setAba} />

      <CampanhasMainContent {...mainContentProps} />

      <CampanhasModalsLayer {...modalsLayerProps} />
    </div>
  );
}
