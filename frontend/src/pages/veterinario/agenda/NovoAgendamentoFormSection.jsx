import NovoAgendamentoConflitosHorario from "./NovoAgendamentoConflitosHorario";
import NovoAgendamentoEquipeSection from "./NovoAgendamentoEquipeSection";
import NovoAgendamentoMotivoEmergenciaSection from "./NovoAgendamentoMotivoEmergenciaSection";
import NovoAgendamentoTipoDataSection from "./NovoAgendamentoTipoDataSection";
import NovoAgendamentoTutorPetSection from "./NovoAgendamentoTutorPetSection";

export default function NovoAgendamentoFormSection({
  carregandoPetsTutor,
  conflitoHorarioSelecionado,
  consultorioSelecionadoModal,
  consultorios,
  diagnosticoConflitoSelecionado,
  dicaTipoSelecionado,
  formNovo,
  motivoPlaceholderPorTipo,
  onChangeCampo,
  onConfiguracoesVet,
  onHideForNovoPet,
  onTutorSelect,
  petsDoTutor,
  retornoNovoPet,
  tipoSelecionado,
  tutorSelecionado,
  veterinarioSelecionadoModal,
  veterinarios,
}) {
  return (
    <div className="space-y-3">
      <NovoAgendamentoTutorPetSection
        carregandoPetsTutor={carregandoPetsTutor}
        formNovo={formNovo}
        onChangeCampo={onChangeCampo}
        onHideForNovoPet={onHideForNovoPet}
        onTutorSelect={onTutorSelect}
        petsDoTutor={petsDoTutor}
        retornoNovoPet={retornoNovoPet}
        tutorSelecionado={tutorSelecionado}
      />

      <NovoAgendamentoEquipeSection
        consultorios={consultorios}
        formNovo={formNovo}
        onChangeCampo={onChangeCampo}
        onConfiguracoesVet={onConfiguracoesVet}
        veterinarios={veterinarios}
      />

      <NovoAgendamentoTipoDataSection
        dicaTipoSelecionado={dicaTipoSelecionado}
        formNovo={formNovo}
        onChangeCampo={onChangeCampo}
      />

      <NovoAgendamentoConflitosHorario
        conflitoHorarioSelecionado={conflitoHorarioSelecionado}
        consultorioSelecionadoModal={consultorioSelecionadoModal}
        diagnosticoConflitoSelecionado={diagnosticoConflitoSelecionado}
        formNovo={formNovo}
        veterinarioSelecionadoModal={veterinarioSelecionadoModal}
      />

      <NovoAgendamentoMotivoEmergenciaSection
        formNovo={formNovo}
        motivoPlaceholderPorTipo={motivoPlaceholderPorTipo}
        onChangeCampo={onChangeCampo}
        tipoSelecionado={tipoSelecionado}
      />
    </div>
  );
}
