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
import {
  RANK_LABELS,
  hoje,
  primeiroDiaMes,
  createDefaultPremio,
} from "../components/campanhas/campanhasConstants";

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

  const campanhasConfiguracoes = {
    rankingConfig: rankingConfigState,
    setRankingConfig: setRankingConfigState,
    rankingConfigSalvando,
    schedulerConfig: schedulerConfigState,
    setSchedulerConfig: setSchedulerConfigState,
    schedulerConfigSalvando,
    salvarRankingConfig,
    salvarSchedulerConfig,
    recalcularRanking,
    setResultadoLote,
    setModalLote,
  };
  const campanhasRetencao = {
    retencaoEditando,
    setRetencaoEditando,
    salvandoRetencao,
    deletandoRetencao,
    salvarRetencao,
    deletarRetencao,
    novaRegraPadrao: NOVA_REGRA_RETENCAO_PADRAO,
  };
  const campanhasCupons = {
    anulando,
    anularCupom,
    formatarValorCupom,
  };
  const campanhasDestaque = {
    destaqueResultado,
    setDestaqueResultado,
    enviarDestaque,
    enviandoDestaque,
  };
  const campanhasSorteios = {
    setErroCriarSorteio,
    setModalSorteio,
    inscrevendo,
    inscreverSorteio,
    executandoSorteio,
    executarSorteio,
    cancelarSorteio,
    abrirCodigosOffline,
    sorteioResultado,
    setSorteioResultado,
  };
  const campanhasUnificacao = {
    confirmandoMerge,
    resultadoMerge,
    confirmarMerge,
    desfazerMerge,
  };

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

      <CampanhasMainContent
        aba={aba}
        onAbrirAba={setAba}
        consultas={campanhasConsultas}
        gestao={campanhasGestao}
        gestor={campanhasGestor}
        configuracoes={campanhasConfiguracoes}
        inativos={campanhasInativos}
        retencao={campanhasRetencao}
        cupons={campanhasCupons}
        destaque={campanhasDestaque}
        sorteios={campanhasSorteios}
        unificacao={campanhasUnificacao}
      />

      <CampanhasModalsLayer
        {...{
          modalEnvioInativos: campanhasInativos.modalEnvioInativos,
          setModalEnvioInativos: campanhasInativos.setModalEnvioInativos,
          resultadoEnvioInativos: campanhasInativos.resultadoEnvioInativos,
          setResultadoEnvioInativos: campanhasInativos.setResultadoEnvioInativos,
          envioInativosForm: campanhasInativos.envioInativosForm,
          setEnvioInativosForm: campanhasInativos.setEnvioInativosForm,
          enviandoInativos: campanhasInativos.enviandoInativos,
          enviarParaInativos: campanhasInativos.enviarParaInativos,
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
    </div>
  );
}
