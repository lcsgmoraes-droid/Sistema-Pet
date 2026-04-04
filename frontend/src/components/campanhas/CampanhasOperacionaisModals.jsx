import CampanhasEnvioInativosModal from "./CampanhasEnvioInativosModal";
import CampanhasSorteioModal from "./CampanhasSorteioModal";
import CampanhasCodigosOfflineModal from "./CampanhasCodigosOfflineModal";
import CampanhasLoteModal from "./CampanhasLoteModal";

export default function CampanhasOperacionaisModals({
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
  rankLabels,
  modalLote,
  setModalLote,
  loteForm,
  setLoteForm,
  resultadoLote,
  enviarLote,
  enviandoLote,
}) {
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
        RANK_LABELS={rankLabels}
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
    </>
  );
}
