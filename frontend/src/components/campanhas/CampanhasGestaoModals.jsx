import CampanhasCarimboManualModal from "./CampanhasCarimboManualModal";
import CampanhasNovaCampanhaModal from "./CampanhasNovaCampanhaModal";
import CampanhasCupomManualModal from "./CampanhasCupomManualModal";

export default function CampanhasGestaoModals({
  fidModalManual,
  setFidModalManual,
  fidClienteId,
  fidManualNota,
  setFidManualNota,
  lancarCarimboManual,
  fidLancandoManual,
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
}) {
  return (
    <>
      <CampanhasCarimboManualModal
        fidModalManual={fidModalManual}
        setFidModalManual={setFidModalManual}
        fidClienteId={fidClienteId}
        fidManualNota={fidManualNota}
        setFidManualNota={setFidManualNota}
        lancarCarimboManual={lancarCarimboManual}
        fidLancandoManual={fidLancandoManual}
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
