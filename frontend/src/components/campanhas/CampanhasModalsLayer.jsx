import CampanhasEnvioInativosModal from "./CampanhasEnvioInativosModal";
import CampanhasSorteioModal from "./CampanhasSorteioModal";
import CampanhasCodigosOfflineModal from "./CampanhasCodigosOfflineModal";
import CampanhasCarimboManualModal from "./CampanhasCarimboManualModal";
import CampanhasLoteModal from "./CampanhasLoteModal";
import CampanhasNovaCampanhaModal from "./CampanhasNovaCampanhaModal";
import CampanhasCupomManualModal from "./CampanhasCupomManualModal";

export default function CampanhasModalsLayer(props) {
  const {
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
    modalCriarCampanha,
    setModalCriarCampanha,
    novaCampanha,
    setNovaCampanha,
    erroCriarCampanha,
    criarCampanha,
    criandoCampanha,
    modalCupomAberto,
    setModalCupomAberto,
    setErroCupom,
    novoCupom,
    setNovoCupom,
    erroCupom,
    criarCupomManual,
    criandoCupom,
  } = props;

  return (
    <>
      <CampanhasEnvioInativosModal
        modalEnvioInativos={modalEnvioInativos}
        setModalEnvioInativos={setModalEnvioInativos}
        resultadoEnvioInativos={resultadoEnvioInativos}
        setResultadoEnvioInativos={setResultadoEnvioInativos}
        envioInativosForm={envioInativosForm}
        setEnvioInativosForm={setEnvioInativosForm}
        enviandoInativos={enviandoInativos}
        enviarParaInativos={enviarParaInativos}
      />

      <CampanhasSorteioModal
        modalSorteio={modalSorteio}
        setModalSorteio={setModalSorteio}
        novoSorteio={novoSorteio}
        setNovoSorteio={setNovoSorteio}
        erroCriarSorteio={erroCriarSorteio}
        criarSorteio={criarSorteio}
        criandoSorteio={criandoSorteio}
      />

      <CampanhasCodigosOfflineModal
        modalCodigosOffline={modalCodigosOffline}
        setModalCodigosOffline={setModalCodigosOffline}
        loadingCodigosOffline={loadingCodigosOffline}
        codigosOffline={codigosOffline}
        RANK_LABELS={RANK_LABELS}
      />

      <CampanhasCarimboManualModal
        fidModalManual={fidModalManual}
        setFidModalManual={setFidModalManual}
        fidClienteId={fidClienteId}
        fidManualNota={fidManualNota}
        setFidManualNota={setFidManualNota}
        lancarCarimboManual={lancarCarimboManual}
        fidLancandoManual={fidLancandoManual}
      />

      <CampanhasLoteModal
        modalLote={modalLote}
        setModalLote={setModalLote}
        loteForm={loteForm}
        setLoteForm={setLoteForm}
        resultadoLote={resultadoLote}
        enviarLote={enviarLote}
        enviandoLote={enviandoLote}
      />

      <CampanhasNovaCampanhaModal
        modalCriarCampanha={modalCriarCampanha}
        setModalCriarCampanha={setModalCriarCampanha}
        novaCampanha={novaCampanha}
        setNovaCampanha={setNovaCampanha}
        erroCriarCampanha={erroCriarCampanha}
        criarCampanha={criarCampanha}
        criandoCampanha={criandoCampanha}
      />

      <CampanhasCupomManualModal
        modalCupomAberto={modalCupomAberto}
        setModalCupomAberto={setModalCupomAberto}
        setErroCupom={setErroCupom}
        novoCupom={novoCupom}
        setNovoCupom={setNovoCupom}
        erroCupom={erroCupom}
        criarCupomManual={criarCupomManual}
        criandoCupom={criandoCupom}
      />
    </>
  );
}
