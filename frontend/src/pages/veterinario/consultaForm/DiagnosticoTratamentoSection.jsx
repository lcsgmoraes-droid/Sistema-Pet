import DiagnosticoBasicoSection from "./DiagnosticoBasicoSection";
import FluxosVinculadosConsulta from "./FluxosVinculadosConsulta";
import PrescricaoMedicamentosSection from "./PrescricaoMedicamentosSection";
import ProcedimentosRealizadosSection from "./ProcedimentosRealizadosSection";
import TimelineConsultaPanel from "./TimelineConsultaPanel";

export default function DiagnosticoTratamentoSection({
  modoSomenteLeitura,
  form,
  setCampo,
  medicamentosCatalogo,
  procedimentosCatalogo,
  consultaIdAtual,
  timelineConsulta,
  carregandoTimeline,
  adicionarItem,
  removerItem,
  setItem,
  selecionarMedicamentoNoItem,
  recalcularDoseItem,
  adicionarProcedimento,
  removerProcedimento,
  setProcedimentoItem,
  selecionarProcedimentoCatalogo,
  abrirModalInsumoRapido,
  abrirFluxoConsulta,
  carregarTimelineConsulta,
  onOpenTimelineLink,
}) {
  return (
    <div className="space-y-4">
      <DiagnosticoBasicoSection
        modoSomenteLeitura={modoSomenteLeitura}
        form={form}
        setCampo={setCampo}
      />

      <PrescricaoMedicamentosSection
        modoSomenteLeitura={modoSomenteLeitura}
        form={form}
        medicamentosCatalogo={medicamentosCatalogo}
        adicionarItem={adicionarItem}
        removerItem={removerItem}
        setItem={setItem}
        selecionarMedicamentoNoItem={selecionarMedicamentoNoItem}
        recalcularDoseItem={recalcularDoseItem}
      />

      <ProcedimentosRealizadosSection
        modoSomenteLeitura={modoSomenteLeitura}
        form={form}
        procedimentosCatalogo={procedimentosCatalogo}
        consultaIdAtual={consultaIdAtual}
        adicionarProcedimento={adicionarProcedimento}
        removerProcedimento={removerProcedimento}
        setProcedimentoItem={setProcedimentoItem}
        selecionarProcedimentoCatalogo={selecionarProcedimentoCatalogo}
        abrirModalInsumoRapido={abrirModalInsumoRapido}
      />

      <FluxosVinculadosConsulta
        consultaIdAtual={consultaIdAtual}
        abrirFluxoConsulta={abrirFluxoConsulta}
      />

      <TimelineConsultaPanel
        consultaIdAtual={consultaIdAtual}
        carregandoTimeline={carregandoTimeline}
        timelineConsulta={timelineConsulta}
        onRefresh={() => carregarTimelineConsulta()}
        onOpenLink={onOpenTimelineLink}
      />
    </div>
  );
}
